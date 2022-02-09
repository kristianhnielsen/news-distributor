import copy
import datetime
import re
from requests_html import HTMLSession
import API.source_classes as source_classes

def find_page_urls(media_object, requests_session):
    media_object.page_urls = []
    # contains javascript to get older articles. First pageload gets 20 articles = 1-2 days of /local/ and 4-5 days of /china/.
    for category in media_object.categories:
        media_object.page_urls.append(f'{media_object.root_link}/section-news-list/section/{category}/')
    
    for page_url in media_object.page_urls:
        response = requests_session.get(page_url)
        response.html.render(sleep=1, timeout=200)
        try:
            article_bodies = response.html.find('li')
        except AttributeError:
            continue
        for article_body in article_bodies:
            for absolute_link in list(article_body.absolute_links):
                if re.search(r'www\.thestandard\.com\.hk.*\d/\d{6}', absolute_link) != None:
                    media_object.links.append(absolute_link)
            
    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    text_bodies = session_get_response.html.find('p')
    for body in text_bodies:
        # these two bodies are always the last bodies in a given article.
        if body.text.startswith('Trademark and Copyright Notice:') or body.text.startswith("Today's Standard"):
            break
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
        publishing_date = session_get_response.html.xpath('//*[@id="content"]/div/div[1]/div/div[1]/span', first=True).text
        raw_date = re.search(re.compile(r'(\d|\d{2}) \w{3} \d{4}'), publishing_date).group(0)
        formatted_date = datetime.datetime.strptime(raw_date, '%d %b %Y')
        publishing_date = formatted_date.strftime('%Y-%m-%d')  # YYYY-MM-DD
    except IndexError:
        return None
    
    return publishing_date

def get():
    standard = source_classes.Media(media_name='The Standard', root_link='https://thestandard.com.hk')
    standard.categories = ['local', 'china']
   

    with HTMLSession() as session:
        find_page_urls(standard, session)

        for link in standard.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'The Standard article No.: {standard.links.index(link)+1} of {len(standard.get_links())}')

            article.publishing_date = find_publishing_date(response)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            standard.get_articles().append(article)
        session.close()
        
    standard.sort_by_date()

    return standard

