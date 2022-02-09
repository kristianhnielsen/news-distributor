import datetime
from requests_html import HTMLSession
import API.source_classes as source_classes

def find_page_urls(media_object, requests_session, number_of_pages_to_check):
    media_object.page_urls = []
    for category in media_object.categories:
        for page_to_check in range(1, number_of_pages_to_check + 1):
            media_object.page_urls.append(f'{media_object.root_link}/category/{category}/page/{page_to_check}')

    for page_url in media_object.page_urls:
        response = requests_session.get(page_url)

        main_container = response.html.xpath('//*[@id="td-list"]', first=True)
        absolute_links = main_container.absolute_links
        for absolute_link in absolute_links:
            if absolute_link.startswith('https://thediplomat.com/category'):
                continue
            media_object.links.append(absolute_link)    

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    article_main_body = session_get_response.html.xpath('//*[@id="td-story-body"]', first=True)
    text_bodies = article_main_body.find('p')
    for body in text_bodies:
        try:
            if body.attrs['ng-show'] == 'dplpw.ad':
                continue
        except KeyError:
            text_body += body.text
            text_body += '\n\n'
    text_body = text_body.strip()

    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.find('h1')[0].text
    except AttributeError:
        return None

    return headline

def find_publishing_date(session_get_response):
    try:
        raw_date = session_get_response.html.xpath('//*[@id="td-meta"]/div/div[2]', first=True).text
        formatted_date = datetime.datetime.strptime(raw_date, '%B %d, %Y')
        publishing_date = formatted_date.strftime('%Y-%m-%d')  # YYYY-MM-DD
    except IndexError:
        return None
    
    return publishing_date

def get(number_of_pages_to_check=2):
    diplomat = source_classes.Media(media_name='The Diplomat', root_link='https://thediplomat.com')
    diplomat.categories = ['asia-defense', 'flashpoints']

    with HTMLSession() as session:
        find_page_urls(diplomat, session, number_of_pages_to_check)

        for link in diplomat.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'The Diplomat article No.: {diplomat.links.index(link)+1} of {len(diplomat.get_links())}')

            article.publishing_date = find_publishing_date(response)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            diplomat.get_articles().append(article)
    diplomat.sort_by_date()

    return diplomat

