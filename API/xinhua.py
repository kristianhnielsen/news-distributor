import re
import bs4
from requests_html import HTMLSession
import API.source_classes as source_classes

def find_page_urls(media_object, requests_session):
    media_object.page_urls = []
    category_base_urls = [
        f'{media_object.root_link}list/china-business.htm',
        f'{media_object.root_link}list/china-chinaworld.htm',
        f'{media_object.root_link}list/china-politics.htm',
        f'{media_object.root_link}list/china-society.htm',
        f'{media_object.root_link}list/china-science.htm'
    ]

    for category_base_url in category_base_urls:
        response = requests_session.get(category_base_url)
        soup = bs4.BeautifulSoup(response.text, 'lxml')
        main_content_container = soup.find(id="list")
        articles_list = main_content_container.find_all('div')

        for article in articles_list:
            for content_element in article.contents:
                if content_element.name == 'a':
                    article_href = content_element.attrs['href']
                    break
                elif content_element.name == 'div':
                    for div_element in content_element.contents:
                        if div_element.name == 'a':
                            article_href = div_element.attrs['href']
                            break
            
            full_url = "https://english.news.cn" + article_href[2:]
            media_object.get_links().append(full_url)

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    text_bodies = session_get_response.html.find('p')
    for body in text_bodies:
        text_body += body.text
        text_body += '\n\n'
    text_body = text_body.strip()
    

    # Remove photo descriptions
    text_body = source_classes.Article.remove_patterns(text_body, re.compile(r'Photo taken on.*(\(|\[).*Xinhua.*(\)|\])'))
    text_body = source_classes.Article.remove_patterns(text_body, re.compile(r'.*(\[|\()Xinhua\/.*(\]|\))'))

    # Remove "Enditem"-suffix
    text_body = source_classes.Article.remove_patterns(text_body, re.compile(r'Enditem$'))
    text_body = source_classes.Article.remove_patterns(text_body, re.compile(r'Enditem.*Next$'))
    text_body = text_body.strip()

    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.find('h1')[0].text
    except IndexError:
        return None

    return headline

def find_publishing_date(session_get_response):
    for meta_element in session_get_response.html.find('meta'):
        try:
            if meta_element.attrs['name'] == 'publishdate':
                return meta_element.attrs['content']
        except KeyError:
            # meta element does not have the "name" attribute
            continue
        
def get(number_of_pages_to_check=3):
    xinhua = source_classes.Media(media_name='Xinhua News Agency', root_link='http://www.xinhuanet.com/english/')
    

    with HTMLSession() as session:
        find_page_urls(xinhua, session)

        for link in xinhua.get_links():
            response = session.get(link)
            if response.status_code == 504 or response.text == '':
                print('Error 504, skipping article.')
                continue
            article = source_classes.Article(source=link)
            print(f'Xinhua article No.: {xinhua.links.index(link)+1} of {len(xinhua.get_links())}')

            article.publishing_date = find_publishing_date(response)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            xinhua.get_articles().append(article)
    xinhua.sort_by_date()

    return xinhua

