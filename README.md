# News Distributor

## Description 

A Python-based news webscraper and distributor. <br/>
This software primarily gathers news content relevant for China, Hong Kong, and Macau.

<br/>

## Table of contents
- [Prerequisites](#prerequisites)
- [Get started](#get-started)
	- [Settings](#settings)
	- [Tasks](#tasks)
	- [Task manager](#task-manager)
	- [Vault](#vault)
- [Troubleshooting](#troubleshooting)
- [Add new source](#add-a-new-source)
- [Author](#author)
- [License](#license)

<br/>
<br/>

---

## PREREQUISITES
Besides having Python 3 installed, you also need:
```bash
pip install requests-html

pip install beautifulsoup4

pip install python-docx-1
```

<br/>

---

## GET STARTED

<br/>

### **Settings**
Change the email settings in `settings.json`. Currently **only Gmail addresses** have been tested.<br/>_You may have to configure security settings for the given Gmail address, before the script can access it._
```json
{
    "email_settings": {
        "email_address": "username@gmail.com",
        "email_password": "password123",
        "default_body": "This is an automated message."
    }
}
```

<br/>

---

### **Tasks**
Configure your tasks in `tasks.json`: <br/>
_There is a list of valid **sources** and days to **run_on** in `tasks.json`._
```json
"tasks": [
        {
            "task_name": "Test Task",
            "recepient": ["email_1_@domain.com", "email_two_@domain.com"],
            "sources": ["Source_1", "Source_two"],
            "keywords": ["WHO", "Wuhan", "COVID"],
            "run_on": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        }
```

<br/>

---

### **Task manager**
Either make a new `.py` file or run it directly from `task_manager.py`:<br/>

```python
import task_manager

run() 			# will update the vault and run all tasks within tasks.json
run_task('Test Task')	# will not update the vault, and only run the task_name given as parameter
```

<br/>

---

### **Vault** 
The `vault` lets you modify the content.<br/>
_`vault.update()` may take up to 2 hours in its current state._
```python
import vault

update()				# Updates the content of the vault via the given APIs
delete_source_from_vault("Source name")	# Deletes all content from a given source 
empty_vault()				# Deletes all content in the vault

```
<br/><br/>

### If the` vault.update()` was **successful**:
- `update_log.txt` will be created/updated.
- `Runtime_files/(task_name)_runtime.pkl` will be created/updated.
- `vault_data.pkl` will be created/updated. 

_The first time you run a new task, it will grab all news articles available since there is no `(task_name)_runtime.pkl` as point of reference._

<br/>

### If the `vault.update()` was **unsuccessful**:
- `error_log.txt` will be created and display which sources where successfully updated. 

<br/>

---	

## Troubleshooting
1. Restart the entire update process `task_manager.run()`
2. Comment out the sources in `vault.update()` which were successful and restart. 
3. If the error persists, the source website might have been updated, and need updating in the relevant `API/source_api.py`. Alternatively you can comment out the problematic source and restart.


_Scraping content from many different websites can cause many kinds of issues. <br/>
Be aware of occational errors if any of the websites structure changes._

<br/>

---

## Add a new source
1. Your webscraper needs to return the Media class object from `API/source_classes.py`.
2. Import your API in `vault.py`.
3. Add the API in similar fashion as other API to `vault.update()`, `vault.extract()`, and add source to relevant tasks in `tasks.json`

<br/>

---

## Author
**Kristian Hviid Nielsen** - [Github](https://github.com/kristianhnielsen)

