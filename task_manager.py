import Tools.email_client as email_client
import Tools.docx_module as docx_module
import re
import datetime
import json
import vault
import os


def run():
    # vault.update()
    tasks = create_tasks_from(import_from_json('tasks.json'))
    for task in tasks:
        task.run()
    
    if datetime.datetime.now().strftime('%A') == 'Friday':
        vault.empty_vault() 
        vault.update()

def run_task(task_name: str):
    tasks = create_tasks_from(import_from_json('tasks.json'))
    task_found = False
    for task in tasks:
        if task.task_name == task_name:
            task_found = True
            task.run()
    
    if not task_found:
        print(f'No task found with the task name: {task_name}.\n You may create a new task in tasks.json')

def create_tasks_from(data):
    list_of_tasks = []
    today_day_of_week = datetime.datetime.now().strftime('%A') 
    for task_data in data['tasks']:
        task = Task(task_data)

        # Only grab tasks that are relevant to today or if no day given in tasks.json
        if len(task.run_on_day_of_week) == 0:
            list_of_tasks.append(task)
        elif today_day_of_week in task.run_on_day_of_week:
            list_of_tasks.append(task)

    return list_of_tasks

def import_from_json(filename: str):
    with open(filename) as f:
        return json.load(f)


class Task:
    def __init__(self, json_task_data):
        self.task_name = json_task_data['task_name']
        print(f'Identified a task: {self.task_name}')
        self.sources = json_task_data['sources']
        self.run_on_day_of_week = json_task_data['run_on']
        self.email_recipient = json_task_data['recepient'] 
        self.keywords = json_task_data['keywords']
        self.runtime_filename = f'{self.task_name}_runtime'
        self.filename = f'{self.task_name} {datetime.date.today()}.docx'
        self.email_subject=f'{self.task_name} {datetime.date.today()}'
        self.earliest_date_for_articles = self.get_date()
        self.relevant_articles = vault.extract(sources=self.sources, keywords=self.keywords, date=self.earliest_date_for_articles) 

    def get_date(self):
        if self.task_name == 'Mongolian News':
            date = datetime.date.today() - datetime.timedelta(days=8)   
        elif datetime.datetime.now().strftime('%A') != 'Monday':
            date =  datetime.date.today() - datetime.timedelta(days=2)
        else: 
            date = datetime.date.today() - datetime.timedelta(days=4)

        return date.isoformat()

    def change_earliest_date_for_articles(self, date=None):
        '''change the date with either String of YYYY-MM-DD, or Int of days to go back. If no match, then it will remain unchanged.'''
        
        if type(date) == int:
            self.earliest_date_for_articles = datetime.date.today() - datetime.timedelta(date)
        elif re.match(r'\d{4}-\d{2}-\d{2}', date):
                self.earliest_date_for_articles = date
        else:
            pass
            
    def run(self):
        settings = import_from_json('settings.json')
        email_settings = settings['email_settings']

        docx_module.write_to_docx(database=self.relevant_articles, document_name=self.filename)
        if type(self.email_recipient) is str:
            email_client.send_email(
                            sender_adress=email_settings['email_address'], 
                            sender_password=email_settings['email_password'], 
                            attachment_files=[self.filename], 
                            email_subject=self.email_subject, 
                            recipient=self.email_recipient,
                            email_body=email_settings['default_body'])
        elif type(self.email_recipient) is list:
            for email_address in self.email_recipient:
                email_client.send_email(
                                sender_adress=email_settings['email_address'], 
                                sender_password=email_settings['email_password'], 
                                attachment_files=[self.filename], 
                                email_subject=self.email_subject, 
                                recipient=email_address,
                                email_body=email_settings['default_body'])   

        vault.commit_custom_runtime_date(self.runtime_filename)
        self.delete_file(self.filename)

        print(f'{self.task_name} completed\n\n')



    def delete_file(self, filename: str):
        """ Deletes the filename given. Intended to clean up .docx files after being sent. 
        Returns void. """
        directory = f'{os.getcwd()}\\{filename}'

        os.unlink(directory)

if __name__ == "__main__":
    run()