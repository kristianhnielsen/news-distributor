import API.source_classes as source_classes
import re
import requests
import bs4

def find_page_urls(media_object, number_of_pages_to_check):
    max_pages = 106
    page_urls = []

    if number_of_pages_to_check >= max_pages:
        number_of_pages_to_check = max_pages
    for page_num in range(1, number_of_pages_to_check+1):
        # as of January 2021, the China section has 105 pages.
        # The earliest articles from this are from January 2012.
        # In case of page overflow i.e. requesting page 106 or 110, will get page 1.
        if f'{media_object.root_link}?page={page_num}' not in page_urls:
            page_urls.append(f'{media_object.root_link}?page={page_num}')

    for page_url in page_urls:
        response = requests.get(page_url)
        soup = bs4.BeautifulSoup(response.text, 'lxml')
        _main = soup.find('main', id='content')
        _link_bodies = _main.find_all('a')
        links = []
        for link_body in _link_bodies:
            link = link_body.get('href')
            if re.search(r'\d{4}/\d{2}/\d{2}', link) != None:
                
                #Skip articles for podcasts
                if "economist.com/podcasts/" in link:
                    continue

                if link.startswith('https:'):
                    media_object.get_links().append(link)
                else:
                    media_object.get_links().append(media_object.root_link + link)

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    soup = bs4.BeautifulSoup(session_get_response.text, 'lxml')
    article_body = soup.find('div', attrs={'itemprop': 'text'})
    bodies = article_body.find_all('p')
    for body in bodies:
        if body.get_text().lower() == 'your browser does not support the <audio> element.' or body.get_text().lower() == 'enjoy more audio and podcasts on ios or android.':
            continue
        text_body += body.get_text() + '\n\n'
    text_body = text_body.strip()

    return text_body

def find_headline_in(session_get_response):
    headline = ''
    soup = bs4.BeautifulSoup(session_get_response.text, 'lxml')
    headline_bodies = soup.find('h1')
    for headline_body in headline_bodies.contents:
        if headline_body.get('data-test-id') == 'Article Headline':
            headline = headline_body.text
            break
    
    return headline

def find_publishing_date(link):
    split_link = link.split('/')
    publishing_date = f'{split_link[4]}-{split_link[5]}-{split_link[6]}'  # YYYY-MM-DD

    return publishing_date  


def get(number_of_pages_to_check=106):
    # The Economist only issues articles on Fridays
    economist = source_classes.Media(media_name='The Economist', root_link='https://www.economist.com')
    find_page_urls(economist, number_of_pages_to_check)

    for link in economist.get_links():
        response = requests.get(link)
        article = source_classes.Article(source=link)
        print(f'Economist article No.: {economist.links.index(link)+1} of {len(economist.get_links())}')
        
        try:
            article.publishing_date = find_publishing_date(link)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue
            
            economist.get_articles().append(article)
        
        except (AttributeError, TypeError) as e:
            print(f'Error: {e}. Skipping article.')
            continue

    economist.sort_by_date()

    return economist

