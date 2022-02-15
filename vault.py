import pickle
import re
import datetime
import os

import API.scmp
import API.economist
import API.bbc
import API.the_guardian
import API.new_york_times
import API.china_daily
import API.global_times
import API.montsame
import API.peoples_daily
import API.xinhua
import API.gogo_mongolia
import API.caixin_global
import API.the_standard
import API.rthk
import API.hk_free_press
import API.the_diplomat
import API.reuters
import API.china_military

def update():
    """ Updates the vault with new articles from all available sources in the past week (or to the closest extent possible). Returns void. """
    start_time = datetime.datetime.now()
    try:
        start_vault_len = len(read_vault())
    except FileNotFoundError:
        start_vault_len = 0
    media_list = []

    # below parameters will yield approx. 1-2 weeks of articles on avg.
    # lowest: The Standard - 1-4 days
    # highest: Global Times - potentially 1+ month 


    add_to_vault_and_error_log(API.scmp.get(topic_url='defence', get_china_news=True, get_hk_news=True), media_list)
    add_to_vault_and_error_log(API.xinhua.get(number_of_pages_to_check=1), media_list)
    add_to_vault_and_error_log(API.global_times.get(), media_list)
    add_to_vault_and_error_log(API.caixin_global.get(), media_list)
    add_to_vault_and_error_log(API.new_york_times.get(), media_list)
    add_to_vault_and_error_log(API.china_daily.get(number_of_pages_to_check=5), media_list)
    add_to_vault_and_error_log(API.bbc.get(number_of_pages_to_check=2), media_list)
    add_to_vault_and_error_log(API.economist.get(number_of_pages_to_check=1), media_list)
    add_to_vault_and_error_log(API.the_guardian.get(get_hk_news=True, get_china_news=True, number_of_pages_to_check=2), media_list)
    add_to_vault_and_error_log(API.montsame.get(number_of_pages_to_check=2), media_list)
    add_to_vault_and_error_log(API.peoples_daily.get(number_of_pages_to_check=5), media_list)
    add_to_vault_and_error_log(API.gogo_mongolia.get(), media_list)
    add_to_vault_and_error_log(API.the_standard.get(), media_list)
    add_to_vault_and_error_log(API.rthk.get(), media_list)
    add_to_vault_and_error_log(API.hk_free_press.get(number_of_days_to_fetch=8), media_list)
    add_to_vault_and_error_log(API.the_diplomat.get(number_of_pages_to_check=2), media_list)
    add_to_vault_and_error_log(API.reuters.get(number_of_pages_to_check=20), media_list)
    add_to_vault_and_error_log(API.china_military.get(number_of_pages_to_check=2), media_list)


    log_update_report(start_time=start_time, start_vault_len=start_vault_len, media_list=media_list)

def empty_vault():
    """ Empties the vault of ALL content!!! """
    # Pickling
    filename = 'vault_data.pkl'
    with open(filename, 'wb') as outfile:
        pickle.dump([], outfile)
    print('Successfully emptied the vault')

def add_list(api_objects: list):
    """ Add a list of multiple API objects to the vault. Returns void. """
    # Transform
    for api in api_objects:
        add(api)

def add(api_object):
    """ Add a single API object to the vault. Returns void. """
    # Transform
    api = make_pickleable(api_object=api_object)
    try:
        existing_vault = read_vault()
    except FileNotFoundError:
        # Pickling
        filename = 'vault_data.pkl'
        with open(filename, 'wb') as outfile:
            pickle.dump('', outfile)
            outfile.close()
        existing_vault = read_vault()
    
    new_vault = []
    for existing_article in existing_vault:
        new_vault.append(existing_article)
    
    for new_article in api:
        new_vault.append(new_article)

    # Pickling
    filename = 'vault_data.pkl'

    with open(filename, 'wb') as outfile:
        pickle.dump(new_vault, outfile)
        outfile.close()

def make_pickleable(api_object):
    """ Takes a Media object from APIs and turns it into a list of dictionaries, which can be uniformly pickled.
    Returns a list. """
    pickleable_api = []
    for article in api_object.get_articles():
        pickleable_api.append({
            'media': api_object.media_name,
            'headline': article.headline,
            'text body': article.text_body,
            'publishing date': article.publishing_date,
            'source': article.source
        })

    return pickleable_api

def overwrite(api_object):
    """ Overwrites whatever is in the vault with new content. Returns void. """
    # Transform
    if type(api_object) == list:
        # This means, that it is more than one API, which have already been through combine()
        pickleable_api = api_object
    else:
        # The API object has not been previously processed by combine()
        pickleable_api = make_pickleable(api_object=api_object)

    # Pickling
    filename = 'vault_data.pkl'
    with open(filename, 'wb') as outfile:
        pickle.dump(pickleable_api, outfile)

def read_vault():
    """ Unpickles the vault. Returns a list of dictionaries. """
    filename = 'vault_data.pkl'
    with open(filename, 'rb') as vault_file:
        vault = pickle.load(vault_file)
        vault_file.close()

    return vault

def extract(sources: list, keywords: list, date='2021-01-01'):
    
    """ Extract articles from the vault based on keywords and/or date. Does not change vault content.
    Returns a list of dictionatries matching the parameters. """

    # Keywords should be a list,
    # date can either be int of days to include or
    # string ('YYYY-MM-DD') of earliest inclusion date.
    vault = read_vault()
    
    class Source:
        def __init__(self, source_name: str, want=False):
            self.source_name = source_name
            self.want = want

    source_objects = [
        Source('South China Morning Post'),
        Source('The Economist'),
        Source('BBC News'),
        Source('China Daily'),
        Source('Global Times'),
        Source('GoGo Mongolia'),
        Source('Montsame Mongolian News Agency'),
        Source('New York Times'),
        Source("People's Daily"),
        Source('The Guardian'),
        Source('Xinhua News Agency'),
        Source('Caixin Global'),
        Source('The Standard'),
        Source('RTHK News'),
        Source('Hong Kong Free Press'),
        Source('The Diplomat'),
        Source('Reuters'),
        Source('China Military'),
    ]
    
    
    for src_obj in source_objects:
        if src_obj.source_name in sources:
            src_obj.want = True

    vault = filter_by_source(database=vault, sources=source_objects)

    vault = filter_by_date(database=vault, date=date)
    
    vault = filter_by_keywords(
        keywords=keywords, 
        database=vault, 
        keywords_search_text_body=True, 
        keywords_search_headline=True
        )
    
    

    return vault

def filter_by_source(database, sources: list, all_sources=False):    
    relevant_articles = []
    for article in database:
        for source in sources:
            if source.want == True and article['media'] in source.source_name:
                relevant_articles.append(article)
    
    return relevant_articles

def filter_by_date(database, date=None):
    if date == None:
        return database

    filtered_database = []
    if type(date) == int:
        # Get a list of dates between today and given number of days in the past
        wanted_dates = []
        today = datetime.date.today()
        for day_num in range(date):
            wanted_dates.append(str(today - datetime.timedelta(days=day_num)))
        
        for article in database:
            if article['publishing date'] in wanted_dates:
                filtered_database.append(article)


    elif re.match(r'\d{4}-\d{2}-\d{2}', date):
        today = datetime.datetime.today()
        given_day = datetime.datetime.strptime(date, "%Y-%m-%d")
        number_of_days = (today - given_day).days
        wanted_dates = []
        for day_num in range(number_of_days):
            wanted_dates.append(str((today - datetime.timedelta(days=day_num)).date()))

        for article in database:
            if article['publishing date'] in wanted_dates:
                filtered_database.append(article)
    
    return filtered_database

def filter_by_keywords(database, keywords=None, keywords_search_text_body=True, keywords_search_headline=False):
    if keywords == None or keywords == []:
        return database
    else:
        # Filter by keywords
        filtered_database = []
        for article in database:
            for keyword in keywords:
                try:
                    text_body = article['text body']
                    headline = article['headline']
                except TypeError:
                    print(f'Failed to search for keywords in {article}')
                
                if keywords_search_text_body:
                    if re.search(keyword.lower(), text_body.lower()) != None:
                        # The article DOES contain at least one of the keywords
                        filtered_database.append(article)
                elif keywords_search_headline:
                    if re.search(keyword.lower(), headline.lower()) != None:
                        # The article DOES contain at least one of the keywords
                        filtered_database.append(article)
            else:
                # The article DOES NOT contain at least one of the keywords
                continue
        return filtered_database

def remove_vault_duplicates():
    """ Returns void, overwriting existing vault with a list of unique elements """
    existing_vault = read_vault()

    # Remove an new article if the vault has an article with same headline, media, and publishing date
    no_dupe_sources_vault = list({v['source']:v for v in existing_vault}.values()) 
    no_dupe_headlines_vault = list({v['headline']:v for v in no_dupe_sources_vault}.values())
    no_dupe_body_vault = list({v['text body']:v for v in no_dupe_headlines_vault}.values())   # Unique dictionary filter in list 
    new_vault = no_dupe_body_vault
       

    print(f'Removed {len(existing_vault)-len(new_vault)} duplicate articles from the vault!')
    print(f'Current number of articles in the vault is: {len(new_vault)}')
    

    overwrite(new_vault)

def commit_custom_runtime_date(runtime_file_name: str):
    """ Overwrites the runtime_date.pkl. Returns void. """
    runtime_date = datetime.date.today()
    if not os.path.isdir(os.getcwd() + '\\Runtime_files'):
        os.mkdir(os.getcwd() + '\\Runtime_files')
    
    # Pickling
    filename = '\\Runtime_files\\' + runtime_file_name + '.pkl'
    with open(os.getcwd() + filename, 'wb') as outfile:
        pickle.dump(runtime_date, outfile)

def get_last_custom_runtime_date(runtime_file_name: str):
    """ Get last complete runtime. Returns a date in string of YYYY-MM-DD """
    
    filename = '\\Runtime_files\\' + runtime_file_name + '.pkl'
    
    try:
        with open(os.getcwd() + filename, 'rb') as f:
            runtime_date = pickle.load(f)
    except FileNotFoundError:
        # runtime_date = input('The file does not exist, please give a date (format: YYYY-MM-DD) to start from: \n')
        runtime_date = '2021-01-01'

        runtime_date = datetime.datetime.strptime(runtime_date, '%Y-%m-%d')
    
    # runtime_date is not including the given date OR the last_runtime_date.
    # To make it inclusive except on Mondays, because including Fri, Sat, Sun AND Mon is just too much.
    if datetime.datetime.now().strftime('%A') != 'Monday':
        runtime_date -= datetime.timedelta(days=1)

    runtime_date = datetime.datetime.strftime(runtime_date, '%Y-%m-%d')

    return runtime_date

def log_update_report(start_time, start_vault_len, media_list: list):
    # If a sources structure changes, it might not get any articles, hence this warning.
    end_vault_len = len(read_vault())
    log_text = f'Date: {datetime.datetime.now()}\n'
    for media in media_list:
        if len(media.articles) == 0:
            log_text += f'WARNING! {media.media_name} did not contain any articles!\n'
        
        elif media.articles[0].publishing_date != str(datetime.date.today()):
            if media.articles[0].publishing_date != str(datetime.date.today() - datetime.timedelta(days=1)):
                log_text += f'WARNING {media.media_name} most recent article is not from today or yesterday!\n'
                log_text += f'{media.media_name} first articles publishing date is {media.articles[0].publishing_date}\n\n'            

    log_text += f'Newly added articles: {end_vault_len - start_vault_len}\n'
    end_time = datetime.datetime.now()
    runtime = (end_time - start_time)
    log_text += f'Runtime: {runtime}\n'
    log_text += '---------------------------------------------------------------\n\n\n'

    log_filename = 'update_log.txt'
    with open(log_filename, 'a') as f:
        f.write(log_text)
    
    # Delete error log, as no errors occurred
    error_log_filename = 'error_log.txt'
    os.unlink(f'{os.getcwd()}\\{error_log_filename}')

def error_logging(media_list: list):
    # Log incremental progress during runtime and save it in a .txt, which will be deleted upon successful runtime completion
    # Should help identify errors and save time by allowing manual restart from point of error occurrance 
    log_text = f'{datetime.datetime.now()} {media_list[-1].media_name} was completed\n'

    log_filename = 'error_log.txt'
    with open(log_filename, 'a') as f:
        f.write(log_text)

def delete_source_from_vault(source_name: str):
    old_vault = read_vault()
    new_vault = []
    for article in old_vault:
        if article['media'] != source_name:
            new_vault.append(article)
    overwrite(new_vault)
    print(f'Successfully deleted all articles published by {source_name}')

def add_to_vault_and_error_log(media_object, media_list: list):
    add_list([media_object])
    media_list.append(media_object)
    error_logging(media_list=media_list)

if __name__ == "__main__":
    update()