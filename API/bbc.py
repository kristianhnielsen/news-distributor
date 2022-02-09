import API.source_classes as source_classes
from requests_html import HTMLSession

def find_page_urls(media_object, requests_session, number_of_pages_to_check):
    page_urls = []
    for page_num in range(1, number_of_pages_to_check+1):
        page_urls.append(f'https://www.bbc.com/news/live/world-asia-china-47640057/page/{page_num}')
    
    for page_url in page_urls:
                response = requests_session.get(page_url)

                try:
                    main_page_articles = response.html.xpath('//*[@id="lx-stream"]/div[2]/ol', first=True)
                    absolute_links = main_page_articles.absolute_links
                except AttributeError:
                    try:
                        main_page_articles = response.html.find('ol')[0]
                        absolute_links = main_page_articles.absolute_links
                    except:
                        continue

                for link in absolute_links:
                    if link.startswith('http://www.bbc.co.uk/faqs/'):
                        continue
                    if link.startswith('https://www.bbc.co') or link.startswith('http://www.bbc.co'):
                        # To ensure inclusion of bbc.com and bbc.co.uk, with https and http connections.
                        # and to ensure exclusion of other external websites
                        media_object.get_links().append(link)
    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    try:
        text_container = session_get_response.html.find('article')[0]
    except IndexError:
        print('Could not find article text. Skipping.')
        return None

    text_bodies = text_container.find('p')
    for body in text_bodies:
        text_body += body.text
        text_body += '\n\n'
    text_body = text_body.strip()

    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.xpath('//*[@id="main-heading"]', first=True).text
    except AttributeError:
        headline = session_get_response.html.find('h1')[0].text
    return headline

def find_publishing_date(session_get_response):
    try:
        publishing_date = session_get_response.html.find('time')
        publishing_date = publishing_date[0].attrs['datetime'].split('T')[0]
    except IndexError:
        # This error usually means that the "article" is different in some way,
        # i.e. more based on interactive Java-Script elements, images/photos or videos.
        return None
    except KeyError as e:
        print(f'KeyError: {e}')
        return None

    return publishing_date


def get(number_of_pages_to_check=50):
    # 50 is the maximum number of pages available
    bbc = source_classes.Media(media_name='BBC News', root_link='https://www.bbc.com/news/world/asia/china')
    
    with HTMLSession() as session:
        find_page_urls(bbc, session, number_of_pages_to_check)

        for link in bbc.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'BBC article No.: {bbc.links.index(link)+1} of {len(bbc.get_links())}')

            article.publishing_date = find_publishing_date(response)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            bbc.get_articles().append(article)
    bbc.sort_by_date()

    return bbc

