import API.source_classes as source_classes
import datetime
import re
import json
from requests_html import HTMLSession
import re
import json
from enum import Enum, auto
from requests import Session
from requests_html import HTMLSession
from abc import ABC, abstractmethod
from datetime import date, timedelta, datetime

def find_page_urls(media_object, requests_session, number_of_pages_to_check):
    page_urls = []
    for category in media_object.categories:
        response = requests_session.get(category)
        last_page_num = response.html.find('em')[0].text
        if last_page_num == '':
            # 2021-03-11 Finance doesn't have pagination on first page and will return empty string as last_page_num
            response = requests_session.get(f'{category}index-1.html')
            last_page_num = response.html.find('em')[0].text
        index = media_object.categories.index(category)
        for page_to_check in range(number_of_pages_to_check):
            if page_to_check == 0 or last_page_num == '':
                page_urls.append(f'{media_object.categories[index]}index.html')
            else:
                page_urls.append(f'{media_object.categories[index]}index{(page_to_check) - int(last_page_num)}.html') 

    for url in page_urls:
        response = requests_session.get(url)
        for element in response.html.find('ul'):
            try:
                if re.search(r'list-news', element.attrs['class'][0]) != None:
                    article_main_container = element
                    break
            except KeyError:
                continue
        article_links = article_main_container.find('li')
        for article in article_links:
            absolute_links_list = list(article.absolute_links)
            for absolute_link in absolute_links_list:
                if re.search(r'\d{4}-\d{2}-\d{2}', absolute_link) != None:
                    media_object.links.append(absolute_link)
    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    p = session_get_response.html.find('p')
    text_body = ''
    for paragraph in session_get_response.html.find('p'):
        stripped_p_text = paragraph.text.strip()
        stripped_p_text = stripped_p_text.replace('\xa0', ' ')
        if stripped_p_text.startswith('Read more\n'):
            continue
        if stripped_p_text.startswith('Support quality journalism in China'):
            break
        if stripped_p_text.startswith('Download our app to receive breaking news'):
            break
        if stripped_p_text == '':
            break
        text_body += stripped_p_text
        text_body += '\n\n'
    text_body.strip()
    
    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.find('h1')[0].text
    except IndexError:
        print('Headline not found.')
        return None
    
    return headline
    
def find_publishing_date(article):
    raw_date_in_link = re.search(re.compile(r'\d{4}-\d{2}-\d{2}'), article.source).group(0)
    formatted_date_in_link = datetime.datetime.strptime(raw_date_in_link, '%Y-%m-%d')
    return formatted_date_in_link.strftime('%Y-%m-%d')  # YYYY-MM-DD


class Status(Enum):
    OK = 'OK'
    ERROR_TEXTBODY = 'ERROR - TEXTBODY'
    ERROR_PUBLISHING_DATE = 'ERROR - PUBLISHING DATE'
    ERROR_HEADLINE = 'ERROR - HEADLINE'
    ERROR_CONNECTION = 'ERROR - CONNECTION'

class SessionType(Enum):
    REQUESTS = auto()
    REQUESTSHTML = auto()

class SessionHandler:
    '''A class to handle sessions.'''
    def __init__(self, session_type: SessionType) -> None:
        self.session_type = session_type
        self.session = self.new_session()

    def new_session(self):
        '''
        Creates a new session based on session_type.
        Add additional sessions here.
        '''
        if self.session_type == SessionType.REQUESTS:
            return Session()
        elif self.session_type == SessionType.REQUESTSHTML:
            return HTMLSession()

    def get_response(self, url):
        '''Returns the get-method from the given session type.'''
        try:
            response = self.session.get(url)
        except ConnectionError:
            '''Restart the session in case of connection errors.'''
            print('Connection error')
            self.session = self.new_session()
            response = self.get_response(url)
        except Exception as e:
            '''Any other exception will set the status as CONNECTION ERROR.'''
            print(e)
            return None

        return response

class PaginationLevels(Enum):
    LOW = 'low'
    WEEK = 'week'
    MONTH = 'month'
    HIGH = 'high'

class Pagination:
    def __init__(self) -> None:
        self.value = int()
        self.levels = {}
        self.define_pagination_values(week=0, month=0, high=0)
    
    def define_pagination_values(self, week: int, month: int, high: int):
        '''Set the different levels of collection for each source. Returns a list of pagination_values corresponding to the dict keys.'''
        self.levels = {
            PaginationLevels.LOW : 1, 
            PaginationLevels.WEEK : week, 
            PaginationLevels.MONTH : month, 
            PaginationLevels.HIGH : high
        }
    
    def get_pagination_value(self):
        return self.value

    def set_level(self, level: PaginationLevels):
        self.value = self.levels[level]


class Source(ABC):
    def __init__(self, source_name, session_type: SessionType):
        self.source_name = source_name
        self.session_handler = SessionHandler(session_type)
        self.root_link = ''
        self.response = None
        self.links = []
        self.pagination = Pagination()
        self.page_urls = []
        self.articles = []   
        self.articles_with_error = []   
        
    @abstractmethod
    def find_page_urls(self):
        '''Used to find URLs of the articles to check. Returns a list of strings.'''
        pass

    @abstractmethod
    def find_article_links(self):
        '''Find links for articles in page_urls for sources with pagination.'''
        pass

    @abstractmethod
    def find_publishing_date(self):
        '''Used to find the publishing date in an article. Returns a string with date ISO format'''
        pass
    
    @abstractmethod
    def find_headline(self):
        '''Used to find the headline in an article. Returns a string'''
        pass
    
    @abstractmethod
    def find_text_body(self):
        '''Used to find the text body of an article. Returns a string.'''
        pass

    @abstractmethod
    def post_processing(self):
        '''Add text manipilation/formatting methods in here as needed per source.'''
        pass

    # Main methods
    def collect_news(self):
        print(f'\n\nInitializing {self.source_name}')
        self.find_article_links()
        
        for link in self.get_links():
            article = Article()
            article.set_source(link)
            self.response = self.session_handler.get_response(article.source)
            
            if self.response == None or self.response.status_code != 200:
                article.status = Status.ERROR_CONNECTION
                self._print_progression(article)
                continue

            article = self._create_article(article)
            self.add_article(article)
            self._print_progression(article)

        self.post_processing()

        return self

    # Getters and setters
    def set_root_link(self, link):
        '''Sets the root link variable. May be changed to redirect focus of any-given source.'''
        self.root_link = link

    def get_links(self):
        '''Returns a list of links.'''
        return self.links
   
    def get_articles(self):
        '''Returns a list of articles gathered by the source.'''
        return self.articles

    def get_bad_articles(self):
        return self.articles_with_error
      
    def add_article(self, article):
        '''Adds an article to the list of articles.'''
        if not article.get_status() is Status.OK:
            self.articles_with_error.append(article)
            return
        self.articles.append(article)

    # Property management methods
    def _remove_duplicate_links(self):
        '''Returns a list of URLs, which does not contain duplicates.'''
        unique = []
        for element in self.links:
            if element not in unique:
                unique.append(element)
        self.links = unique

    def _sort_articles_by_date(self):
        '''Sorts the list of gathered article by publishing date (new to old).'''
        # reverse = None (Sorts in Ascending order)
        # key is set to sort using second element of
        # sublist lambda has been used
        self.get_articles().sort(key=lambda article: article.publishing_date, reverse=False)

    def _create_article(self, article):
        '''Returns an Article object, with it's attributes assigned by the instance-specific abstract methods.
        Text manipulation should take place in the abstract "find"-methods.'''
        article.set_source_name(self.source_name)
        article.set_headline(self.find_headline())
        article.set_publishing_date(self.find_publishing_date())
        article.set_text_body(self.find_text_body())
        return article  
    
    def _fix_encoding_on_articles(self):
        for article in self.get_articles():
            article.fix_encoding()

    def _get_textbody_from_paragrapghs(self, paragraphs):
        '''Most common non-manipulative method of getting from <p>'s of an article.'''
        txt = ''
        for body in paragraphs:
            txt += body.text + '\n\n'

        return txt.strip()

    def _extract_date_from_url(self, url_date_format):
        standard_url_date_format = self._replace_date_seperators(url_date_format)
        common_formats = {
            r'\d{4}-\d{2}-\d{2}':'%Y-%m-%d', 
            r'\d{2}-\d{2}-\d{4}':'%d-%m-%Y', 
            r'\d{6}-\d{2}' : '%Y%m-%d', 
            r'\d{4}-\d{4}' : '%Y-%m%d', 
            r'\d{8}' : '%Y%m%d',
            r'\d{4}-\w{3}-\d{2}':'%Y-%b-%d', 
            r'\d{2}-\w{3}-\d{4}':'%d-%b-%Y', 
            r'\d{4}\w{3}-\d{2}' : '%Y%b-%d', 
            r'\d{4}-\w{3}\d{2}' : '%Y-%b%d', 
            r'\d{4}\w{3}\d{2}' : '%Y%b%d'
            }
        
        try:
            raw_date = re.search(re.compile(url_date_format), self.response.url).group(0)
            raw_date = self._replace_date_seperators(raw_date)
            formatted_date = datetime.strptime(raw_date, common_formats.get(standard_url_date_format))
            date, _ = formatted_date.isoformat().split('T')
            return date
        except (IndexError, AttributeError):
            return None

    def _replace_date_seperators(self, date):
        common_seperators = ['/', '-']
        for common_seperator in common_seperators:
            date = date.replace(common_seperator, '-')
        
        return date

    # Miscellaneous methods
    def _print_progression(self, current_article):
        '''Prints the progress of the webscraping to the terminal for feedback.'''
        current_article_num = self.links.index(current_article.source) + 1
        total_article_num = len(self.get_links())
        percent_decimals = 2
        percent_complete = f"{(100/total_article_num)*current_article_num:.{percent_decimals}f}"
        
        print(f'{self.source_name}\t\t{percent_complete}% of {total_article_num} articles\t\tStatus: {current_article.status.value}')
       
class Article:
    def __init__(self) -> None:
        self.media_name = 'Caixin Global'
        self.source = ''
        self.source_name = ''
        self.publishing_date = ''
        self.headline = ''
        self.text_body = ''
        self.status = Status.OK 

    def set_source_name(self, source_name):
        self.source_name = source_name

    def set_source(self, source):
        self.source = source

    def set_publishing_date(self, date):
        self.publishing_date = date

    def set_headline(self, headline):
        self.headline = headline

    def set_text_body(self, text_body):
        self.text_body = text_body

    def get_status(self):
        if self.headline == None or self.headline == '':
            self.status = Status.ERROR_HEADLINE
        elif self.text_body == None or self.text_body == '':
            self.status = Status.ERROR_HEADLINE
        elif self.publishing_date == None or self.publishing_date == '':
            self.status = Status.ERROR_PUBLISHING_DATE

        return self.status

    def remove_patterns(self, regex):
            if re.search(regex, self.text_body) is not None:
                self.text_body = re.sub(regex, '', self.text_body).strip()

            if re.search(regex, self.headline) is not None:
                self.headline = re.sub(regex, '', self.headline).strip()
            
    def fix_encoding(self):
        self.text_body = self.text_body.encode('ascii', 'ignore').decode()
        self.headline = self.headline.encode('ascii', 'ignore').decode()
       


class Caixin(Source):
    def __init__(self):
        super().__init__('Caixin Global', session_type=SessionType.REQUESTSHTML)
        self.media_name = 'Caixin Global'
        self.set_root_link('https://www.caixinglobal.com')
        self.categories = self.get_category_urls(['business-and-tech', 'finance', 'economy', 'china', 'world']) 

        self.pagination.define_pagination_values(week=8, month=32, high=2_000) 

    # Abstract methods
    def find_page_urls(self):
        pass
    
    def find_article_links(self):
        for category_ID in self.find_category_IDs():
            total_page_number = self.find_total_page_number(category_ID)

            for page_num in range(1, total_page_number + 1):
                response = self.session_handler.get_response(self.jquery_link_generator(page_number=page_num, articles_per_page=100, category_ID=category_ID))
                #status_code = json.loads(response.text)['code']
                data = json.loads(response.text)['data']
                
                valid_articles_found = 0
                for article_request in data['list']:
                    if self.article_published_within_wanted_timeframe(article_request):
                        valid_articles_found += 1
                        self.links.append(article_request['url'])
                
                if valid_articles_found == 0:
                    break
        
        self._remove_duplicate_links()

    def find_headline(self):
        try:
            headline = self.response.html.find('h1')[0].text
            return headline
        except IndexError:
            print('Headline not found.')
            return None

    def find_publishing_date(self):
        return self._extract_date_from_url(r'\d{4}-\d{2}-\d{2}')

    def find_text_body(self):
        txt_body = ''
        for paragraph in self.response.html.find('p'):
            stripped_p_text = paragraph.text.strip()
            stripped_p_text = stripped_p_text.replace('\xa0', ' ')

            # End of article indicators 
            if stripped_p_text.startswith('Read more\n'):
                break
            if stripped_p_text.startswith('Support quality journalism in China'):
                break
            if stripped_p_text.startswith('Download our app to receive breaking news'):
                break
            if stripped_p_text == '':
                break
            
            txt_body += stripped_p_text + '\n\n'
        

        return txt_body
    
    def post_processing(self):
        self._fix_encoding_on_articles()
        self._sort_articles_by_date()

    # Additional methods
    def article_published_within_wanted_timeframe(self, article_request):
        try:
            publishing_date = re.search(re.compile(r'\d{4}-\d{2}-\d{2}'), article_request['url']).group(0)
        except AttributeError:
            return False

        for day in range(self.pagination.value):
            wanted_date = date.today() - timedelta(days=day)
            if publishing_date == str(wanted_date):
                return True

        return False

    def get_category_urls(self, category_names: list):
            '''Returns the URLs for each category/section of the source.'''
            category_urls = []
            for category_name in category_names:
                category_urls.append(f'{self.root_link}/{category_name}/')
            
            return category_urls

    def find_category_IDs(self):
        category_IDs = []
        for category in self.categories:
            response = self.session_handler.get_response(category)
            scripts = response.html.find('script')
            for script in scripts:
                if 'vpid' in script.text.lower():
                    idNum = script.text.split("'")[1] 
                    category_IDs.append(idNum)
                    break

        return category_IDs

    def find_total_page_number(self, category_ID: str):
        response = self.session_handler.get_response(self.jquery_link_generator(1, 100, category_ID))
        data = json.loads(response.text)['data']
        response.close()
        return data['totalPage']

    def jquery_link_generator(self, page_number: int, articles_per_page: int, category_ID: str):
        return f'https://gateway.caixinglobal.com/api/data/getNewsListByPids?page={page_number}&size={articles_per_page}&pids={category_ID}'


# def get(number_of_pages_to_check=50):
#     # 50 is the maximum number of pages available
#     # gets 100 articles per page.
#     caixin = source_classes.Media(media_name='Caixin Global', root_link='https://www.caixinglobal.com')
#     latest_1_000 = 'https://gateway.caixin.com/api/extapi/homeInterface.jsp?subject=100990318;100990314;100990311&start=0&count=1000'
#     caixin.categories = [
#         f'{caixin.root_link}/business-and-tech/',
#         f'{caixin.root_link}/finance/',
#         f'{caixin.root_link}/economy/',
#         f'{caixin.root_link}/china/',
#         f'{caixin.root_link}/world/'
#     ]
    


#     with HTMLSession() as session:
#         find_page_urls(caixin, session, number_of_pages_to_check)

#         for link in caixin.get_links():
#             article = source_classes.Article(link)
#             response = session.get(link)
#             print(f'Caixin Global article No.: {caixin.links.index(link)+1} of {len(caixin.get_links())}')

#             article.headline = find_headline_in(response)
#             article.text_body = find_text_body_in(response)
#             article.publishing_date = find_publishing_date(article)
#             if not article.has_content():
#                 continue

#             caixin.articles.append(article)
#     caixin.sort_by_date()

#     return caixin

def get():
    c = Caixin()
    c.pagination.set_level(PaginationLevels.WEEK)
    return c.collect_news()