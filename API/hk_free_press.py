import API.source_classes as source_classes
import datetime
import re
from requests_html import HTMLSession


def find_page_urls(media_object, requests_session, number_of_days_to_fetch):
    page_urls = []
    for day in range(number_of_days_to_fetch):
        today = datetime.datetime.now()
        wanted_date_unformatted = (today - datetime.timedelta(days=day)).date()
        wanted_date_formatted = datetime.datetime.strftime(wanted_date_unformatted, "%Y/%m/%d")
        page_urls.append(f'{media_object.root_link}{wanted_date_formatted}')
    
    for page_url in page_urls:
        response = requests_session.get(page_url)
        main_article_container = response.html.find('main')[0]
        for absolute_link in main_article_container.absolute_links:
            if re.match(r'https://hongkongfp.com/\d{4}/\d{2}/\d{2}', absolute_link):
                media_object.links.append(absolute_link)

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    article_container = session_get_response.html.find('article')[0]
    paragraphs = article_container.find('p')
    for paragraph in paragraphs:
        if len(paragraph.attrs) != 0:
            break
        if paragraph.text.startswith('Support HKFP'):
            break
        text_body += paragraph.text + ' \n\n'

    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.find('h1')[0].text
        return headline
    except AttributeError:
        return None

def find_publishing_date(link):
    try:
        raw_date = re.search(re.compile(r'\d{4}/\d{2}/\d{2}'), link).group(0)
        formatted_date = datetime.datetime.strptime(raw_date, '%Y/%m/%d')
        publishing_date = formatted_date.strftime('%Y-%m-%d')  # YYYY-MM-DD
        return publishing_date
    except IndexError:
        return None

def get(number_of_days_to_fetch: int):
    hkfp = source_classes.Media(media_name='Hong Kong Free Press', root_link='https://hongkongfp.com/')


    with HTMLSession() as session:
        find_page_urls(hkfp, session, number_of_days_to_fetch)

        for link in hkfp.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'{hkfp.media_name} article No.: {hkfp.links.index(link)+1} of {len(hkfp.get_links())}')

            article.publishing_date = find_publishing_date(link)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)

            article.text_body = article.text_body.strip()

            hkfp.get_articles().append(article)
    hkfp.sort_by_date()

    return hkfp

