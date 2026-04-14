import tkinter as tk
from tkinter import messagebox
from scraper import Scraper
from extract_car_data import extract_car_data
from selenium_utils import get_full_stock_html, accept_cookies
import json
import os
import requests
from collections import OrderedDict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import undetected_chromedriver as uc
import random
from scraperUtils import human_like_browsing, ad_is_deleted, create_undetected_chrome_driver
import tkinter.ttk as ttk
import threading



def checkAdsBS():
    """
    Test version: Checks only the first 2 car listings using requests + BeautifulSoup and a proxy.
    Prints the listing URL, the FULL HTML content, and whether it exists or does not exist in the GUI terminal.
    Also saves the HTML content to a file for each checked ad.
    """
    import json
    import requests
    from bs4 import BeautifulSoup
    import time
    # Load cars
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cars_file = os.path.join(base_dir, "data", "cars.json")
    with open(cars_file, "r", encoding="utf-8") as f:
        cars = json.load(f)
    manual_proxy = proxy_entry.get().strip() if 'proxy_entry' in globals() else ''
    max_checks = min(2, len(cars))
    for idx in range(max_checks):
        car = cars[idx]
        url = car.get("listing_url")
        if not url:
            msg = f"[{idx+1}] No URL for car index {idx}\n"
            print(msg.strip())
            output_text.insert(tk.END, msg)
            continue
        proxy = manual_proxy if manual_proxy else get_next_proxy()
        # Always set the proxy in the manual proxy entry box
        if 'proxy_entry' in globals() and proxy_entry.winfo_exists():
            proxy_entry.delete(0, tk.END)
            proxy_entry.insert(0, proxy)
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
        msg_proxy = f"[{idx+1}] Using proxy: {proxy}\n"
        print(msg_proxy.strip())
        output_text.insert(tk.END, msg_proxy)
        try:
            resp = requests.get(url, proxies=proxies, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            html_filename = os.path.join(base_dir, f"data/checked_ad_{idx+1}.html")
            with open(html_filename, "w", encoding="utf-8") as html_file:
                html_file.write(resp.text)
            print(f"[{idx+1}] FULL HTML saved to {html_filename}\n---END HTML---\n")
            if ad_is_deleted(resp.text):
                msg = f"[{idx+1}] {url} - DOES NOT EXIST\n"
            else:
                msg = f"[{idx+1}] {url} - EXISTS\n"
            print(msg.strip())
            output_text.insert(tk.END, msg)
        except Exception as e:
            err_msg = f"[{idx+1}] {url} - ERROR: {e}\n"
            print(err_msg.strip())
            output_text.insert(tk.END, err_msg)
    summary = f"\nChecked {max_checks} ads for existence.\n"
    output_text.insert(tk.END, summary)

def save_dealer_to_json(dealer_info, dealers_file=None):
    if dealers_file is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dealers_file = os.path.join(base_dir, "data", "dealers.json")
    os.makedirs(os.path.dirname(dealers_file), exist_ok=True)
    if os.path.exists(dealers_file):
        with open(dealers_file, "r") as f:
            try:
                dealers = json.load(f)
            except json.JSONDecodeError:
                dealers = []
    else:
        dealers = []
    if not any(d['dealer_name'] == dealer_info['dealer_name'] for d in dealers):
        dealers.append(dealer_info)
        with open(dealers_file, "w") as f:
            json.dump(dealers, f, indent=2)
        return True
    return False

def scrape_dealer():
    main_url = main_url_entry.get()
    stock_url = stock_url_entry.get()
    if not main_url or not stock_url:
        messagebox.showerror("Error", "Please enter both URLs.")
        return
    try:
        scraper = Scraper(base_url=main_url)
        main_html = scraper.fetch_page(main_url)
        dealer_info = scraper.parse_dealer_info(main_html, main_url)
        dealer_info.pop('url', None)
        dealer_info['mainURL'] = main_url
        dealer_info['stockURL'] = stock_url

        # --- Extract postcode from address and split into front/back ---
        address = dealer_info.get('address', '').strip()
        parts = address.split()
        if len(parts) >= 2:
            dealer_info['frontOfPostCode'] = parts[-2]
            dealer_info['backOfPostCode'] = parts[-1]
            dealer_info['postcode'] = f"{parts[-2]} {parts[-1]}"
        else:
            dealer_info['frontOfPostCode'] = ""
            dealer_info['backOfPostCode'] = ""
            dealer_info['postcode'] = ""

        output_text.insert(tk.END, json.dumps(dealer_info, indent=2))
        added = save_dealer_to_json(dealer_info)
        if added:
            messagebox.showinfo("Success", "Dealer info saved to dealers.json.")
        else:
            messagebox.showinfo("Info", "Dealer already exists in dealers.json.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to scrape dealer: {e}")

def extract_cars():
    stock_url = stock_url_entry.get()
    if not stock_url:
        messagebox.showerror("Error", "Please enter the Stock Page URL.")
        return
    try:
        response = requests.get(stock_url)
        if response.status_code == 200:
            car_list = extract_car_data(response.text)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cars_file = os.path.join(base_dir, "data", "cars.json")
            with open(cars_file, "w", encoding="utf-8") as f:
                json.dump(car_list, f, ensure_ascii=False, indent=2)
            output_text.insert(tk.END, json.dumps(car_list, indent=2))
            messagebox.showinfo("Success", f"Extracted {len(car_list)} cars and saved to cars.json.")
        else:
            messagebox.showerror("Error", f"Failed to fetch stock page: {response.status_code}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to extract cars: {e}")

def clean_price(price_str):
    # Remove £ and commas, handle +VAT, Inc VAT, No VAT, then convert to int
    if not price_str:
        return 0
    price_str = price_str.replace('£', '').replace(',', '').strip()
    price_str_upper = price_str.upper()
    is_vat = False
    # Only multiply by 1.2 if +VAT is present and NOT Inc VAT or No VAT
    if '+VAT' in price_str_upper and 'NO VAT' not in price_str_upper and 'INC VAT' not in price_str_upper:
        is_vat = True
        price_str = price_str_upper.replace('+VAT', '').strip()
    else:
        # Remove Inc VAT or No VAT text if present, but do not multiply
        price_str = price_str_upper.replace('INC VAT', '').replace('NO VAT', '').strip()
    try:
        price = float(price_str)
        if is_vat:
            price = int(round(price * 1.2))
        else:
            price = int(round(price))
        return price
    except Exception:
        return 0

def scrape_all():
    main_url = main_url_entry.get()
    stock_url = stock_url_entry.get()
    if not main_url or not stock_url:
        messagebox.showerror("Error", "Please enter both URLs.")
        return
    try:
        # Scrape dealer info
        scraper = Scraper(base_url=main_url)
        main_html = scraper.fetch_page(main_url)
        dealer_info = scraper.parse_dealer_info(main_html, main_url)
        dealer_info.pop('url', None)
        dealer_info['mainURL'] = main_url
        dealer_info['stockURL'] = stock_url

        # --- Extract postcode from address and split into front/back ---
        address = dealer_info.get('address', '').strip()
        parts = address.split()
        if len(parts) >= 2:
            dealer_info['frontOfPostCode'] = parts[-2]
            dealer_info['backOfPostCode'] = parts[-1]
            dealer_info['postcode'] = f"{parts[-2]} {parts[-1]}"
        else:
            dealer_info['frontOfPostCode'] = ""
            dealer_info['backOfPostCode'] = ""
            dealer_info['postcode'] = ""

        save_dealer_to_json(dealer_info)
        # Scrape car stock info using Selenium
        full_html = get_full_stock_html(stock_url)
        with open("full_stock_page.html", "w", encoding="utf-8") as f:
            f.write(full_html)
        car_list = extract_car_data(full_html)

        # Add dealer_name and dealer_id to each car
        for car in car_list:
            car["dealer_name"] = dealer_info.get("dealer_name")
            car["dealer_id"] = dealer_info.get("dealer_id")
            car["frontOfPostCode"] = dealer_info.get("frontOfPostCode", "")
            car["backOfPostCode"] = dealer_info.get("backOfPostCode", "")
            car["postcode"] = dealer_info.get("postcode", "")
            # Split title into make and model
            if "title" in car and car["title"]:
                parts = car["title"].split(" ", 1)
                car["make"] = parts[0]
                car["model"] = parts[1] if len(parts) > 1 else ""
                del car["title"]  # Remove the old title field if you don't want it
            # Clean and convert price
            if "price" in car and isinstance(car["price"], str):
                try:
                    car["price"] = clean_price(car["price"])
                except Exception:
                    car["price"] = 0

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cars_file = os.path.join(base_dir, "data", "cars.json")
        # Read existing cars if file exists
        if os.path.exists(cars_file):
            with open(cars_file, "r", encoding="utf-8") as f:
                try:
                    existing_cars = json.load(f)
                except Exception:
                    existing_cars = []
        else:
            existing_cars = []

        # Append new cars, avoiding duplicates by car_id
        existing_car_ids = {car["car_id"] for car in existing_cars if "car_id" in car}
        for car in car_list:
            if car.get("car_id") not in existing_car_ids:
                existing_cars.append(car)

        # Remove 'url' and reorder fields before saving
        ordered_cars = []
        for car in existing_cars:
            car.pop("url", None)  # Remove 'url' if present
            car["imageScraped"] = car.get("imageScraped", False)  # Add or preserve the flag
            ordered_car = OrderedDict()
            ordered_car["make"] = car.get("make", "")
            ordered_car["model"] = car.get("model", "")
            ordered_car["imageScraped"] = car["imageScraped"]
            for key in car:
                if key not in ("make", "model", "imageScraped"):
                    ordered_car[key] = car[key]
            ordered_cars.append(ordered_car)

        with open(cars_file, "w", encoding="utf-8") as f:
            json.dump(ordered_cars, f, ensure_ascii=False, indent=2)

        output_text.insert(tk.END, json.dumps({
            "dealer_info": dealer_info,
            "cars": car_list
        }, indent=2))
        msg = "Dealer info saved.\n"
        msg += f"Extracted {len(car_list)} cars and saved to cars.json."
        messagebox.showinfo("Success", msg)
        # Refresh the programme to update tables and stock counts
        refresh_programme()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to scrape: {e}")

def fetch_free_proxies(limit=20, timeout=5):
    """
    Fetches a list of free proxies from multiple sources and validates them.
    Returns a list of working proxies in 'ip:port' format.
    """
    from bs4 import BeautifulSoup
    sources = [
        ("https://www.sslproxies.org/", "sslproxies"),
        ("https://free-proxy-list.net/", "freeproxylist"),
        ("https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all", "proxyscrape"),
        ("https://spys.me/proxy.txt", "spysme"),
        ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", "speedx"),
        ("https://proxyspace.pro/http.txt", "proxyspace"),
        ("https://www.proxyscan.io/download?type=http", "proxyscan"),
        ("https://www.proxy-list.download/api/v1/get?type=http", "proxylistdownload"),
    ]
    proxies = []
    regex = r"[0-9]+(?:\.[0-9]+){3}:[0-9]+"  # Correct regex for IP:PORT
    for url, src in sources:
        try:
            print(f"[ProxyDebug] Fetching from {url} ({src})...")
            resp = requests.get(url, timeout=timeout)
            print(f"[ProxyDebug] First 500 chars from {src}:\n{resp.text[:500]}\n---END RESPONSE---\n")
            if src in ("sslproxies", "freeproxylist"):
                soup = BeautifulSoup(resp.text, "html.parser")
                table = soup.find("table", attrs={"id": "proxylisttable"})
                if table:
                    for row in table.tbody.find_all("tr"):
                        cols = row.find_all("td")
                        if len(cols) >= 2:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            proxy = f"{ip}:{port}"
                            proxies.append(proxy)
                print(f"[ProxyDebug] {len(proxies)} proxies so far after {src}")
            elif src == "proxyscrape":
                found = re.findall(regex, resp.text)
                proxies.extend(found)
                print(f"[ProxyDebug] {len(found)} proxies found from {src}, {len(proxies)} total")
            elif src in ("spysme", "speedx", "proxyspace", "proxyscan", "proxylistdownload"):
                found = re.findall(regex, resp.text)
                proxies.extend(found)
                print(f"[ProxyDebug] {len(found)} proxies found from {src}, {len(proxies)} total")
            if len(proxies) >= limit:
                print(f"[ProxyDebug] Reached limit ({limit}) after {src}")
                break
        except Exception as e:
            print(f"[ProxyDebug] Error fetching proxies from {url}: {e}")
            continue
    print(f"[ProxyDebug] Total proxies fetched before validation: {len(proxies)}")
    # Validate proxies
    # Validate proxies in parallel
    import concurrent.futures
    working = []
    test_url = "https://httpbin.org/ip"
    max_workers = min(20, limit * 2)  # Don't spawn too many threads
    def test_proxy(proxy):
        try:
            print(f"[ProxyDebug] Testing proxy {proxy}...")
            resp = requests.get(test_url, proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"}, timeout=3)
            if resp.status_code == 200:
                print(f"[ProxyDebug] Proxy {proxy} is working.")
                return proxy
            else:
                print(f"[ProxyDebug] Proxy {proxy} failed with status {resp.status_code}")
        except Exception as e:
            print(f"[ProxyDebug] Proxy {proxy} failed: {e}")
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxies}
        for future in concurrent.futures.as_completed(future_to_proxy):
            result = future.result()
            if result:
                working.append(result)
                print(f"[ProxyDebug] {len(working)} valid so far.")
                if len(working) >= limit:
                    print(f"[ProxyDebug] Reached working proxy limit ({limit})")
                    break
    print(f"[ProxyDebug] Total working proxies: {len(working)}")
    return working

def normalize_image_url(url):
    # Replace /media/wXXX/ with /media/w1024/
    return re.sub(r'/media/w\d+/', '/media/w1024/', url)

# --- Proxy Rotation Setup ---
_PROXIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "proxies.json")

def _load_proxies_from_file():
    if os.path.exists(_PROXIES_FILE):
        try:
            with open(_PROXIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _save_proxies_to_file(proxy_list):
    os.makedirs(os.path.dirname(_PROXIES_FILE), exist_ok=True)
    with open(_PROXIES_FILE, "w", encoding="utf-8") as f:
        json.dump(proxy_list, f, indent=2)

PROXY_LIST = _load_proxies_from_file()
_proxy_index = 0

def get_next_proxy():
    global _proxy_index, PROXY_LIST
    if not PROXY_LIST:
        # Fetch and cache proxies if not already done
        PROXY_LIST = fetch_free_proxies(limit=20)
        _proxy_index = 0
    if not PROXY_LIST:
        return None
    proxy = PROXY_LIST[_proxy_index % len(PROXY_LIST)]
    _proxy_index += 1
    # Always set the proxy in the manual proxy entry box for user reuse
    if 'proxy_entry' in globals() and proxy_entry.winfo_exists():
        proxy_entry.delete(0, tk.END)
        proxy_entry.insert(0, proxy)
    return proxy

def get_undetected_chrome_driver(proxy=None, log_output=None):
    # Resolve proxy: prefer manual entry box, then passed proxy, then auto-fetch
    manual_proxy = proxy_entry.get().strip() if 'proxy_entry' in globals() else ''
    if manual_proxy:
        proxy = manual_proxy
        if log_output:
            log_output(f"[Proxy] Using manual proxy: {proxy}\n")
    if not proxy:
        proxy = get_next_proxy()
    return create_undetected_chrome_driver(proxy=proxy, log_output=log_output if not manual_proxy else None)

def scrape_images_for_unscraped_cars():
    scrape_images_and_information_for_unscraped_cars(mode='images')

def scrape_vehicle_information():
    scrape_images_and_information_for_unscraped_cars(mode='info')

def scrape_images_and_information_for_unscraped_cars(mode='both'):  # mode: 'both', 'images', 'info'
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup
    from selenium_utils import accept_cookies

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cars_file = os.path.join(base_dir, "data", "cars.json")
    with open(cars_file, "r", encoding="utf-8") as f:
        all_cars = json.load(f)

    # --- Filter cars if a dealer is selected ---
    dealer = selected_dealer["dealer"] if 'selected_dealer' in globals() else None
    if dealer:
        dealer_id = dealer.get("dealer_id")
        cars_to_process = [car for car in all_cars if str(car.get("dealer_id")) == str(dealer_id)]
        if not cars_to_process:
            messagebox.showinfo("No Cars", f"No cars found for dealer: {dealer.get('dealer_name','')}")
            return
    else:
        cars_to_process = all_cars[:]

    # Check if all cars are already scraped (based on mode)
    def _needs_scraping(car):
        if mode == 'images': return not car.get('imageScraped', False)
        if mode == 'info':   return not car.get('informationScraped', False)
        return not car.get('imageScraped', False) or not car.get('informationScraped', False)
    if all(not _needs_scraping(car) for car in cars_to_process):
        try:
            messagebox.showinfo("Complete", "All vehicles have been scraped.")
        except Exception:
            print("All vehicles have been scraped.")
        return

    mode_label = {'images': 'Scrape Images', 'info': 'Scrape Vehicle Info', 'both': 'Scrape Images & Info'}[mode]
    manual_proxy = proxy_entry.get().strip() if 'proxy_entry' in globals() else ''
    proxy = manual_proxy if manual_proxy else get_next_proxy()
    if 'output_text' in globals():
        try:
            output_text.insert(tk.END, f"[{mode_label}] Using proxy: {proxy if proxy else 'None (direct connection)'}\n")
        except Exception:
            pass
    else:
        print(f"[{mode_label}] Using proxy: {proxy if proxy else 'None (direct connection)'}")

    driver = get_undetected_chrome_driver()
    cookies_accepted = False
    idx = len(cars_to_process) - 1
    while idx >= 0:
        car = cars_to_process[idx]
        if not _needs_scraping(car):
            idx -= 1
            continue  # Skip cars that don't need scraping in this mode
        need_save = False
        print(f"Processing {car.get('make','')} {car.get('model','')} ({car.get('car_id','')})")
        driver.get(car["listing_url"])
        time.sleep(random.uniform(4, 8))
        if not cookies_accepted:
            try:
                accept_cookies(driver)
                cookies_accepted = True
                print("Accepted cookies dialog.")
            except Exception as e:
                print(f"Could not accept cookies: {e}")
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except Exception:
            print("Timeout waiting for page body to load.")
        # Check if ad is deleted
        if ad_is_deleted(driver.page_source):
            print(f"Ad no longer available: {car.get('listing_url')}")
            # Remove from all_cars and cars_to_process
            car_id = car.get("car_id")
            all_cars = [c for c in all_cars if c.get("car_id") != car_id]
            del cars_to_process[idx]
            with open(cars_file, "w", encoding="utf-8") as f:
                json.dump(all_cars, f, ensure_ascii=False, indent=2)
            try:
                output_text.insert(tk.END, f"Ad no longer available and deleted: {car.get('listing_url')}\n")
            except Exception:
                pass
            idx -= 1
            continue
        # --- Random scrolling ---
        page_height = driver.execute_script("return document.body.scrollHeight")
        scroll_steps = random.randint(3, 7)
        scroll_positions = sorted(random.sample(range(0, page_height, max(1, page_height // (scroll_steps + 1))), scroll_steps))
        if random.choice([True, False]):
            scroll_positions = scroll_positions[::-1]
        for pos in scroll_positions:
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(random.uniform(1.2, 2.5))
        if random.choice([True, False]):
            driver.execute_script("window.scrollTo(0, 0);")
        else:
            driver.execute_script(f"window.scrollTo(0, {page_height});")
        time.sleep(random.uniform(1.5, 3.0))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # --- Scrape vehicle information if needed in this mode ---
        if mode in ('both', 'info') and not car.get("informationScraped", False):
            # All overview fields from data-testid="overview" section
            overview_fields = {
                "Fuel type": "fuel_type",
                "Gearbox": "gearbox",
                "Engine": "engine",
                "Body type": "body_type",
                "Doors": "doors",
                "Seats": "seats",
                "Owners": "owners",
                "Emission class": "emission_class",
                "Body colour": "body_colour",
            }
            for k in overview_fields.values():
                car[k] = "Unknown"
            overview_section = soup.find('section', {'data-testid': 'overview'})
            if overview_section:
                for card in overview_section.find_all('div', class_=re.compile(r'sc-tqnfbs-4')):
                    label_p = card.find('p', class_=re.compile(r'sc-tqnfbs-5'))
                    value_p = card.find('p', class_=re.compile(r'sc-tqnfbs-6'))
                    if label_p and value_p:
                        label = label_p.get_text(strip=True)
                        value = value_p.get_text(strip=True)
                        if label in overview_fields:
                            car[overview_fields[label]] = value
            car["informationScraped"] = True
            need_save = True
            print(f"Scraped vehicle info for {car.get('make','')} {car.get('model','')}")
        # --- Scrape images if needed in this mode ---
        if mode in ('both', 'images') and not car.get("imageScraped", False):
            clicked_gallery = False
            try:
                gallery_btn = WebDriverWait(driver, 12).until(
                    EC.presence_of_element_located((By.XPATH, "//button[.//span[text()='Gallery']]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gallery_btn)
                time.sleep(random.uniform(0.5, 1.0))
                try:
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Gallery']]"))
                    ).click()
                except Exception:
                    driver.execute_script("arguments[0].click();", gallery_btn)
                print("Clicked Gallery button.")
                clicked_gallery = True
                # Wait for gallery images to actually appear after click
                try:
                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "button.image-gallery-item img"))
                    )
                except Exception:
                    print("Gallery images did not appear after click, will still try to parse.")
                time.sleep(random.uniform(1.5, 2.5))
            except Exception as e:
                print(f"Gallery button not found: {e}")
            soup = BeautifulSoup(driver.page_source, "html.parser")
            new_images = []
            for img in soup.select("button.image-gallery-item img"):
                src = img.get("src")
                if src:
                    normalized = normalize_image_url(src)
                    if normalized not in new_images:
                        new_images.append(normalized)
            if new_images:
                car["images"] = new_images
                car["imageScraped"] = True
                need_save = True
                print(f"Found {len(new_images)} images.")
            else:
                print(f"WARNING: No images found for {car.get('make','')} {car.get('model','')} — imageScraped left as False, will retry next run.")
        # --- More natural random scrolling (max 60% of page height, similar to vehicle info) ---
        human_like_browsing(driver)
        # Always scroll to top before scraping images
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(0.2, 0.5))
        if need_save:
            # Update the car in all_cars
            car_id = car.get("car_id")
            for i, c in enumerate(all_cars):
                if c.get("car_id") == car_id:
                    all_cars[i] = car
                    break
            with open(cars_file, "w", encoding="utf-8") as f:
                json.dump(all_cars, f, ensure_ascii=False, indent=2)
        idx -= 1
    driver.quit()
    # Final save (optional)
    with open(cars_file, "w", encoding="utf-8") as f:
        json.dump(all_cars, f, ensure_ascii=False, indent=2)

def delete_sold_vehicles():
    import json
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup
    from selenium_utils import accept_cookies

    def log(msg):
        output_text.insert(tk.END, msg)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cars_file = os.path.join(base_dir, "data", "cars.json")
    with open(cars_file, "r", encoding="utf-8") as f:
        cars = json.load(f)

    driver = get_undetected_chrome_driver(log_output=log)
    cookies_accepted = False
    sold_phrase = "The advert you are looking for is no longer available but we’ve found some similar vehicles for sale that match your search criteria"
    deleted_count = 0

    # Clear the output_text box for new run

    # Iterate in reverse so we can safely delete by index
    for idx in range(len(cars) - 1, -1, -1):
        car = cars[idx]
        print(f"Checking {car.get('make','')} {car.get('model','')} ({car.get('car_id','')})")
        try:
            driver.get(car["listing_url"])
            time.sleep(random.uniform(2, 4))
            if not cookies_accepted:
                try:
                    accept_cookies(driver)
                    cookies_accepted = True
                    print("Accepted cookies dialog.")
                except Exception as e:
                    print(f"Could not accept cookies: {e}")
            page_source = driver.page_source
            if sold_phrase in page_source:
                msg = f"DELETED: {car.get('make','')} {car.get('model','')} ({car.get('car_id','')}) at {car.get('listing_url','')}\n"
                print(msg.strip())
                output_text.insert(tk.END, msg)
                del cars[idx]
                deleted_count += 1
                # Save after each deletion
                with open(cars_file, "w", encoding="utf-8") as f:
                    json.dump(cars, f, ensure_ascii=False, indent=2)
        except Exception as e:
            err_msg = f"Error checking car {car.get('car_id','')}: {e}\n"
            print(err_msg.strip())
            output_text.insert(tk.END, err_msg)
            # Keep car if error occurs
    driver.quit()
    # Final save (optional, for consistency)
    with open(cars_file, "w", encoding="utf-8") as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)
    summary = f"\nDeleted {deleted_count} sold vehicles. {len(cars)} remain.\n"
    output_text.insert(tk.END, summary)
    messagebox.showinfo("Done", summary)

def check_ads():
    import json
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup
    from selenium_utils import accept_cookies
    import random

    def log(msg):
        output_text.insert(tk.END, msg)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cars_file = os.path.join(base_dir, "data", "cars.json")
    with open(cars_file, "r", encoding="utf-8") as f:
        cars = json.load(f)

    driver = get_undetected_chrome_driver(log_output=log)
    cookies_accepted = False
    sold_phrase = "The advert you are looking for is no longer available but we’ve found some similar vehicles for sale that match your search criteria"
    deleted_count = 0


    for idx in range(len(cars) - 1, -1, -1):
        car = cars[idx]
        print(f"Checking {car.get('make','')} {car.get('model','')} ({car.get('car_id','')})")
        try:
            driver.get(car["listing_url"])
            # Human-like random delay
            time.sleep(random.uniform(1.5, 4.5))
            # Simulate a random number of scrolls (0-4), random direction
            for _ in range(random.randint(0, 4)):
                direction = random.choice([-1, 1])
                scroll_amount = random.randint(200, 800) * direction
                driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_amount)
                time.sleep(random.uniform(0.3, 1.2))
            if not cookies_accepted:
                try:
                    accept_cookies(driver)
                    cookies_accepted = True
                    print("Accepted cookies dialog.")
                    time.sleep(random.uniform(1, 2))
                except Exception as e:
                    print(f"Could not accept cookies: {e}")
            # Simulate another small scroll
            driver.execute_script("window.scrollTo(0, arguments[0]);", random.randint(400, 800))
            time.sleep(random.uniform(0.5, 1.2))
            page_source = driver.page_source
            if sold_phrase in page_source:
                msg = f"DELETED: {car.get('make','')} {car.get('model','')} ({car.get('car_id','')}) at {car.get('listing_url','')}\n"
                print(msg.strip())
                output_text.insert(tk.END, msg)
                del cars[idx]
                deleted_count += 1
                # Save after each deletion
                with open(cars_file, "w", encoding="utf-8") as f:
                    json.dump(cars, f, ensure_ascii=False, indent=2)
        except Exception as e:
            err_msg = f"Error checking car {car.get('car_id','')}: {e}\n"
            print(err_msg.strip())
            output_text.insert(tk.END, err_msg)
            # Keep car if error occurs
    driver.quit()
    # Final save (optional, for consistency)
    with open(cars_file, "w", encoding="utf-8") as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)
    summary = f"\nChecked all ads. Deleted {deleted_count} sold vehicles. {len(cars)} remain.\n"
    output_text.insert(tk.END, summary)
    messagebox.showinfo("Done", summary)

def check_ip():
    import time
    def log(msg):
        output_text.insert(tk.END, msg)
    output_text.insert(tk.END, "\n--- Checking Rotated Proxy IP ---\n")
    driver = get_undetected_chrome_driver(log_output=log)
    try:
        driver.get("https://www.whatismyip.com/")
        output_text.insert(tk.END, "Opened https://www.whatismyip.com/ in Chrome.\n")
        time.sleep(10)
        output_text.insert(tk.END, "Closed Chrome after 10 seconds.\n")
    except Exception as e:
        output_text.insert(tk.END, f"Error during IP check: {e}\n")
    finally:
        driver.quit()

# Place this function definition above the GUI layout code that creates the ScrapeCars button

def scrape_cars_for_selected_dealer_gui():
    dealer = selected_dealer["dealer"]
    if not dealer:
        messagebox.showerror("Error", "Please select a dealer from the table.")
        return
    try:
        stock_url = dealer.get("stockURL")
        if not stock_url:
            messagebox.showerror("Error", "Selected dealer does not have a stock URL.")
            return
        manual_proxy = proxy_entry.get().strip() if 'proxy_entry' in globals() else ''
        proxy = manual_proxy if manual_proxy else get_next_proxy()
        if 'output_text' in globals():
            try:
                output_text.insert(tk.END, f"[Scrape Cars] Using proxy: {proxy if proxy else 'None (direct connection)'}\n")
            except Exception:
                pass
        else:
            print(f"[Scrape Cars] Using proxy: {proxy if proxy else 'None (direct connection)'}")
        full_html = get_full_stock_html(stock_url)
        stock_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "full_stock_page.html")
        with open(stock_html_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        if 'output_text' in globals():
            try:
                output_text.insert(tk.END, f"[Scrape Cars] Saved HTML ({len(full_html)} chars) to {stock_html_path}\n")
            except Exception:
                pass
        new_car_list = extract_car_data(full_html)
        if 'output_text' in globals():
            try:
                output_text.insert(tk.END, f"[Scrape Cars] extract_car_data found {len(new_car_list)} cars\n")
            except Exception:
                pass
        for car in new_car_list:
            car["dealer_name"] = dealer.get("dealer_name")
            car["dealer_id"] = dealer.get("dealer_id", "")
            car["frontOfPostCode"] = dealer.get("frontOfPostCode", "")
            car["backOfPostCode"] = dealer.get("backOfPostCode", "")
            car["postcode"] = dealer.get("postcode", "")
            if "title" in car and car["title"]:
                parts = car["title"].split(" ", 1)
                car["make"] = parts[0]
                car["model"] = parts[1] if len(parts) > 1 else ""
                del car["title"]
            if "price" in car and isinstance(car["price"], str):
                try:
                    car["price"] = clean_price(car["price"])
                except Exception:
                    car["price"] = 0
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cars_file = os.path.join(base_dir, "data", "cars.json")
        dealers_file = os.path.join(base_dir, "data", "dealers.json")
        if os.path.exists(cars_file):
            with open(cars_file, "r", encoding="utf-8") as f:
                try:
                    existing_cars = json.load(f)
                except Exception:
                    existing_cars = []
        else:
            existing_cars = []
        existing_cars_for_dealer = [car for car in existing_cars if car.get("dealer_id") == dealer.get("dealer_id")]
        existing_car_ids = {car["car_id"] for car in existing_cars_for_dealer if "car_id" in car}
        new_car_ids = {car["car_id"] for car in new_car_list if "car_id" in car}
        kept_cars = [car for car in existing_cars if car.get("dealer_id") != dealer.get("dealer_id") or car.get("car_id") in new_car_ids]
        added_cars = [car for car in new_car_list if car["car_id"] not in existing_car_ids]
        deleted_cars = [car for car in existing_cars_for_dealer if car["car_id"] not in new_car_ids]
        updated_cars = kept_cars + added_cars
        ordered_cars = []
        for car in updated_cars:
            car.pop("url", None)
            car["imageScraped"] = car.get("imageScraped", False)
            ordered_car = OrderedDict()
            ordered_car["make"] = car.get("make", "")
            ordered_car["model"] = car.get("model", "")
            ordered_car["imageScraped"] = car["imageScraped"]
            for key in car:
                if key not in ("make", "model", "imageScraped"):
                    ordered_car[key] = car[key]
            ordered_cars.append(ordered_car)
        with open(cars_file, "w", encoding="utf-8") as f:
            json.dump(ordered_cars, f, ensure_ascii=False, indent=2)
        # --- Update dealer stock_count in dealers.json ---
        if os.path.exists(dealers_file):
            with open(dealers_file, "r", encoding="utf-8") as f:
                try:
                    dealers_data = json.load(f)
                except Exception:
                    dealers_data = []
            for d in dealers_data:
                if d.get("dealer_id") == dealer.get("dealer_id"):
                    d["stock_count"] = len(new_car_list)
            with open(dealers_file, "w", encoding="utf-8") as f:
                json.dump(dealers_data, f, ensure_ascii=False, indent=2)
        # --- Double check cars.json matches dealer stock_count ---
        cars_for_dealer = [car for car in ordered_cars if car.get("dealer_id") == dealer.get("dealer_id")]
        if len(cars_for_dealer) != len(new_car_list):
            messagebox.showwarning("Stock Count Mismatch", f"Warning: Dealer stock_count is {len(new_car_list)} but cars.json has {len(cars_for_dealer)} cars for this dealer.")
        output_text.insert(tk.END, json.dumps({
            "dealer": dealer,
            "added": len(added_cars),
            "kept": len(kept_cars),
            "deleted": len(deleted_cars),
            "total": len(ordered_cars)
        }, indent=2))
        messagebox.showinfo("Success", f"Scraped cars for {dealer['dealer_name']}\nAdded: {len(added_cars)}\nKept: {len(kept_cars)}\nDeleted: {len(deleted_cars)}\nTotal now: {len(ordered_cars)})")
        # Refresh the programme to update tables and stock counts
        refresh_programme()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to scrape cars for dealer: {e}")

# --- Global Default Manual Proxy ---
DEFAULT_MANUAL_PROXY = ""

# --- Load dealers for dropdown ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dealers_file = os.path.join(base_dir, "data", "dealers.json")
cars_file = os.path.join(base_dir, "data", "cars.json")
try:
    with open(dealers_file, "r", encoding="utf-8") as f:
        dealers_list = json.load(f)
except Exception:
    dealers_list = []

# Count cars per dealer_name
try:
    with open(cars_file, "r", encoding="utf-8") as f:
        cars_list = json.load(f)
except Exception:
    cars_list = []

from collections import Counter
car_counts = Counter(car.get("dealer_name", "") for car in cars_list)

# --- GUI Layout ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Dealer Page Scrape")
    root.resizable(True, True)
    root.geometry("1400x900")  # Set a wider default window size

    # --- Top Frame for Controls ---
    top_frame = tk.Frame(root)
    top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

    # --- Radio Buttons for Dealers/Cars ---
    view_mode = tk.StringVar(value="Dealers")
    radio_frame = tk.Frame(top_frame)
    radio_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
    tk.Radiobutton(radio_frame, text="Dealers", variable=view_mode, value="Dealers").pack(side=tk.LEFT)
    tk.Radiobutton(radio_frame, text="Cars", variable=view_mode, value="Cars").pack(side=tk.LEFT)

    # --- Table Frame ---
    table_frame = tk.Frame(root)
    table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

    # --- Dealers Table (Treeview) ---
    dealer_columns = ["dealer_id", "dealer_name", "stock_count", "address", "phone", "mainURL", "stockURL", "postcode"]
    dealer_tree = ttk.Treeview(table_frame, columns=dealer_columns, show="headings", selectmode="browse")
    for col in dealer_columns:
        dealer_tree.heading(col, text=col)
        dealer_tree.column(col, width=120, anchor="w")
    # Add vertical and horizontal scrollbars
    dealer_vsb = tk.Scrollbar(table_frame, orient="vertical", command=dealer_tree.yview)
    dealer_hsb = tk.Scrollbar(table_frame, orient="horizontal", command=dealer_tree.xview)
    dealer_tree.configure(yscrollcommand=dealer_vsb.set, xscrollcommand=dealer_hsb.set)
    dealer_tree.grid(row=0, column=0, sticky="nsew")
    dealer_vsb.grid(row=0, column=1, sticky="ns")
    dealer_hsb.grid(row=1, column=0, sticky="ew")
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    # Populate dealer table
    def populate_dealer_table():
        dealer_tree.delete(*dealer_tree.get_children())
        for dealer in dealers_list:
            row = [dealer.get(col, "") for col in dealer_columns]
            dealer_tree.insert("", tk.END, values=row)
    populate_dealer_table()

    # --- Cars Table (Treeview, hidden by default) ---
    car_columns = ["car_id", "make", "model", "price", "dealer_id", "dealer_name", "year_reg", "mileage", "postcode"]
    car_tree = ttk.Treeview(table_frame, columns=car_columns, show="headings", selectmode="browse")
    for col in car_columns:
        car_tree.heading(col, text=col)
        car_tree.column(col, width=100, anchor="w")
    # Do not pack car_tree yet

    def populate_car_table():
        car_tree.delete(*car_tree.get_children())
        for car in cars_list:
            row = [car.get(col, "") for col in car_columns]
            car_tree.insert("", tk.END, values=row)

    # --- Switch table view based on radio button ---
    def on_view_mode_change(*args):
        if view_mode.get() == "Dealers":
            car_tree.grid_remove()
            dealer_tree.grid(row=0, column=0, sticky="nsew")
            dealer_vsb.grid(row=0, column=1, sticky="ns")
            dealer_hsb.grid(row=1, column=0, sticky="ew")
            populate_dealer_table()
        else:
            dealer_tree.grid_remove()
            dealer_vsb.grid_remove()
            dealer_hsb.grid_remove()
            car_tree.grid(row=0, column=0, sticky="nsew")
            # Optionally add scrollbars for car_tree if needed
            populate_car_table()
    view_mode.trace_add("write", on_view_mode_change)

    # --- Row selection for dealer actions ---
    selected_dealer = {"dealer": None}
    def on_dealer_row_select(event):
        sel = dealer_tree.selection()
        if sel:
            values = dealer_tree.item(sel[0], "values")
            dealer_id = values[0]
            dealer = next((d for d in dealers_list if str(d.get("dealer_id")) == str(dealer_id)), None)
            selected_dealer["dealer"] = dealer
            # Autofill main_url_entry and stock_url_entry for convenience
            if dealer:
                main_url_entry.delete(0, tk.END)
                main_url_entry.insert(0, dealer.get("mainURL", ""))
                stock_url_entry.delete(0, tk.END)
                stock_url_entry.insert(0, dealer.get("stockURL", ""))
        else:
            selected_dealer["dealer"] = None
    dealer_tree.bind("<<TreeviewSelect>>", on_dealer_row_select)

    # --- Right Controls (URLs, Proxy, Buttons) ---
    right_controls = tk.Frame(top_frame)
    right_controls.pack(side=tk.LEFT, anchor='n', padx=10)

    # Centered label for Main Dealer Info URL
    main_url_label = tk.Label(right_controls, text="Main Dealer Info URL:")
    main_url_label.pack(anchor='center')
    main_url_entry = tk.Entry(right_controls, width=120, justify='center')  # Center text
    main_url_entry.pack(padx=2, pady=2)

    # Centered label for Stock Page URL
    stock_url_label = tk.Label(right_controls, text="Stock Page URL:")
    stock_url_label.pack(anchor='center')
    stock_url_entry = tk.Entry(right_controls, width=120, justify='center')  # Center text
    stock_url_entry.pack(padx=2, pady=2)

    # --- Clear Button for both text boxes ---
    def clear_url_entries():
        main_url_entry.delete(0, tk.END)
        stock_url_entry.delete(0, tk.END)

    clear_btn = tk.Button(right_controls, text="Clear URLs", command=clear_url_entries)
    clear_btn.pack(padx=2, pady=2)

    # Centered label for Manual Proxy
    proxy_label = tk.Label(right_controls, text="Manual Proxy (ip:port, leave blank for auto):")
    proxy_label.pack(anchor='center')
    proxy_entry = tk.Entry(right_controls, width=40, justify='center')
    _startup_proxy = PROXY_LIST[0] if PROXY_LIST else DEFAULT_MANUAL_PROXY
    proxy_entry.insert(0, _startup_proxy)
    proxy_entry.pack(padx=2, pady=2)

    def clear_proxy_entry():
        proxy_entry.delete(0, tk.END)

    proxy_nav_frame = tk.Frame(right_controls)
    proxy_nav_frame.pack(padx=2, pady=2)

    def _set_proxy(index):
        global _proxy_index
        if not PROXY_LIST:
            return
        _proxy_index = index % len(PROXY_LIST)
        proxy_entry.delete(0, tk.END)
        proxy_entry.insert(0, PROXY_LIST[_proxy_index])

    def prev_proxy():
        global _proxy_index
        if not PROXY_LIST:
            return
        _set_proxy(_proxy_index - 1)

    def next_proxy():
        global _proxy_index
        if not PROXY_LIST:
            return
        _set_proxy(_proxy_index + 1)

    def save_proxy_entry():
        global PROXY_LIST, _proxy_index
        proxy = proxy_entry.get().strip()
        if not proxy:
            messagebox.showwarning("Save Proxy", "No proxy entered.")
            return
        if proxy in PROXY_LIST:
            PROXY_LIST.remove(proxy)
        PROXY_LIST.insert(0, proxy)
        _proxy_index = 0
        _save_proxies_to_file(PROXY_LIST)
        messagebox.showinfo("Save Proxy", f"Proxy saved: {proxy}")

    tk.Button(proxy_nav_frame, text="<", width=3, command=prev_proxy).pack(side=tk.LEFT, padx=2)
    clear_proxy_btn = tk.Button(proxy_nav_frame, text="Clear Proxy", command=clear_proxy_entry)
    clear_proxy_btn.pack(side=tk.LEFT, padx=2)
    tk.Button(proxy_nav_frame, text="Save Proxy", command=save_proxy_entry).pack(side=tk.LEFT, padx=2)
    tk.Button(proxy_nav_frame, text=">", width=3, command=next_proxy).pack(side=tk.LEFT, padx=2)

    button_frame = tk.Frame(right_controls)
    button_frame.pack(pady=5, anchor='w')

    def run_in_thread(fn):
        t = threading.Thread(target=fn, daemon=True)
        t.start()

    # --- Function buttons (unchanged, but now all controls are defined above) ---
    tk.Button(button_frame, text="Scrape Dealer & Cars", command=lambda: run_in_thread(scrape_all)).pack(side=tk.LEFT, padx=2)
    scrape_images_button = tk.Button(button_frame, text="Scrape Images", command=lambda: run_in_thread(scrape_images_for_unscraped_cars))
    scrape_images_button.pack(side=tk.LEFT, padx=2)
    scrape_vehicle_info_button = tk.Button(button_frame, text="Scrape Vehicle Information", command=lambda: run_in_thread(scrape_vehicle_information))
    scrape_vehicle_info_button.pack(side=tk.LEFT, padx=2)
    scrape_images_and_info_button = tk.Button(button_frame, text="Scrape Image & Information", command=lambda: run_in_thread(scrape_images_and_information_for_unscraped_cars))
    scrape_images_and_info_button.pack(side=tk.LEFT, padx=2)
    check_ads_button = tk.Button(button_frame, text="Check Ads", command=lambda: run_in_thread(check_ads))
    check_ads_button.pack(side=tk.LEFT, padx=2)
    check_ip_button = tk.Button(button_frame, text="Check IP", command=lambda: run_in_thread(check_ip))
    check_ip_button.pack(side=tk.LEFT, padx=2)

    # --- ScrapeCars button uses new logic ---
    scrape_cars_button = tk.Button(button_frame, text="ScrapeCars", command=lambda: run_in_thread(scrape_cars_for_selected_dealer_gui))
    scrape_cars_button.pack(side=tk.LEFT, padx=2)

    # --- FindProxies button ---
    def find_proxies_gui():
        global PROXY_LIST, _proxy_index
        import requests
        import concurrent.futures
        import re
        output_text.insert(tk.END, "[FindProxies] Searching for working proxies...\n")
        try:
            working = fetch_free_proxies(limit=20)
            # Replace the global proxy list so all scrape functions use fresh proxies
            PROXY_LIST = working
            _proxy_index = 0
            _save_proxies_to_file(working)
            if working:
                output_text.insert(tk.END, f"[FindProxies] Found {len(working)} working proxies. Fetching locations...\n")
                def get_location(proxy):
                    ip = proxy.split(":")[0]
                    try:
                        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=country,regionName,city,query", timeout=5)
                        if resp.status_code == 200:
                            data = resp.json()
                            country = data.get("country", "?")
                            region = data.get("regionName", "?")
                            city = data.get("city", "?")
                            return f"{proxy}  |  {country}, {region}, {city}"
                    except Exception:
                        pass
                    return f"{proxy}  |  Location: Unknown"
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    results = list(executor.map(get_location, working))
                output_text.insert(tk.END, "[FindProxies] Proxy list with locations:\n")
                for line in results:
                    output_text.insert(tk.END, line + "\n")
            else:
                output_text.insert(tk.END, "[FindProxies] No working proxies found.\n")
        except Exception as e:
            output_text.insert(tk.END, f"[FindProxies] Error: {e}\n")

    find_proxies_button = tk.Button(button_frame, text="FindProxies", command=lambda: run_in_thread(find_proxies_gui))
    find_proxies_button.pack(side=tk.LEFT, padx=2)

    # --- Update Dealer Stock Count ---
    def update_dealer_stock_count():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dealers_file = os.path.join(base_dir, "data", "dealers.json")
        cars_file = os.path.join(base_dir, "data", "cars.json")
        try:
            with open(dealers_file, "r", encoding="utf-8") as f:
                dealers = json.load(f)
        except Exception:
            dealers = []
        try:
            with open(cars_file, "r", encoding="utf-8") as f:
                cars = json.load(f)
        except Exception:
            cars = []
        # Count cars for each dealer_id
        from collections import Counter
        car_counts = Counter(car.get("dealer_id", "") for car in cars)
        for dealer in dealers:
            dealer_id = dealer.get("dealer_id", "")
            dealer["stock_count"] = car_counts.get(dealer_id, 0)
        with open(dealers_file, "w", encoding="utf-8") as f:
            json.dump(dealers, f, ensure_ascii=False, indent=2)
        # Refresh the dealer table
        global dealers_list
        dealers_list = dealers
        populate_dealer_table()
        messagebox.showinfo("Success", "Dealer stock counts updated.")

    update_stock_btn = tk.Button(button_frame, text="Update Dealer Stock Count", command=update_dealer_stock_count)
    update_stock_btn.pack(side=tk.LEFT, padx=2)

    # --- Delete Dealer and Their Cars ---
    def delete_dealer():
        dealer = selected_dealer["dealer"]
        if not dealer:
            messagebox.showerror("Error", "Please select a dealer from the table.")
            return
        dealer_id = dealer.get("dealer_id", "")
        if not dealer_id:
            messagebox.showerror("Error", "Selected dealer does not have a dealer_id.")
            return
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete dealer '{dealer.get('dealer_name','')}' and all their cars?")
        if not confirm:
            return
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dealers_file = os.path.join(base_dir, "data", "dealers.json")
        cars_file = os.path.join(base_dir, "data", "cars.json")
        # Remove dealer from dealers.json
        try:
            with open(dealers_file, "r", encoding="utf-8") as f:
                dealers = json.load(f)
        except Exception:
            dealers = []
        new_dealers = [d for d in dealers if str(d.get("dealer_id")) != str(dealer_id)]
        with open(dealers_file, "w", encoding="utf-8") as f:
            json.dump(new_dealers, f, ensure_ascii=False, indent=2)
        # Remove cars from cars.json
        try:
            with open(cars_file, "r", encoding="utf-8") as f:
                cars = json.load(f)
        except Exception:
            cars = []
        removed_cars = [car for car in cars if car.get("dealer_id") == dealer_id]
        new_cars = [car for car in cars if car.get("dealer_id") != dealer_id]
        with open(cars_file, "w", encoding="utf-8") as f:
            json.dump(new_cars, f, ensure_ascii=False, indent=2)
        # Refresh tables
        global dealers_list, cars_list
        dealers_list = new_dealers
        cars_list = new_cars
        populate_dealer_table()
        populate_car_table()
        messagebox.showinfo("Deleted", f"Deleted dealer '{dealer.get('dealer_name','')}' and {len(removed_cars)} cars.")

    delete_dealer_btn = tk.Button(button_frame, text="DeleteDealer", command=delete_dealer)
    delete_dealer_btn.pack(side=tk.LEFT, padx=2)

    # --- Delete All Cars for Selected Dealer ---
    def delete_cars():
        dealer = selected_dealer["dealer"]
        if not dealer:
            messagebox.showerror("Error", "Please select a dealer from the table.")
            return
        dealer_id = dealer.get("dealer_id", "")
        if not dealer_id:
            messagebox.showerror("Error", "Selected dealer does not have a dealer_id.")
            return
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete ALL cars for dealer '{dealer.get('dealer_name','')}'?")
        if not confirm:
            return
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cars_file = os.path.join(base_dir, "data", "cars.json")
        dealers_file = os.path.join(base_dir, "data", "dealers.json")
        # Remove cars from cars.json
        try:
            with open(cars_file, "r", encoding="utf-8") as f:
                cars = json.load(f)
        except Exception:
            cars = []
        removed_cars = [car for car in cars if str(car.get("dealer_id")) == str(dealer_id)]
        new_cars = [car for car in cars if str(car.get("dealer_id")) != str(dealer_id)]
        with open(cars_file, "w", encoding="utf-8") as f:
            json.dump(new_cars, f, ensure_ascii=False, indent=2)
        # Update dealer's stock_count in dealers.json
        try:
            with open(dealers_file, "r", encoding="utf-8") as f:
                dealers = json.load(f)
        except Exception:
            dealers = []
        for d in dealers:
            if str(d.get("dealer_id")) == str(dealer_id):
                d["stock_count"] = 0
        with open(dealers_file, "w", encoding="utf-8") as f:
            json.dump(dealers, f, ensure_ascii=False, indent=2)
        # Refresh tables
        global cars_list, dealers_list
        cars_list = new_cars
        dealers_list = dealers
        populate_car_table()
        populate_dealer_table()
        # Double-check: ensure no cars remain for this dealer
        cars_left = [car for car in new_cars if str(car.get("dealer_id")) == str(dealer_id)]
        if cars_left:
            messagebox.showwarning("Warning", f"Some cars for dealer '{dealer.get('dealer_name','')}' still remain in cars.json! Please check the data.")
        else:
            messagebox.showinfo("Deleted", f"Deleted {len(removed_cars)} cars for dealer '{dealer.get('dealer_name','')}'. Stock count set to 0.")

    delete_cars_btn = tk.Button(button_frame, text="DeleteCars", command=delete_cars)
    delete_cars_btn.pack(side=tk.LEFT, padx=2)

    # --- Refresh GUI Data ---
    def refresh_programme():
        global dealers_list, cars_list
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dealers_file = os.path.join(base_dir, "data", "dealers.json")
        cars_file = os.path.join(base_dir, "data", "cars.json")
        try:
            with open(dealers_file, "r", encoding="utf-8") as f:
                dealers_list = json.load(f)
        except Exception:
            dealers_list = []
        try:
            with open(cars_file, "r", encoding="utf-8") as f:
                cars_list = json.load(f)
        except Exception:
            cars_list = []
        populate_dealer_table()
        populate_car_table()
        #messagebox.showinfo("Refreshed", "Programme data refreshed.")

    refresh_btn = tk.Button(button_frame, text="Refresh", command=refresh_programme)
    refresh_btn.pack(side=tk.LEFT, padx=2)

    # --- Bottom Frame for Terminal ---
    bottom_frame = tk.Frame(root)
    bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

    output_text = tk.Text(bottom_frame, height=15, width=100, wrap=tk.WORD)
    output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Add a vertical scrollbar to the output_text widget, right next to it
    scrollbar = tk.Scrollbar(bottom_frame, command=output_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    output_text.config(yscrollcommand=scrollbar.set)

    # --- Debugging: Show all functions and their bytecode size ---
    def show_functions_info():
        import inspect
        functions = [
            # scrape_cars_for_selected_dealer,  # Removed obsolete reference
            checkAdsBS, save_dealer_to_json, scrape_dealer, extract_cars, clean_price, scrape_all, fetch_free_proxies, normalize_image_url, get_next_proxy
            # ...existing code...
        ]
        functions.sort(key=lambda f: f.__name__)
        for func in functions:
            func_name = func.__name__
            bytecode_size = len(inspect.getsource(func).encode('utf-8'))
            output_text.insert(tk.END, f"{func_name}: {bytecode_size} bytes\n")
    # Uncomment the following line to show functions info on startup
    # show_functions_info()

    # --- Enable double-click to copy cell value in Treeview tables ---
    def on_treeview_double_click(event, tree, columns):
        region = tree.identify('region', event.x, event.y)
        if region == 'cell':
            row_id = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)
            if row_id and col_id:
                col_index = int(col_id.replace('#', '')) - 1
                item = tree.item(row_id)
                values = item.get('values', [])
                if 0 <= col_index < len(values):
                    cell_value = str(values[col_index])
                    root.clipboard_clear()
                    root.clipboard_append(cell_value)
                    output_text.insert(tk.END, f"Copied: {cell_value}")

    dealer_tree.bind('<Double-1>', lambda e: on_treeview_double_click(e, dealer_tree, dealer_columns))
    car_tree.bind('<Double-1>', lambda e: on_treeview_double_click(e, car_tree, car_columns))

    # --- OpenDriver with Manual Proxy ---
    def open_driver_with_manual_proxy():
        proxy = proxy_entry.get().strip() if 'proxy_entry' in globals() else ''
        if not proxy:
            messagebox.showerror("Error", "Please enter a valid proxy (ip:port) in the Manual Proxy box before opening the driver.")
            return
        output_text.insert(tk.END, f"[OpenDriver] Opening undetected Chrome with proxy: {proxy}\n")
        def _log(msg):
            root.after(0, lambda m=msg: (output_text.insert(tk.END, m + "\n"), output_text.see(tk.END)))

        def _run():
            try:
                _log("[OpenDriver] Starting Chrome...")
                driver = get_undetected_chrome_driver(proxy=proxy, log_output=_log)
                _log("[OpenDriver] Chrome launched, loading Google...")
                driver.get("https://www.google.com/")
                _log("[OpenDriver] Chrome opened. You can now browse and test proxy speed.")
                # Keep thread alive until Chrome is closed
                while True:
                    try:
                        _ = driver.window_handles
                        time.sleep(1)
                    except Exception:
                        break
                _log("[OpenDriver] Chrome window closed.")
            except Exception as e:
                import traceback
                _log(f"[OpenDriver] Error: {e}\n{traceback.format_exc()}")
        threading.Thread(target=_run, daemon=True).start()

    open_driver_button = tk.Button(button_frame, text="OpenDriver", command=open_driver_with_manual_proxy)
    open_driver_button.pack(side=tk.LEFT, padx=2)

    # --- Start the GUI ---
    root.mainloop()