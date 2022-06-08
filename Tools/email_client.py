import logging
import smtplib
import ssl
import mimetypes
from email.message import EmailMessage
import datetime


def send_email(sender_adress: str, sender_password: str, recipient: str, attachment_files: list, email_subject=f'Automated Content {datetime.date.today()}', email_body=' '):
    message = EmailMessage()
    message['From'] = sender_adress
    message['To'] = recipient
    message['Subject'] = email_subject
    body = email_body

    message.set_content(body)

    # Attach files to the email
    for attachment_file in attachment_files:
        mime_type, _ = mimetypes.guess_type(attachment_file)
        mime_type, mime_subtype = mime_type.split('/')
        try:
            with open(attachment_file, 'rb') as file:
                message.add_attachment(file.read(),
                                       maintype=mime_type,
                                       subtype=mime_subtype,
                                       filename=attachment_file)
        except FileNotFoundError:
            logging.critical(f'ERROR! Could not find the type of {attachment_file}. The file was skipped.')
            continue
    
    SSL_context = ssl.create_default_context()
    port = 587  
    smtp_server = "smtp-mail.outlook.com"

    server = smtplib.SMTP(smtp_server, port)

    server.starttls(context=SSL_context)

    server.login(sender_adress, sender_password)

    server.send_message(message)
    server.quit()
    
    print(f'E-mail with the subject {message["Subject"]} was successfully sent to {recipient}')