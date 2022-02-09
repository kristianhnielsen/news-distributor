import API.source_classes as source_classes
import datetime
import re
import bs4
import requests
from time import sleep

            
def suffix_manipulation(text):
    # Remove related articles and GT suffixes
    return source_classes.Article.remove_patterns(text, re.compile(r'(Global Times$|Newspaper headline:.*)', re.IGNORECASE))

def photo_description_manipulation(text):
    # Find and remove common photo description-text patterns from text.
    # WARNING! May leave "leftover text" not caught completely by the pattern.
    photo_text_regex = re.compile(r"""
                        [^.]*                                   # Include whatever sentence before the photo source declarations
                        (\.\s)?                                 # Find the full stop right before the photo source declarations
                        (photo([s]?)|illustration([s]?)):\s?    # Photo: OR illustration: 
                        (VCG|IC|CFP|MOD|AFP|NPU|                # Abbreviations
                        cnsphoto|pixabay|Xinhua|Weibo|Unsplash| # Other news agencies
                        China Military|Screenshot of CCTV|      # Other common photo sources
                        China Space News|                       # Other common photo sources
                        \w*\s\w*\/GT|                           # name of photograher / GT - Global Times
                        China News Service\/.*[\)\]]|           # Photo: China News Service/Name LastName - this may leave residual text before description
                        (www\.)?\w*\.(com|cn))                   # other web source                      
                        """, re.VERBOSE | re.IGNORECASE)
    text = source_classes.Article.remove_patterns(text, photo_text_regex)

    # Alternative photo description
    alt_photo_text_regex = re.compile(r'[^.]*(\.\s)?\(Xinhua\/.*\)')
    text = source_classes.Article.remove_patterns(text, alt_photo_text_regex)

    alt_alt_photo_text_regex = re.compile(r'(\[|\()File photo.*(\]|\))', re.IGNORECASE)
    text = source_classes.Article.remove_patterns(text, alt_alt_photo_text_regex)

    return text

def find_page_urls(media_object):
    for category in media_object.categories:
        cat_obj = source_classes.Media(media_name='category', root_link=category)
        _response = requests.get(cat_obj.root_link)
        _soup = bs4.BeautifulSoup(_response.text, 'lxml')
        cat_obj.main_container = _soup.find(class_='level01_list')
        for article in cat_obj.main_container.find_all(class_='list_info'):
            link = article.find('a', href=True)['href']
            media_object.get_links().append(link)
    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    soup = bs4.BeautifulSoup(session_get_response.text, 'lxml')
    
    try:
        article_content = soup.find(class_='article_content')
    except AttributeError:
        try:
            article_content = soup.find(class_='article_text')
        except:
            return None
    
    if article_content != None:
        for content_element in article_content.contents:
            for element in content_element:
                if type(element) == bs4.element.NavigableString:
                    if element == 'Global Times':
                        continue
                    text_body += element
                elif type(element) == bs4.element.Tag and element.name == 'a':
                    # element is an a-Tag, and will include the text, but not the href
                    text_body += element.text.strip()
                elif type(element) == bs4.element.Tag and element.name == 'br':
                    # element is a <br> tag, append break to text_body
                    text_body += '\n'
    else:
        print('could not find article_content')
        return None
    
    text_body = photo_description_manipulation(text_body)
    text_body = suffix_manipulation(text_body)
    text_body = text_body.strip()


    return text_body

def find_headline_in(session_get_response):
    headline = ''
    soup = bs4.BeautifulSoup(session_get_response.text, 'lxml')
    try:
        headline = soup.find(class_='article_title').text.strip()
    except AttributeError:
        try:
            headline = soup.find(class_='title').text.strip()
        except:
            return None
    
    return headline

def find_publishing_date(session_get_response):
    soup = bs4.BeautifulSoup(session_get_response.text, 'lxml')

    try:
        date = soup.find(class_='pub_time').text.split('Published: ')
        dt_format = datetime.datetime.strptime(date[1][:12], "%b %d, %Y")
        publishing_date = dt_format.isoformat().split('T')[0]
    except AttributeError:
        return None

    return publishing_date  


def get():
    # GT does not have an archive or pagination feature, and each category can only display about 90 of the newest articles.
    # Disclaimer: it is very difficult to format the text_body from GT, as it does not contain new lines, tabs or other kinds of white space.
    # This will sometimes result in imperfect attempts to insert new lines and make it more human readable.
    
    gt = source_classes.Media(media_name='Global Times', root_link='https://www.globaltimes.cn/china/')
    gt.categories = [gt.root_link,
                     f'{gt.root_link}politics/',
                     f'{gt.root_link}society/',
                     f'{gt.root_link}diplomacy/',
                     f'{gt.root_link}military/',
                     f'{gt.root_link}science/'
                     ]

    find_page_urls(gt)

    session = requests.Session()
    for link in gt.get_links():
        article = source_classes.Article(link)
        try:
            response = session.get(link)
        except requests.exceptions.ConnectionError:
            print('Connection error occurred. Taking a 5 second break')
            sleep(5)
            response = session.get(link)
        print(f'Global Times article No.: {gt.links.index(link) + 1} of {len(gt.get_links())}')

        article.publishing_date = find_publishing_date(response)
        article.headline = find_headline_in(response)
        article.text_body = find_text_body_in(response)
        if not article.has_content():
                continue
        article.fix_binary()

        gt.get_articles().append(article)
    gt.sort_by_date()

    return gt

