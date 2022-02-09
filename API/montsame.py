import API.source_classes as source_classes
from requests_html import HTMLSession


def find_page_urls(media_object, requests_session, number_of_pages_to_check):
    media_object.page_urls = []
    for page_num in range(1, number_of_pages_to_check + 1):
        category_indicators = [302, 303, 304, 417]  # Politics, Economy, Society, Environment
        for category in category_indicators:
            media_object.page_urls.append(f'https://www.montsame.mn/en/more/{category}?class=list&page={page_num}')
    
    for page_url in media_object.page_urls:
        response = requests_session.get(page_url)

        try:
            main_page_articles = response.html.xpath('//*[@id="left-container"]/div/div[1]', first=True)
            absolute_links = main_page_articles.absolute_links
        except AttributeError:
            try:
                main_page_articles = response.html.xpath('//*[@id="u10416740705070082"]/div/div[2]', first=True)
                absolute_links = main_page_articles.absolute_links
            except:
                continue

        for link in absolute_links:
            if '?class=list&page=' in link:
                # Skips any links to other pages, but keeps links to articles
                continue

            media_object.get_links().append(link)

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    text_container = session_get_response.html.xpath('//*[@id="left-container"]/div[1]/div/div[2]', first=True)
    text_bodies = text_container.find('p')
    for body in text_bodies:
        if body.text != '':
            temp_body = body.text.replace('\r\n', ' ')
            text_body += temp_body
            text_body += '\n\n'
    text_body = text_body.strip()

    return text_body

def find_headline_in(session_get_response):
    headline = session_get_response.html.find('h4')[0].text
    
    return headline

def find_publishing_date(session_get_response):
    try:
        publishing_date = session_get_response.html.xpath('//*[@id="left-container"]/div[1]/div/div[1]/div[1]/div[3]')[0].text
        publishing_date = publishing_date.split(' ')[0]
        return publishing_date
    except IndexError:
        try:
            publishing_date = session_get_response.html.xpath('//*[@id="left-container"]/div[1]/div/div[1]/div[2]/div[3]')[0].text
            publishing_date = publishing_date.split(' ')[0]
            return publishing_date
        except (AttributeError, IndexError):
            return None


def get(number_of_pages_to_check=10):
    montsame = source_classes.Media(media_name='Montsame Mongolian News Agency', root_link='https://www.montsame.mn/en/')

    with HTMLSession() as session:
        
        find_page_urls(montsame, session, number_of_pages_to_check)

        for link in montsame.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'Montsame article No.: {montsame.links.index(link) + 1} of {len(montsame.get_links())}')

            article.publishing_date = find_publishing_date(response)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            montsame.get_articles().append(article)
    montsame.sort_by_date()

    return montsame

