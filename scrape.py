from dotenv import load_dotenv
import os
import email
import smtplib
import time
import pymongo
from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pprint import pprint
import json
import sys

load_dotenv()
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

options = webdriver.ChromeOptions()
options.headless = True
chrome_options = webdriver.ChromeOptions()
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)

def check_and_send():
    pprint("Connecting to mongodb database...")
    cluster = MongoClient(os.getenv("DATABASE_PASSWORD"))
    db = cluster["amazon-price-tracker"]
    collection = db["items"]
    print("Connected.")

    for x in collection.find():
        print(x['url'])
        product_price,product_name = scrape_bare(x['url'])
        collection.find_one_and_update({'url' : x['url']},{ '$push': {'price' : product_price}})
        print(product_price, product_name)
        subs = x['subscription']
        for sub in subs:
            print(sub['name'])
            print(sub['email'])
            print(sub['targetPrice'])

            if(product_price <= sub['targetPrice']):
                email_notification_sender(sub['email'], sub['name'], x['url'], product_name, product_price, sub['targetPrice'])

        print('\n')
    
    driver.close()

def email_notification_sender(reciever_email,reciever_name,item_url,product_name,product_price,target_price):
    sender_address = os.getenv("SENDER_ADDRESS")
    sender_pass = os.getenv("SENDER_PASSWORD")
    receiver_address = reciever_email

    mail_content = '''
Hey {name}!

The item you were looking forward to is now on sale, grab it now!

Item Name : {product_name}
Your Target Price : {target_price}
Current Price : {curr_price}

Click the link below to get it!
{url}

Happy Shopping ✨
    '''.format(name = reciever_name, url = item_url, target_price = target_price , curr_price = product_price, product_name = product_name)

    message = MIMEMultipart()
    message['From'] = sender_address
    message['To'] = receiver_address
    message['Subject'] = 'The item you were looking forward to is now on SALE 🎉'
    message.attach(MIMEText(mail_content, 'plain'))

    session = smtplib.SMTP('smtp.gmail.com', 587) 
    session.starttls()
    session.login(sender_address, sender_pass)
    text = message.as_string()
    session.sendmail(sender_address, receiver_address, text)
    session.quit()
    print('Mail Sent')

def scrape_product_with_link(link, reciever_email, reciever_name, target_price):
    driver.get(link)
    driver.implicitly_wait(10)
    product_name = driver.title
    print(product_name)

    product_price = driver.find_element_by_id('priceblock_ourprice')
    product_price = product_price.text.replace(" ", "")
    product_price = product_price[1:].replace(",","")
    product_price = float(product_price)
    print(product_price)

    if(product_price < target_price):
        email_notification_sender(reciever_email, reciever_name, link, product_name, product_price,target_price)
        
    driver.close()

def scrape_bare(url):
    driver.get(url)
    product_name = driver.title
    print(product_name)

    product_price = driver.find_element_by_id('priceblock_ourprice')
    product_price = product_price.text.replace(" ", "")
    product_price = product_price[1:].replace(",","")
    product_price = float(product_price)
    print(product_price)

    return product_price,product_name

try:
    check_and_send()
except:
    print("Oops!", sys.exc_info()[0], "occurred.")
    print("Selenium Error")
    pass
finally:
    print("Application ran sucessfully!!!")
    # driver.close()