import random
import time
import undetected_chromedriver as uc


def create_undetected_chrome_driver(proxy=None, log_output=None):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    ]
    languages = ["en-US,en;q=0.9", "en-GB,en;q=0.8", "fr-FR,fr;q=0.7", "de-DE,de;q=0.7"]
    timezones = ["Europe/London", "Europe/Paris", "America/New_York", "Asia/Kolkata"]
    options = uc.ChromeOptions()
    options.add_argument(f"--user-agent={random.choice(user_agents)}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--lang={random.choice(languages)}")
    if proxy:
        proxy_url = proxy if proxy.startswith("http") else f"http://{proxy}"
        options.add_argument(f'--proxy-server={proxy_url}')
        if log_output:
            log_output(f"[Proxy] Using proxy: {proxy_url}\n")
    else:
        if log_output:
            log_output("[Proxy] No proxy available, using direct connection.\n")
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=147)
    driver.maximize_window()
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    js_code = f'''
        Object.defineProperty(navigator, 'languages', {{get: () => ['{random.choice(['en-US','en','fr','de'])}']}});
        Object.defineProperty(navigator, 'platform', {{get: () => '{random.choice(['Win32','MacIntel','Linux x86_64'])}'}});
        Object.defineProperty(navigator, 'vendor', {{get: () => '{random.choice(['Google Inc.','Apple Computer, Inc.',''])}'}});
        Object.defineProperty(Intl.DateTimeFormat().resolvedOptions(), 'timeZone', {{get: () => '{random.choice(timezones)}'}});
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{random.choice(['Intel Inc.','NVIDIA Corporation','AMD'])}';
            if (parameter === 37446) return '{random.choice(['Intel Iris OpenGL','NVIDIA GeForce GTX 1050','AMD Radeon RX 580'])}';
            return getParameter.call(this, parameter);
        }};
    '''
    driver.execute_script(js_code)
    return driver


def human_like_browsing(driver, min_scrolls=1, max_scrolls=4):
    """
    Simulate human-like behavior: random scrolls, delays, and small interactions.
    """
    time.sleep(random.uniform(1.5, 4.5))
    for _ in range(random.randint(min_scrolls, max_scrolls)):
        direction = random.choice([-1, 1])
        scroll_amount = random.randint(200, 800) * direction
        driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_amount)
        time.sleep(random.uniform(0.3, 1.2))
    driver.execute_script("window.scrollTo(0, arguments[0]);", random.randint(400, 800))
    time.sleep(random.uniform(0.5, 1.2))

def ad_is_deleted(page_source):
    """
    Returns True if the ad is deleted (based on known phrase), else False.
    """
    sold_phrase = "The advert you are looking for is no longer available but we’ve found some similar vehicles for sale that match your search criteria"
    return sold_phrase in page_source
