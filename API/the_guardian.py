import datetime
import re
from requests_html import HTMLSession
import API.source_classes as source_classes

def find_page_urls(media_object, requests_session, number_of_pages_to_check, get_china_news, get_hk_news):
    china_max_pages = 1082
    hk_max_pages = 109

    selected_urls = [media_object.root_link]
    if get_china_news:
        if number_of_pages_to_check >= china_max_pages:
            number_of_pages_to_check = china_max_pages
        for page_num in range(1, number_of_pages_to_check):
            # as of January 2021, the China section has 1082 pages.
            # In case of page overflow i.e. requesting page 1086 or 1100, will get page 1.
            china_page = f'https://www.theguardian.com/world/china?page={page_num}'
            if china_page not in selected_urls:
                selected_urls.append(china_page)

    if get_hk_news:
        if number_of_pages_to_check >= hk_max_pages:
            number_of_pages_to_check = hk_max_pages
        for page_num in range(1, number_of_pages_to_check):
            # as of March 2021, the Hong Kong section has 111 pages.
            # In case of page overflow i.e. requesting page 106 or 1000, will get page 1.
            hk_page = f'https://www.theguardian.com/world/hong-kong?page={page_num}'
            if hk_page not in selected_urls:
                selected_urls.append(hk_page)

    for url in selected_urls:
        response = requests_session.get(url)

        main_page_articles = response.html.xpath('//*[@id="top"]/div[3]', first=True)
        absolute_links = main_page_articles.absolute_links

        for link in absolute_links:
            if re.match(re.compile(r'https://www.theguardian.com/.*\d{4}/\w{3}/\d{2}'), link):
                # Only consider link if it contains a publishing date
                # Links not containing pub-date are usually dead-ends, live blogs, etc.
                media_object.get_links().append(link)

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    try:
        text_bodies = session_get_response.html.find('p')
        for body in text_bodies:
            text_body += body.text
            text_body += '\n\n'
        text_body = text_body.strip()
    except (AttributeError, TypeError):
        return None

    return text_body

def find_headline_in(session_get_response):
    try:
         headline = session_get_response.html.find('h1')[0].text
    except (AttributeError, TypeError, IndexError):
        return None

    return headline

def find_publishing_date(link):
    try:
        raw_date_in_link = re.search(re.compile(r'\d{4}/\w{3}/\d{2}'), link)
        split_link = link[raw_date_in_link.start():raw_date_in_link.end()]
        formatted_date_in_link = datetime.datetime.strptime(split_link, '%Y/%b/%d')
        publishing_date = formatted_date_in_link.strftime('%Y-%m-%d')
    except (AttributeError, TypeError):
        return None

    return publishing_date

def get(get_hk_news=False, get_china_news=False, number_of_pages_to_check=50):
    guardian = source_classes.Media(media_name='The Guardian', root_link='https://www.theguardian.com/world/')
    

    with HTMLSession() as session:
        find_page_urls(guardian, session, number_of_pages_to_check, get_china_news, get_hk_news)
        

        for link in guardian.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'The Guardian article No.: {guardian.links.index(link)+1} of {len(guardian.get_links())}')
            
            article.publishing_date = find_publishing_date(link)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue
            
            guardian.get_articles().append(article)

    guardian.sort_by_date()

    return guardian

