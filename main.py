from flask import Flask
import redis
import time
import os
import json
import pickle
from dotenv import load_dotenv


from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By

app = Flask(__name__)

load_dotenv()
username = os.getenv("LOGIN_USER")
password = os.getenv("LOGIN_PASSWORD")
selenium_url = os.getenv("SELENIUM_URL")

login_page = 'https://abbonati.ilpost.it/mio-account/?redirect=https://www.ilpost.it'
morning_page = 'https://www.ilpost.it/podcasts/morning/'
username_xpath="//input[@id='username']"
password_xpath="//input[@id='password']"
accept_button_xpath='//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]'
login_xpath = '//*[@id="customer_login"]/div/form/p[3]/button'
morning_today_xpath = '//audio[@id="ilpostPlayerAudio"]'

r = redis.Redis(host='trenzalore.asgard.lan', port=6379, db=0)

def get_cookies_redis():
  try:
    cookies=pickle.loads(r.get('cookies'))
    now=time.time()
    print(f"Found {len(cookies)} cookies in redis!")
    for cookie in cookies:
      if cookie.get('expiry'):
        if now > cookie.get('expiry'):
          if len(cookie.get('value')) > 10:
            print(f"[🔴]{cookie.get('name')} - Expired: {time.ctime(cookie.get('expiry'))}")
            return False
          else:
            print(f"[🟠]{cookie.get('name')} - Ignored: {time.ctime(cookie.get('expiry'))}")
        else:
          print(f"[🟢]{cookie.get('name')}")
    return cookies
  except:
    print("Niente cookies in Redis")
    return False
  

  






def create_cookies():
  driver = webdriver.Remote(
    command_executor=selenium_url,
    options=webdriver.ChromeOptions()
  )

  with driver:
    driver.get(login_page)
    print("Accept Cookie thing")
    elem = driver.find_element(By.XPATH, accept_button_xpath)
    elem.click()
    print ("Fill Credentials")
    elem = driver.find_element(By.XPATH, username_xpath)
    elem.send_keys(username)
    elem = driver.find_element(By.XPATH, password_xpath)
    elem.send_keys(password)
    try:
      print("Login")
      elem = driver.find_element(By.XPATH, login_xpath)
      elem.click()
    except:
      print("Failed to login")
    cookies=driver.get_cookies()
    r.set('cookies', pickle.dumps(cookies))
    driver.close()
    return cookies
    

def get_cookies():
  try:
    cookies=get_cookies_redis()
  except:
    print("Validazione Cookie fallita, avvio la rigenerazione")
    cookies=create_cookies()
    

  print(json.dumps(cookies))
  
  
  

# @app.route("/morning")
def get_morning_url():
  driver = webdriver.Remote(
    command_executor=selenium_url,
    options=webdriver.ChromeOptions()
  )

  with driver:
    driver.get(login_page)
    print("Accept Cookie thing")
    elem = driver.find_element(By.XPATH, accept_button_xpath)
    elem.click()
    print ("Fill Credentials")
    elem = driver.find_element(By.XPATH, username_xpath)
    elem.send_keys(username)
    elem = driver.find_element(By.XPATH, password_xpath)
    elem.send_keys(password)
    try:
      print("Login")
      elem = driver.find_element(By.XPATH, login_xpath)
      elem.click()
    except:
      print("Failed to login")
    
    try:
      print("Accept Second Cookie Thing")
      elem = driver.find_element(By.XPATH, accept_button_xpath)
      elem.click()
    except:
      print("Failed to Accept Cookie (who cares)")
    time.sleep(5)
    
    print("Navigate to Morning Post Page")
    driver.get(morning_page)
    elem = driver.find_element(By.XPATH, morning_today_xpath)
    url = elem.get_attribute('src')
    print(driver.get_cookies())
    driver.close()
    return url

# @app.route("/")
def main():
  if ( not username or not password ):
    print("Missing username or password!")
    return False
  get_cookies()
  return True
  url = get_morning_url()
  # url = "ciao.mp3"
  return "<p>Hello, World!</p>"
  
  
# @app.route("/ping")
def hello_world():
  return "pong"

# if __name__ == "__main__":
#     main()

# @app.route("/file")
# def lastrun():
#   file = open("cache.txt", 'r')
#   ret=file.read()
#   file.close()
#   return ret
if __name__ == "__main__":
    main()