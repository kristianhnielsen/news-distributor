import API.source_classes as source_classes
import datetime
import re
from requests_html import HTMLSession

def find_page_urls(media_object, requests_session, number_of_pages_to_check):
    wanted_categories = ['Top Stories']
    page_urls = []
    response = requests_session.get(media_object.root_link)
    media_object.categories = response.html.find('h3')
    for category in media_object.categories:
        if category.text in wanted_categories:
            for page in range(1, number_of_pages_to_check + 1):
                default_category_link = list(category.absolute_links)[0]
                if page > 1:
                    no_htm_suffix_link = default_category_link.split('.htm')[0]
                    paged_link = f'{no_htm_suffix_link}_{page}.htm'
                    page_urls.append(paged_link)
                else:
                    page_urls.append(default_category_link)



    for page_url in page_urls:
        response = requests_session.get(page_url)

        main_container = response.html.xpath('//*[@id="main-news-list"]', first=True)
        absolute_links = main_container.absolute_links
        for absolute_link in absolute_links:
            if absolute_link.startswith(f'{media_object.root_link}view/'):
                media_object.links.append(absolute_link)
            
    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    article_main_body = session_get_response.html.xpath('//*[@id="article-content"]', first=True)
    
    try:
        text_bodies = article_main_body.find('p')
    except AttributeError:
        return None

    for body in text_bodies:
        # This excludes elements with pagination text or video elements
        if body.text.startswith('1 2 '):
            continue
        if body.text.startswith('<!-- //Video'):
            continue
        
        text_body += body.text
        text_body += '\n\n'
    text_body = text_body.strip()

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
    try:
        raw_date = re.search(re.compile(r'\d{4}-\d{2}/\d{2}'), article.source).group(0)
        formatted_date = datetime.datetime.strptime(raw_date, '%Y-%m/%d')
        publishing_date = formatted_date.strftime('%Y-%m-%d')  # YYYY-MM-DD
    except IndexError:
        return None

    return publishing_date  


def get(number_of_pages_to_check=1):
    cn_mil = source_classes.Media(media_name='China Military', root_link='http://eng.chinamil.com.cn/')
    
    #cn_mil.links.append('http://eng.chinamil.com.cn/view/2021-03/23/content_10009256.htm')
   
    with HTMLSession() as session:
        find_page_urls(cn_mil, session, number_of_pages_to_check)

        for link in cn_mil.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'China Military article No.: {cn_mil.links.index(link)+1} of {len(cn_mil.get_links())}')

            article.publishing_date = find_publishing_date(article)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            cn_mil.get_articles().append(article)
    cn_mil.sort_by_date()

    return cn_mil

