#!/usr/bin/env python3
"""This stupid webapp catches the latest morning post from ilpost.it ."""
import orjson, json
import os
import pickle
import time
import redis
import requests
from dotenv import load_dotenv
from typing import Union
from fastapi import FastAPI, status, Response
from fastapi.responses import PlainTextResponse, ORJSONResponse, HTMLResponse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By

load_dotenv()

# Values from envirionment
USERNAME = os.getenv("LOGIN_USER")
PASSWORD = os.getenv("LOGIN_PASSWORD")
SELENIUM_URL = os.getenv("SELENIUM_URL", "http://selenium:4444")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
CACHE_TIME = int(os.getenv("CACHE_TIME", "3600"))

# Used Variables
SELENIUM_HUB = SELENIUM_URL + "/wd/hub"
LOGIN_PAGE = "https://www.ilpost.it/wp-login.php?redirect_to=https://www.ilpost.it"
MORNING_PAGE = "https://www.ilpost.it/podcasts/morning/"
USERNAME_XPATH = "//input[@id='user_login']"
PASSWORD_XPATH = "//input[@id='user_pass']"
CHECKBOX_XPATH = "//input[@id='rememberme']"
# accept_button_xpath='//*[@id="qc-cmp2-ui"]/div[2]/div/button[2]'
LOGIN_XPATH = '//input[@id="wp-submit"]'
MORNING_TODAY_XPATH = '//audio[@id="ilpostPlayerAudio"]'

# Init Objects
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, socket_timeout=1)
app = FastAPI()

def get_cookies_redis():
    """Return false if redis has no cookies.
    Otherwise return cookies."""
    pickled_cookies = r.get("cookies")
    print("DEBUG")
    try:
        cookies = pickle.loads(pickled_cookies)
    except (TypeError):
        cookies = create_cookies()
    now = time.time()
    print(f"Found {len(cookies)} cookies in redis!")
    for cookie in cookies:
        if cookie.get("expiry"):
            if now > cookie.get("expiry"):
                if len(cookie.get("value")) > 10:
                    print(
                        f"[🔴] {cookie.get('name')} - \
                        Expired: {time.ctime(cookie.get('expiry'))}"
                    )
                    cookies = None
                else:
                    print(
                        f"[🟠] {cookie.get('name')} - \
                        Ignored: {time.ctime(cookie.get('expiry'))}"
                    )
            else:
                print(f"[🟢] {cookie.get('name')}")
        else:
            print(f"[🟢] {cookie.get('name')} (session)")
    return cookies


def create_cookies():
    """Create new cookies on wordpress!"""
    driver = webdriver.Remote(
        command_executor=SELENIUM_HUB, options=webdriver.ChromeOptions()
    )
    print("Creating New Cookies!")
    with driver:
        driver.get(LOGIN_PAGE)
        print("Fill Credentials")
        elem = driver.find_element(By.XPATH, USERNAME_XPATH)
        elem.send_keys(USERNAME)
        elem = driver.find_element(By.XPATH, PASSWORD_XPATH)
        elem.send_keys(PASSWORD)
        elem = driver.find_element(By.XPATH, CHECKBOX_XPATH)
        elem.click()
        try:
            print("Login")
            elem = driver.find_element(By.XPATH, LOGIN_XPATH)
            elem.click()
        except NoSuchElementException as missing:
            print(missing.message)
        except TimeoutException as timeout:
            print(timeout.message)
        time.sleep(10)
        cookies = driver.get_cookies()
        r.set("cookies", pickle.dumps(cookies))
        driver.close()
        return cookies


def is_selenium_available():
    """Check if selenium is available"""
    response = requests.get(SELENIUM_URL + "/ui/index.html")
    status = response.status_code
    if status != 200:
        accessible = False
    else:
        accessible = True
    return accessible, status


def is_redis_available():
    """Check if redis is ready!"""
    try:
        r.memory_stats()
    except (redis.exceptions.ConnectionError, redis.exceptions.BusyLoadingError, redis.exceptions.TimeoutError):
        return False
    return True


@app.api_route("/cookies", response_class=ORJSONResponse)
def get_cookies_json(response: Response):
    """Geneare payload of cookies in json format"""
    checks = do_checks()
    if checks[0] == 0 :
        message = get_cookies()
    else:
        message = checks[1]
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return message


def get_cookies():
    """Get cookies or try generatin new ones"""
    cookies = get_cookies_redis()
    if not cookies:
        print("Validazione Cookie fallita, avvio la rigenerazione")
        cookies = create_cookies()
    return cookies


@app.api_route("/morning", response_class=ORJSONResponse, status_code=200)
async def get_morning_url(response: Response, force: Union[str, None] = None, fresh: Union[str, None] = None, newcookies: Union[str, None] = None):
    """Give back payload of our loved podcast!"""
    checks = do_checks()
    if checks[0] == 0:
        print("Checks Ok")
        if force is not None:
            newcookies = True
            fresh = True

        if newcookies is not None:
            print("---> Forcing new Cookies")
            create_cookies()
        now = time.time()
        last_scrape = (
            0 if r.get("last_scrape") is None else pickle.loads(r.get("last_scrape"))
        )
        if ((now - last_scrape) > CACHE_TIME) or fresh is not None:
            update_morning_url()
            last_scrape = pickle.loads(r.get("last_scrape"))

        last_change = (
            0 if r.get("last_change") is None else pickle.loads(r.get("last_change"))
        )

        old_morning = (
            "Null"
            if r.get("old_morning") is None
            else pickle.loads(r.get("old_morning"))
        )
        morning = "Null" if r.get("morning") is None else pickle.loads(r.get("morning"))

        last_change_human = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_change))
        last_scrape_human = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_scrape))

        message = {
            "morning": morning,
            "old_morning": old_morning,
            "last_scrape_info": {
                "last_scrape": last_scrape,
                "last_scrape_human_time": last_scrape_human
            },
            "last_change_info": {
                "last_change": last_change,
                "last_change_human_time": last_change_human
            }
        }
    else:
        message = checks[1]
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return message


def update_morning_url():
    """Scrape the new podcast"""
    cookies = get_cookies()
    driver = webdriver.Remote(
        command_executor=SELENIUM_HUB, options=webdriver.ChromeOptions()
    )
    with driver:
        print("Navigate to Morning Post Page")
        driver.get("https://ilpost.it")
        driver.delete_all_cookies()
        for cookie in cookies:
            if cookie.get("domain") == ".ilpost.it":
                driver.add_cookie(cookie)
        time.sleep(5)
        print("Loading page")
        driver.get(MORNING_PAGE)
        elem = driver.find_element(By.XPATH, MORNING_TODAY_XPATH)
        morning = elem.get_attribute("src")
        driver.close()
        last_scrape = time.time()
        old_morning = (
            "Null" if r.get("morning") is None else pickle.loads(r.get("morning"))
        )

        if old_morning != morning:
            r.set("old_morning", pickle.dumps(old_morning))
            r.set("morning", pickle.dumps(morning))
            r.set("last_change", pickle.dumps(last_scrape))
        r.set("last_scrape", pickle.dumps(last_scrape))
        response = {
            "morning": morning,
            "old_morning": old_morning,
            "last_scrape": last_scrape,
            "last_change": last_scrape,
        }
        return response

@app.get("/", response_class=HTMLResponse, status_code=200)
async def main():
    """Main Page"""
    response = "<center><p>Go away sucker</p></center>"
    return response

def do_checks():
    """Health Checks"""
    print("Starting Checks")

    print("Check Selenium")
    selenium_status = is_selenium_available()

    print("Check Redis")
    redis_status = is_redis_available()

    exit_code=0
    ok_code=200
    ko_code=500

    if not selenium_status[0]:
        print("Selenium Failed")
        selenium_state="Connection to Selenium Failed"
        selenium_state_code=ko_code
        exit_code=exit_code+1
    else:
        selenium_state="ok"
        selenium_state_code=ok_code

    if not redis_status:
        print("Redis Failed")
        redis_state = "Connection to Redis Failed"
        redis_state_code=ko_code
        exit_code=exit_code+1
    else:
        redis_state = "ok"
        redis_state_code=ok_code

    if not USERNAME or not PASSWORD:
        print("Credentials Failed")
        creds_state = "Missing credentials"
        creds_state_code=ko_code
        exit_code=exit_code+1
    else:
        creds_state = "ok"
        creds_state_code=ok_code

    message = {
        "selenium": {
            "state": selenium_state,
            "state_code": selenium_state_code
            },
        "redis": {
            "state ": redis_state,
            "state_code": redis_state_code
        },
        "credentials": {
            "state ": creds_state ,
            "state_code": creds_state_code
        }
    }
    print("Finished Checks")
    print(exit_code)
    return exit_code, message


@app.get("/ping", response_class=PlainTextResponse, status_code=200)
async def ping():
    """Pong"""
    return "pong"

@app.get("/status", response_class=ORJSONResponse, status_code=200)
async def status_page(response: Response):
    checks = do_checks()
    if checks[0] > 0: 
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return checks[1]


@app.api_route('/hello', response_class=PlainTextResponse, status_code=200)
async def hello():
    return "Hello World!"
