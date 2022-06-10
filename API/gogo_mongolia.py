import re
import json
import bs4
from enum import Enum, auto
from time import sleep
from requests import Session
from requests_html import HTMLSession
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta

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
       
class Article:
    def __init__(self) -> None:
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
    def collect(self):
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

    def _create_article(self, article: Article):
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


class GogoMongolia(Source):
    def __init__(self):
        super().__init__('GoGo Mongolia', session_type=SessionType.REQUESTSHTML)
        self.set_root_link('https://mongolia.gogo.mn')
        self.pagination.define_pagination_values(week=8, month=30, high=1000)  
        self.media_name = self.source_name      

    # Additional methods
    def get_category_urls(self):
            '''Returns the URLs for each category/section of the source.'''
            categories = []
            category_IDs = ['7073', '7068', '7368', '7369', '7371', '7081', '7510']
            for days in range(1, self.pagination.value + 1):
                d = date.today() - timedelta(days=days)
                
                for ID in category_IDs:
                    categories.append(f'{self.root_link}/i/{ID}/fetch?lastDate={d}T14:51:55%2B08:00')
            
            return categories

    # Abstract methods
    def find_page_urls(self):
        self.data = []
        
        for link in self.get_category_urls():
                r = self.session_handler.get_response(link)
                self.data.append(json.loads(r.text)['nav_news_list'])

    def find_article_links(self):
        self.find_page_urls()
        
        for category in self.data:
            for article in category:
                link = f'{self.root_link}/r/{article["lid"]}'
                self.links.append(link)
                
        self._remove_duplicate_links()

    def find_headline(self):
        try:
            headline = self.response.html.find('h1')[0].text.strip()
        except (AttributeError, IndexError):
            return None
        
        return headline

    def find_publishing_date(self):
        for element in self.response.html.find('meta'):
            try:
                if re.search(r'\d{4}-\d{2}-\d{2}', element.attrs['content']) != None:
                    date, _ = element.attrs['content'].split('T')
                    return date 
            except (KeyError, ValueError):
                continue
        
        return None

    def find_text_body(self):
        txt_body = ''
        text_bodies = self.response.html.find('p')
        for body in text_bodies:
            body = body.text.strip() + '\n\n'
            # Gogo Mongolia's webpages sometimes have hidden <p>'s with same content, check for dubplicates
            if body not in txt_body:
                txt_body += body
        return txt_body.strip()
    
    def post_processing(self):
        self._fix_encoding_on_articles()
        self._sort_articles_by_date()
 
def get():
    src = GogoMongolia()
    src.pagination.set_level(PaginationLevels.WEEK)
    return src.collect()
