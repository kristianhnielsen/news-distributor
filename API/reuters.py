from requests_html import HTMLSession
import API.source_classes as source_classes

def find_page_urls(media_object, requests_session, number_of_pages_to_check):
    media_object.categories = ['china-news']
    media_object.page_urls = []
    for category in media_object.categories:
        for page_to_check in range(1, number_of_pages_to_check + 1):
            media_object.page_urls.append(f'{media_object.root_link}{category}?page={page_to_check}')
    
    for page_url in media_object.page_urls:
        response = requests_session.get(page_url)

        main_container = response.html.xpath('//*[@id="content"]', first=True)
        absolute_links = main_container.absolute_links
        for absolute_link in absolute_links:
            if absolute_link.startswith('https://www.reuters.com/article'):
                media_object.links.append(absolute_link)
        
    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    try:
        article_main_body = session_get_response.html.xpath('//*[@id="fusion-app"]/div/div[2]/div/div[1]/article/div/div/div', first=True)
        text_bodies = article_main_body.find('p')
    except AttributeError:
        return None
    
    for body in text_bodies:
        try:
            if body.attrs['data-testid'].startswith('paragraph'):
                text_body += body.text
                text_body += '\n\n'
        except KeyError:
            continue
    text_body = text_body.strip()

    return text_body

def find_headline_in(session_get_response):
    try:
        headline_object = session_get_response.html.find('h1', first=True)
        headline_text = headline_object.html.split('</a></span>')[1]
        headline = headline_text.replace('</h1>', '')
    except (AttributeError, IndexError):
        try:
            headline = session_get_response.html.find('h1', first=True).text
        except (AttributeError, IndexError):
            return None
    
    return headline

def find_publishing_date(session_get_response):
    meta_elements = session_get_response.html.xpath('/html/head/meta')
    for meta in meta_elements:
        try:
            if meta.attrs['name'] == 'sailthru.date':
                raw_date = meta.attrs['content']
                break
            elif meta.attrs['name'] == 'article:published_time':
                raw_date = meta.attrs['content']
                break
            elif meta.attrs['property'] == 'og:article:published_time':
                raw_date = meta.attrs['content']
                break
        except KeyError:
            continue

    try:
        publishing_date = raw_date.split('T')[0]
    except UnboundLocalError:
        publishing_date = None

    return publishing_date

def get(number_of_pages_to_check=20):
    reuters = source_classes.Media(media_name='Reuters', root_link='https://www.reuters.com/news/archive/')
    
    with HTMLSession() as session:
        find_page_urls(reuters, session, number_of_pages_to_check)

        for link in reuters.get_links():
            try:
                response = session.get(link)
            except ConnectionError:
                print('Encountered a connection error, skipping article!')
                continue
            article = source_classes.Article(source=link)
            print(f'Reuters article No.: {reuters.links.index(link)+1} of {len(reuters.get_links())}')

            article.publishing_date = find_publishing_date(response)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            reuters.get_articles().append(article)
    reuters.sort_by_date()

    return reuters

