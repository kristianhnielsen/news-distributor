import API.source_classes as source_classes
import datetime
import re
import time
from requests_html import HTMLSession

def find_page_urls(media_object, requests_session, number_of_pages_to_check):
    page_urls = []
    response = requests_session.get(media_object.root_link)
    wanted_category_names = ['News', 'Latest', 'Innovation', 'Education', 'Society', 'HK/Taiwan/Macao', 'Environment', 'Health', 'Military', 'National Affairs']
    latest_category_link = ''
    a_tags = response.html.find('a')
    found_categories = []
    for a_tag in a_tags:
        try:
            if a_tag.attrs['target'] == '_top':
                if list(a_tag.absolute_links)[0].startswith(media_object.root_link):
                    if a_tag.text in wanted_category_names and a_tag.text not in found_categories:
                        found_categories.append(a_tag.text)
                        media_object.categories.append(f'{list(a_tag.absolute_links)[0]}')
        except KeyError:
            continue
    for category_link in media_object.categories:
        # Get 3 times as many pages from 'Latest' section as the other categories to get articles published within the same timespan.
        if category_link == latest_category_link:
            for page_num in range(1, (number_of_pages_to_check*3)+1):
                page_urls.append(f'{category_link}/page_{page_num}.html')

        
        else:
            for page_num in range(1, number_of_pages_to_check+1):
                page_urls.append(f'{category_link}/page_{page_num}.html')

    for page in page_urls:
            # found_any_links_on_page is a failsafe that stops if no relevant links are found.
            # This helps vault.build_database() as CD's max page_num rises by the day.
            found_any_links_on_page = False
            try:
                response = requests_session.get(page)
            except ConnectionError:
                print('Connection error! Waiting 5 seconds then retry.')
                time.sleep(5)
                response = requests_session.get(page)
            main_page_articles = response.html.xpath('/html/body/div[5]/div[1]', first=True)
            absolute_links = main_page_articles.absolute_links

            for link in absolute_links:
                if re.search((r'\d{6}/\d{2}'), link) != None:
                    # Only consider link if it contains a publishing date
                    # Links not containing pub-date are usually dead-ends, live blogs, etc.
                    found_any_links_on_page = True
                    media_object.get_links().append(link)
            if not found_any_links_on_page:
                break
    
    media_object.remove_duplicate_links()

def find_text_body_in(article, session_get_response):
    text_body = ''
    try:
        body_container = session_get_response.html.xpath('//*[@id="Content"]', first=True)
        text_bodies = body_container.find('p')
        for body in text_bodies:
            text_body += body.text
            text_body += '\n\n'
        text_body = text_body.strip()

        if text_body == '':
            print(f'Article did not contain any text. Skipping article.')
            return None
    except AttributeError:
        print(f'Could not find the body of {article.source}. Skipping to next article.')
        return None

    return text_body

def find_headline_in(session_get_response):
    headline = ''
    try:
        headline = session_get_response.html.find('h1')[0].text
    except IndexError:
        return None

    return headline

def find_publishing_date(article):
    publishing_date = ''

    raw_date_in_link = re.search(re.compile(r'\d{6}/\d{2}'), article.source).group(0)
    formatted_date_in_link = datetime.datetime.strptime(raw_date_in_link, '%Y%m/%d')
    publishing_date = formatted_date_in_link.strftime('%Y-%m-%d')  # YYYY-MM-DD
    
    return publishing_date  

def get(number_of_pages_to_check=10_000):
    cd = source_classes.Media(media_name='China Daily', root_link='https://global.chinadaily.com.cn/china')
    cd.get_links().append('https://global.chinadaily.com.cn/a/202103/22/WS60586b9aa31024ad0bab0cba.html')

    with HTMLSession() as session:
        find_page_urls(cd, session, number_of_pages_to_check)
        
        # Open articles
        for link in cd.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'China Daily article No.: {cd.links.index(link)+1} of {len(cd.get_links())}')

            article.publishing_date = find_publishing_date(article)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(article, response)
            if not article.has_content():
                continue

            cd.get_articles().append(article)
    cd.sort_by_date()

    return cd
