#Qwerty@123

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import Keys

MY_ADDRESS = Keys.getEmailID()
PASSWORD = Keys.getEmailPassword()

TO_ADDRESS = "kamarajk@tcd.ie"

def sendEmail():
    s = smtplib.SMTP(host = 'smtp.gmail.com', port = 587)
    s.starttls()
    s.login(MY_ADDRESS, PASSWORD)

    message = "ALERT! This specific area might require your attention. Please check it out."

    msg = MIMEMultipart()

    msg['From'] = MY_ADDRESS
    msg['To'] = TO_ADDRESS
    msg['Subject'] = "ALERT!!! Potential disaster detected."

    msg.attach(MIMEText(message, 'plain'))

    s.send_message(msg)
    del msg

    s.quit()

    print("Email sent successfully!")