from flask import Flask
from flask import jsonify
import redis
import time
import os
import pickle
import json
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.common import exceptions

app = Flask(__name__)

load_dotenv()

# Values from envirionment
username = os.getenv("LOGIN_USER")
password = os.getenv("LOGIN_PASSWORD")
selenium_url = os.getenv("SELENIUM_URL")
cache_time=os.getenv("CACHE_TIME", 600)

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
    pickled_cookies=r.get('cookies')
    cookies=pickle.loads(pickled_cookies)
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
      else:
        print(f"[🟢]{cookie.get('name')} (session)")
      
    return cookies
  except:
    print("Niente cookies in Redis")
    return False
  
def create_cookies():
  driver = webdriver.Remote(
    command_executor=selenium_url,
    options=webdriver.ChromeOptions()
  )
  print("Creating New Cookies!")
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
    time.sleep(10)
    cookies=driver.get_cookies()
    r.set('cookies', pickle.dumps(cookies))
    driver.close()
    return cookies
    
@app.route("/cookies")
def get_cookies_json():
  cookies=get_cookies()
  
  response = app.response_class(
      response=json.dumps(cookies),
      status=200,
      mimetype='application/json'
  )
  return response

def get_cookies():
  cookies=get_cookies_redis()
  if not cookies:
    print("Validazione Cookie fallita, avvio la rigenerazione")
    cookies=create_cookies()
  return cookies

@app.route("/morning")
def get_morning_url():

  # Se Ho girto negli ultimi 5 minuti pesco da redis
  now=time.time()
  last_scrape = 0 if r.get('last_scrape') is None else pickle.loads(r.get('last_scrape'))
  if ((now - last_scrape) > cache_time):
    update_morning_url()
    last_scrape=pickle.loads(r.get('last_scrape'))

  last_change = 0      if r.get('last_change') is None else pickle.loads(r.get('last_change'))
  old_morning = "Null" if r.get('old_morning') is None else pickle.loads(r.get('old_morning'))
  morning     = "Null" if r.get('morning')     is None else pickle.loads(r.get('morning'))
  
  return jsonify(
    morning=morning,
    old_morning=old_morning,
    last_scrape=last_scrape,
    last_change=last_change
  )

def update_morning_url():
  cookies=get_cookies()
  driver = webdriver.Remote(
    command_executor=selenium_url,
    options=webdriver.ChromeOptions()
  )
  with driver:
    print("Navigate to Morning Post Page")
    driver.get('https://ilpost.it')
    driver.delete_all_cookies()
    for cookie in cookies:
      if (cookie.get('domain') == '.ilpost.it'): 
        driver.add_cookie(cookie)
    time.sleep(5) 
    print("Loading page")
    driver.get(morning_page)
    elem = driver.find_element(By.XPATH, morning_today_xpath)
    morning = elem.get_attribute('src')
    driver.close()
    last_scrape=time.time()
    old_morning = "Null" if r.get('morning') is None else pickle.loads(r.get('morning'))
    
    if old_morning != morning:
      r.set('old_morning', pickle.dumps(old_morning))
      r.set('morning', pickle.dumps(morning))
      r.set('last_change', pickle.dumps(last_scrape))
    r.set('last_scrape', pickle.dumps(last_scrape))
    return jsonify(
        morning=morning,
        old_morning=old_morning,
        last_scrape=last_scrape,
        last_change=last_scrape
    )

@app.route("/")
def main():
  if ( not username or not password ):
    print("Missing username or password!")
    return False
  return "<p>Up And Running!</p>"
  
@app.route("/ping")
def ping():
  return "pong"
