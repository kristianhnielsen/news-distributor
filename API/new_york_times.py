import re
import API.source_classes as source_classes
from requests_html import HTMLSession

def find_page_urls(media_object, requests_session):
    response = requests_session.get(media_object.root_link)
    main_page_articles = response.html.find('li')
    absolute_links = []
    for element in main_page_articles:
        if len(element.absolute_links) == 0:
            continue
        for link in list(element.absolute_links):
            absolute_links.append(link)

    for link in absolute_links:
        # The search excludes non-relevant links
        if re.search(r'www.nytimes.com/\d{4}/\d{2}/\d{2}', link) != None:
            media_object.get_links().append(link)
           
    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    text_container = session_get_response.html.xpath('//*[@id="story"]/section', first=True)
    text_bodies = text_container.find('p')
    for body in text_bodies:
        text_body += body.text
        text_body += '\n\n'
    text_body = text_body.strip()

    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.xpath('//*[@id="story"]/div[3]/header/div[3]', first=True).text
    except AttributeError:
        headline = session_get_response.html.find('h1')[0].text

    return headline

def find_publishing_date(session_get_response):
    try:
        publishing_date = session_get_response.html.xpath('//*[@id="story"]/div[3]/header/div[6]/ul/li/time')[0]
        publishing_date = publishing_date.attrs['datetime'].split('T')[0]
        return publishing_date
    except IndexError:
        try:
            publishing_date = session_get_response.html.find('time')[0]
            publishing_date = publishing_date.attrs['datetime'].split('T')[0]
            return publishing_date
        except (IndexError, KeyError):
            # This error usually means that the "article" is different in some way,
            # i.e. more based on interactive Java-Script elements, images/photos or videos.
            return None



def get():
    # It is not possible to access an online backlog or archive of earlier articles, other than the ones given in the root_link.
    nyt = source_classes.Media(media_name='New York Times', root_link='https://www.nytimes.com/topic/destination/china')

    with HTMLSession() as session:
        find_page_urls(nyt, session)

        for link in nyt.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'NY Times article No.: {nyt.links.index(link)+1} of {len(nyt.get_links())}')

            
            article.publishing_date = find_publishing_date(response)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            article.fix_binary()
            if not article.has_content():
                continue
            
            nyt.get_articles().append(article)
    nyt.sort_by_date()

    return nyt
