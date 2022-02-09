from requests_html import HTMLSession
import API.source_classes as source_classes


def find_page_urls(media_object, requests_session, topic_url='', get_hk_news=False, get_china_news=False):
    china_news_categories = [f'{media_object.root_link}news/china',
                             f'{media_object.root_link}news/china/politics',
                             f'{media_object.root_link}news/china/diplomacy',
                             f'{media_object.root_link}news/china/science',
                             f'{media_object.root_link}news/china/military'
                             ]
    hk_news_categories = [f'{media_object.root_link}news/hong-kong',
                          f'{media_object.root_link}news/hong-kong/politics',
                          f'{media_object.root_link}news/hong-kong/hong-kong-economy',
                          f'{media_object.root_link}news/hong-kong/health-environment',
                          f'{media_object.root_link}news/hong-kong/law-and-crime',
                          f'{media_object.root_link}news/hong-kong/society',
                          f'{media_object.root_link}news/hong-kong/education',
                          f'{media_object.root_link}news/hong-kong/transport'
                          ]

    selected_urls = [media_object.root_link]
    if get_hk_news:
        for element in hk_news_categories:
            selected_urls.append(element)
    if get_china_news:
        for element in china_news_categories:
            selected_urls.append(element)
    if topic_url != '':
        selected_urls.append(f'{media_object.root_link}topics/{topic_url}')

    response = requests_session.get(media_object.root_link)
    for category in selected_urls:
        response = requests_session.get(category)

        try:
            main_page_articles = response.html.xpath('//*[@id="main-content"]/div/div[2]/div[2]/div[1]/div/div/div[1]/div[3]/div[2]/div[1]', first=True)
            absolute_links = main_page_articles.absolute_links
        except AttributeError:
            try:
                main_page_articles = response.html.xpath('//*[@id="main-content"]/div[2]/div[1]/div[3]/div[2]/div[1]/div', first=True)
                absolute_links = main_page_articles.absolute_links
            except AttributeError:
                try:
                    main_page_articles = response.html.xpath('//*[@id="main-content"]/div/div[2]/div[2]/div[1]/div/div/div[1]/div[3]/div[2]/div[1]', first=True)
                    absolute_links = main_page_articles.absolute_links
                except AttributeError:
                    try:
                        main_page_articles = response.html.xpath('//*[@id="topic-detail"]/div[1]/div/div[5]', first=True)
                        absolute_links = main_page_articles.absolute_links
                    except:
                        continue

        for link in absolute_links:
            # Filtering out common dead-end links
            if link.startswith('https://www.scmp.com/author'):
                continue
            if link.endswith('.com/opinion') or link.endswith('.com/topics'):
                continue
            if link.endswith('#comments'):
                continue
            if "article" not in link:
                continue

            media_object.get_links().append(link)

    media_object.remove_duplicate_links()

def find_text_body_in(session_get_response):
    text_body = ''
    try:
        text_body = session_get_response.html.full_text
        text_body = text_body.split('"articleBody":"')[1]
        text_body = text_body.split('","image":')[0]
        text_body = text_body.split('","articleSection":')[0]
    except IndexError:
        print('Error: Could not find text body')
        return None

    # Split up text_body to insert new lines after every 3 full-stops
    # Essentially making the text more human readable.
    split_text_body = text_body.split('. ')
    new_text_body = ''
    for element in split_text_body:
        if split_text_body.index(element) % 3:
            new_text_body += element + '.\n\n'
        else:
            new_text_body += element + '. '
    text_body = new_text_body.strip()[:-1]

    return text_body

def find_headline_in(session_get_response):
    try:
        headline = session_get_response.html.xpath('//*[@id="main-content"]/div[2]/div[2]/div[2]/div[1]/div/div[2]/div[2]/div[3]/h1')[0]
        headline = headline.text
    except IndexError:
        try:
            headline = session_get_response.html.find('h1').text
        except AttributeError:
            return None

    return headline

def find_publishing_date(session_get_response):
    try:
        publishing_date = session_get_response.html.xpath('//*[@id="main-content"]/div[2]/div[2]/div[2]/div[1]/div/div[2]/div[2]/div[3]/div[4]/div/div[2]/div/div[3]/div[1]/div/p[1]/time')[0]
        publishing_date = publishing_date.attrs['datetime'].split('T')[0]
        publishing_date = publishing_date.split('T')[0]
    except:
        return None
    
    return publishing_date

def get(topic_url='', get_hk_news=False, get_china_news=False):
    scmp = source_classes.Media(media_name='South China Morning Post', root_link='https://www.scmp.com/')
    

    with HTMLSession() as session:
        find_page_urls(scmp, session, topic_url, get_hk_news, get_china_news)

        # Open articles
        for link in scmp.get_links():
            response = session.get(link)
            article = source_classes.Article(source=link)
            print(f'South China Morning Post article No.: {scmp.links.index(link)+1} of {len(scmp.get_links())}')

            
            article.publishing_date = find_publishing_date(response)
            article.headline = find_headline_in(response)
            article.text_body = find_text_body_in(response)
            if not article.has_content():
                continue

            scmp.get_articles().append(article)
    scmp.sort_by_date()

    return scmp


