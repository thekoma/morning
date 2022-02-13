#!/usr/bin/env python3
"""This stupid webapp catches the latest morning post from ilpost.it ."""
import json
import os
import pickle
import time

import redis
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from werkzeug.middleware.proxy_fix import ProxyFix

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
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)


def get_cookies_redis():
    """Return false if redis has no cookies.
    Otherwise return cookies."""
    pickled_cookies = r.get("cookies")
    cookies = pickle.loads(pickled_cookies)
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
                    cookies=None
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
        # print("Accept Cookie thing")
        # elem = driver.find_element(By.XPATH, accept_button_xpath)
        # elem.click()
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
        accessible=False
    else:
        accessible=True
    return accessible, status



def is_redis_available():
    """Check if redis is ready!"""
    try:
        r.memory_stats()
    except (redis.exceptions.ConnectionError, redis.exceptions.BusyLoadingError):
        return False
    return True


@app.route("/cookies")
def get_cookies_json():
    """Geneare payload of cookies in json format"""
    checks = do_checks()
    if checks[0]:
        cookies = get_cookies()
        response = app.response_class(
            response=json.dumps(cookies), status=200, mimetype="application/json"
        )
    else:
        response = checks[1]
    return response


def get_cookies():
    """Get cookies or try generatin new ones"""
    cookies = get_cookies_redis()
    if not cookies:
        print("Validazione Cookie fallita, avvio la rigenerazione")
        cookies = create_cookies()
    return cookies


@app.route("/morning")
def get_morning_url():
    """Give back payload of our loved podcast!"""
    force = request.args.get("force")
    fresh = request.args.get("fresh")
    newcookies = request.args.get("newcookies")
    if force is not None:
        newcookies = True
        fresh = True

    if newcookies is not None:
        print("---> Forcing new Cookies")
        create_cookies()

    checks = do_checks()
    if checks[0]:
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

        response=jsonify(
            morning=morning,
            old_morning=old_morning,
            last_scrape=last_scrape,
            last_change=last_change,
        )
    else:
        response = checks[1]
    return response


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
        return jsonify(
            morning=morning,
            old_morning=old_morning,
            last_scrape=last_scrape,
            last_change=last_scrape,
        )


@app.route("/")
def main():
    """Main Page"""
    if not USERNAME or not PASSWORD:
        response = app.response_class(
            response="<p>Missing credentials!</p>", status=500
        )
    else:
        response = app.response_class(response="<p>Hello</p>", status=200)
    return response


def do_checks():
    """Health Checks"""
    print("Starting Checks")

    print("Check Selenium")
    selenium_status = is_selenium_available()

    print("Check Redis")
    redis_status = is_redis_available()

    if not selenium_status[0]:
        print("Selenium Failed")
        response = app.response_class(
            response="Connection to Selenium Failed", status=500
        )
        state = False
    if not redis_status:
        print("Redis Failed")
        response = app.response_class(response="Connection to Redis Failed", status=500)
        state = False
    elif not USERNAME or not PASSWORD:
        print("Credentials Failed")
        response = app.response_class(response="Missing credentials", status=500)
        state = False
    else:
        response = app.response_class(response="ok", status=200)
        state = True
    print("Finished Checks")
    return state, response


@app.route("/ping")
def ping():
    """Pong"""
    checks = do_checks()
    if checks[0]:
        response = app.response_class(response="pong", status=200)
    else:
        response = checks[1]
    return response
