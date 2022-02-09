import datetime
import re
from requests_html import HTMLSession
import API.source_classes as source_classes

def find_page_urls(media_object, requests_session):
    response = requests_session.get(media_object.root_link)
    main_article_container = response.html.xpath('//*[@id="ns2-230"]', first=True)
    for absolute_link in main_article_container.absolute_links:
        media_object.links.append(absolute_link)

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    main_body = session_get_response.html.xpath('//*[@id="avatar-pos-main-body"]/div[1]/div[6]/div[2]', first=True)
            
    if main_body.attrs['class'][0] != 'itemFullText':
        # if the div class is not 'itemFullText', then it is often an audioclip, and the text has been moved down by 1 div
        main_body = session_get_response.html.xpath('//*[@id="avatar-pos-main-body"]/div[1]/div[6]/div[3]', first=True)
    text_body = main_body.text.strip()

    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.find('h2')[0].text
    except AttributeError:
        return None

    return headline

def find_publishing_date(link):
    try:
        raw_date = re.search(re.compile(r'\d{8}'), link).group(0)
        formatted_date = datetime.datetime.strptime(raw_date, '%Y%m%d')
        publishing_date = formatted_date.strftime('%Y-%m-%d')  # YYYY-MM-DD
    except IndexError:
        return None

    return publishing_date

def get():
    rthk = source_classes.Media(media_name='RTHK News', root_link='https://news.rthk.hk/rthk/en/latest-news.htm')

    with HTMLSession() as session:
        
        find_page_urls(rthk, session)

        for link in rthk.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'RTHK News article No.: {rthk.links.index(link)+1} of {len(rthk.get_links())}')
            
            article.publishing_date = find_publishing_date(link)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)    
            if not article.has_content():
                continue

            rthk.get_articles().append(article)
    rthk.sort_by_date()

    return rthk

