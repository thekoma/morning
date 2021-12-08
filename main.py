import time
import os
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By

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
    driver.close()
    return url

def main():
  if ( not username or not password ):
    print("Missing username or password!")
    return False
  url = get_morning_url()
  print(f"The Morning mp3 is: {url}")

if __name__ == "__main__":
    main()