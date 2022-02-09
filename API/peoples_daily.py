import datetime
import re
from requests_html import HTMLSession
import API.source_classes as source_classes

def find_page_urls(media_object, requests_session, number_of_pages_to_check):
    media_object.page_urls = []
    for page_num in range(1, number_of_pages_to_check + 1):
        media_object.page_urls.append(f'http://en.people.cn/98649/index{page_num}.html')
    
    for page in media_object.page_urls:
        response = requests_session.get(page)

        main_page_articles = response.html.xpath('/html/body/div/div[5]/div[1]', first=True)
        absolute_links = main_page_articles.absolute_links

        for link in absolute_links:
            if re.match(re.compile(r'.*\d{4}/\d{4}'), link):
                # Only consider link if it contains a publishing date
                # Links not containing pub-date are usually dead-ends, live blogs, etc.
                media_object.get_links().append(link)

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    body_container = session_get_response.html.xpath('//*[@id="p_content"]', first=True)
    if body_container is None:
        body_container = session_get_response.html.xpath('/html/body/div[6]', first=True)
    if body_container is None:
        body_container = session_get_response.html.xpath('/html/body/div[1]/div[3]', first=True)
    
    text_bodies = body_container.find('p')
    if len(text_bodies) == 0:
        return None

    for body in text_bodies:
        # showPlayer({ is to recognize internal video player element 
        if not body.text.startswith('showPlayer({'):
            if body.text != '':
                text_body += body.text
                text_body += '\n\n'
    text_body = text_body.strip()


    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.find('h1')[0].text
    except IndexError:
        try:
            headline = session_get_response.html.find('h2')[0].text
        except AttributeError:
            return None

    return headline

def find_publishing_date(link):
    raw_date_in_link = re.search(re.compile(r'\d{4}/\d{4}'), link).group(0)
    formatted_date_in_link = datetime.datetime.strptime(raw_date_in_link, '%Y/%m%d')
    publishing_date = formatted_date_in_link.strftime('%Y-%m-%d')  # YYYY-MM-DD

    return publishing_date


def get(number_of_pages_to_check=50):
    # 50 pages = 500 links
    pd = source_classes.Media(media_name="People's Daily", root_link='http://en.people.cn/98649/index.html')

    with HTMLSession() as session:
        
        find_page_urls(pd, session, number_of_pages_to_check)

        for link in pd.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f"People's Daily article No.: {pd.links.index(link)+1} of {len(pd.get_links())}")

           
            article.publishing_date = find_publishing_date(link)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            pd.get_articles().append(article)
    pd.sort_by_date()

    return pd

