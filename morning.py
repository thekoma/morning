#!/usr/bin/env python3

import redis
import time
import os
import pickle
import json
import requests
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask
from flask import jsonify
from flask import request
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By

load_dotenv()

# Values from envirionment
username = os.getenv("LOGIN_USER")
password = os.getenv("LOGIN_PASSWORD")
selenium_url = os.getenv("SELENIUM_URL", "http://selenium:4444")
redis_host =os.getenv("REDIS_HOST", "redis")
redis_port =os.getenv("REDIS_PORT", 6379)
redis_db =os.getenv("REDIS_DB", 0)
cache_time=os.getenv("CACHE_TIME", 3600)

# Used Variables
selenium_hub = selenium_url + "/wd/hub"
login_page = 'https://www.ilpost.it/wp-login.php?redirect_to=https://www.ilpost.it'
morning_page = 'https://www.ilpost.it/podcasts/morning/'
username_xpath="//input[@id='user_login']"
password_xpath="//input[@id='user_pass']"
checkbox_xpath="//input[@id='rememberme']"
# accept_button_xpath='//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]'
login_xpath = '//input[@id="wp-submit"]'
morning_today_xpath = '//audio[@id="ilpostPlayerAudio"]'

# Init Objects
r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
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
            print(f"[🔴] {cookie.get('name')} - Expired: {time.ctime(cookie.get('expiry'))}")
            return False
          else:
            print(f"[🟠] {cookie.get('name')} - Ignored: {time.ctime(cookie.get('expiry'))}")
        else:
          print(f"[🟢] {cookie.get('name')}")
      else:
        print(f"[🟢] {cookie.get('name')} (session)")
    return cookies
  except:
    print("Niente cookies in Redis")
    return False
  
def create_cookies():
  driver = webdriver.Remote(
    command_executor=selenium_hub,
    options=webdriver.ChromeOptions()
  )
  print("Creating New Cookies!")
  with driver:
    driver.get(login_page)
    # print("Accept Cookie thing")
    # elem = driver.find_element(By.XPATH, accept_button_xpath)
    # elem.click()
    print ("Fill Credentials")
    elem = driver.find_element(By.XPATH, username_xpath)
    elem.send_keys(username)
    elem = driver.find_element(By.XPATH, password_xpath)
    elem.send_keys(password)
    elem = driver.find_element(By.XPATH, checkbox_xpath)
    elem.click()
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

def is_selenium_available():
  response=requests.get(selenium_url + "/ui/index.html")
  status=response.status_code
  if status > 200:
    return False, status
  else:
    return True, status


def is_redis_available():
    try:
      a=r.memory_stats()
    except (redis.exceptions.ConnectionError, redis.exceptions.BusyLoadingError):
      return False
    return True

@app.route("/cookies")
def get_cookies_json():
  checks=do_checks()
  if checks[0]:
    cookies=get_cookies()
    
    response = app.response_class(
        response=json.dumps(cookies),
        status=200,
        mimetype='application/json'
    )
  else:
    response = checks[1]
  return response

def get_cookies():
  cookies=get_cookies_redis()
  if not cookies:
    print("Validazione Cookie fallita, avvio la rigenerazione")
    cookies=create_cookies()
  return cookies

@app.route("/morning")
def get_morning_url():
  force = request.args.get('force')
  fresh = request.args.get('fresh')
  newcookies = request.args.get('newcookies')
  if force !=  None:
    newcookies = True
    fresh = True

  if newcookies !=  None:
    print("---> Forcing new Cookies")
    create_cookies()

  checks=do_checks()
  if checks[0]:
    now=time.time()
    last_scrape = 0 if r.get('last_scrape') is None else pickle.loads(r.get('last_scrape'))
    if ((now - last_scrape) > cache_time) or fresh !=  None:
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
  else:
    response = checks[1]
  return response

def update_morning_url():
  cookies=get_cookies()
  driver = webdriver.Remote(
    command_executor=selenium_hub,
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
    response = app.response_class(
      response="<p>Missing credentials!</p>",
      status=500
    )
  else:
    response = app.response_class(
      response="<p>Hello</p>",
      status=200
    )
  return response


def do_checks():
  print("Starting Checks")
  
  print("Check Selenium")
  selenium_status=is_selenium_available()
  
  print("Check Redis")
  redis_status=is_redis_available()
  
  if not selenium_status[0]:
    print("Selenium Failed")
    response = app.response_class(
      response="Connection to Selenium Failed",
      status=500
    )
    state = False
  if not redis_status:
    print("Redis Failed")
    response = app.response_class(
      response="Connection to Redis Failed",
      status=500
    )
    state = False
  elif ( not username or not password ):
    print("Credentials Failed")
    response = app.response_class(
      response="Missing credentials",
      status=500
    )
    state = False
  else:
    response = app.response_class(
        response="ok",
        status=200
    )
    state = True
  print("Finished Checks")
  return state, response

@app.route("/ping")
def ping():
  checks=do_checks()
  if checks[0]:
    response = app.response_class(
        response="pong",
        status=200
    )
  else:
    response = checks[1]
  return response

