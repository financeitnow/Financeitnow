from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from scraperUtils import create_undetected_chrome_driver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def accept_cookies(driver):
    """
    Handles clicking the 'Accept All' cookie button, both on the main page and within iframes.
    """
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
    except Exception as e:
        print("No iframe appeared:", e)

    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Found {len(iframes)} iframes")
    for idx, iframe in enumerate(iframes):
        print(f"Iframe {idx}: {iframe.get_attribute('outerHTML')[:200]}")

    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All')]"))
        ).click()
        print("Clicked Accept All by text")
        time.sleep(1)
    except Exception as e:
        print("Accept All not found by text:", e)
        for idx, iframe in enumerate(iframes):
            try:
                driver.switch_to.frame(iframe)
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.sp_choice_type_11"))
                ).click()
                print(f"Clicked Accept All in iframe {idx}")
                time.sleep(1)
                driver.switch_to.default_content()
                break
            except Exception as e2:
                driver.switch_to.default_content()
                print(f"Accept All not found in iframe {idx}: {e2}")

def get_full_stock_html(stock_url, scroll_pause=2, max_scrolls=30):
    driver = create_undetected_chrome_driver()
    driver.get(stock_url)

    # Use the new accept_cookies utility function
    accept_cookies(driver)

    buttons = driver.find_elements(By.TAG_NAME, "button")
    for idx, b in enumerate(buttons):
        print(f"Button {idx} text: '{b.text}' class: '{b.get_attribute('class')}'")

    # Now scroll as before
    last_height = driver.execute_script("return document.body.scrollHeight")
    scrolls = 0
    while scrolls < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scrolls += 1
    html = driver.page_source
    driver.quit()
    return html


