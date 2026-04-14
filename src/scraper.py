import re
import json
import os
from bs4 import BeautifulSoup
from scraperUtils import human_like_browsing, ad_is_deleted

class Scraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.dealers = []
        self.cars = []

    def fetch_page(self, url):
        import requests
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    def parse_dealer_info(self, dealer_html, dealer_url):
        soup = BeautifulSoup(dealer_html, 'html.parser')
        # 1. Dealer Name
        name_tag = soup.find('h1', class_='dealer-title')
        dealer_name = name_tag.text.strip() if name_tag else None

        # 2. Stock Count (from "View 120 cars" button)
        stock_btn = soup.find('button', string=re.compile(r'View \d+ cars'))
        stock_count = None
        if stock_btn:
            match = re.search(r'View (\d+) cars', stock_btn.text)
            if match:
                stock_count = int(match.group(1))

        # 3. Address (from Address <ul>)
        address_ul = soup.find('h3', string='Address')
        address = []
        if address_ul:
            ul = address_ul.find_next('ul')
            if ul:
                address = [li.text.strip() for li in ul.find_all('li') if li.text.strip()]
        # Join address lines
        address_str = ', '.join(address)

        # 4. Phone number (from tel: link)
        phone = None
        phone_link = soup.find('a', href=re.compile(r'^tel:'))
        if phone_link:
            phone = phone_link.text.strip()

        # 5. Try to get more structured data from JSON-LD if present
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    dealer_name = data.get('name', dealer_name)
                    phone = data.get('telephone', phone)
                    addr = data.get('address', {})
                    address_str = ', '.join([
                        addr.get('streetAddress', ''),
                        addr.get('addressLocality', ''),
                        addr.get('addressRegion', ''),
                        addr.get('postalCode', '')
                    ]).replace(' ,', '').strip(', ')
            except Exception:
                pass

        # 6. Dealer ID (use a hash of the URL or another unique method)
        dealer_id = abs(hash(dealer_url)) % (10 ** 8)

        return {
            'dealer_id': dealer_id,
            'dealer_name': dealer_name,
            'stock_count': stock_count,
            'address': address_str,
            'phone': phone,
            'url': dealer_url
        }

    def parse_car_info(self, car_html, dealer_id):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(car_html, 'html.parser')
        car_title = soup.find('h2', class_='car-title').text.strip()
        car_price = soup.find('span', class_='car-price').text.strip()
        image_urls = [img['src'] for img in soup.find_all('img', class_='car-image')]

        # --- Split title into make and model ---
        parts = car_title.split(" ", 1)
        make = parts[0]
        model = parts[1] if len(parts) > 1 else ""

        return {
            'make': make,
            'model': model,
            'price': car_price,
            'dealer_id': dealer_id,
            'images': image_urls
        }

    def scrape_dealers(self):
        dealer_list_url = f"{self.base_url}/dealers"
        print(f"Fetching dealer list from: {dealer_list_url}")
        html = self.fetch_page(dealer_list_url)
        with open("debug_dealer_list.html", "w", encoding="utf-8") as f:
            f.write(html)
        soup = BeautifulSoup(html, 'html.parser')
        dealer_links = soup.find_all('a', class_='dealer-link')
        print(f"Found {len(dealer_links)} dealers.")
        for link in dealer_links:
            url = link['href']
            if not url.startswith('http'):
                url = self.base_url + url
            print(f"Adding dealer: {url}")
            self.dealers.append({'url': url})

    def scrape_cars(self):
        # Logic to scrape car listings and store in self.cars
        pass

    def save_data(self):
        import json
        with open('data/dealers.json', 'w') as dealers_file:
            json.dump(self.dealers, dealers_file)
        with open('data/cars.json', 'w') as cars_file:
            json.dump(self.cars, cars_file)

    def run(self):
        # Example run method to scrape dealers and cars
        self.scrape_dealers()
        for dealer in self.dealers:
            dealer_url = dealer['url']
            html = self.fetch_page(dealer_url)
            dealer_info = self.parse_dealer_info(html, dealer_url)
            dealer['info'] = dealer_info  # Add parsed info to dealer dict

            # Now scrape cars for this dealer
            self.scrape_cars_for_dealer(dealer)

        # Save all data to files
        self.save_data()

    def scrape_cars_for_dealer(self, dealer):
        # Logic to scrape cars for a specific dealer
        dealer_id = dealer['dealer_id']
        cars_url = f"{self.base_url}/dealer/{dealer_id}/cars"
        cars_page = self.fetch_page(cars_url)
        car_listings = self.parse_car_listings(cars_page, dealer_id)
        self.cars.extend(car_listings)

    def parse_car_listings(self, html, dealer_id):
        soup = BeautifulSoup(html, 'html.parser')
        car_items = soup.find_all('div', class_='car-item')
        cars = []
        for item in car_items:
            link = item.find('a', class_='car-link')['href']
            car_html = self.fetch_page(link)
            car_info = self.parse_car_info(car_html, dealer_id)
            cars.append(car_info)
        return cars

    def ScrapeVehicleInfo(self, cars_file=None, proxy=None):
        import json
        import time
        from selenium_utils import accept_cookies
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from bs4 import BeautifulSoup
        import re
        import os
        from scraperUtils import human_like_browsing, ad_is_deleted
        from gui import get_undetected_chrome_driver
        if cars_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cars_file = os.path.join(base_dir, "data", "cars.json")
        with open(cars_file, "r", encoding="utf-8") as f:
            cars = json.load(f)
        driver = get_undetected_chrome_driver(proxy=proxy)
        driver.maximize_window()  # Always full screen
        cookies_accepted = False
        idx = len(cars) - 1
        while idx >= 0:
            car = cars[idx]
            if not car.get("informationScraped", False):
                print(f"Scraping vehicle info for {car.get('make', '')} {car.get('model', '')} ({car.get('car_id', '')})")
                driver.get(car["listing_url"])
                human_like_browsing(driver)
                time.sleep(1)
                page_source = driver.page_source
                if ad_is_deleted(page_source):
                    print(f"DELETED: {car.get('make','')} {car.get('model','')} ({car.get('car_id','')}) at {car.get('listing_url','')}")
                    del cars[idx]
                    with open(cars_file, "w", encoding="utf-8") as f:
                        json.dump(cars, f, ensure_ascii=False, indent=2)
                    idx -= 1
                    continue
                if not cookies_accepted:
                    try:
                        accept_cookies(driver)
                        cookies_accepted = True
                        print("Accepted cookies dialog.")
                    except Exception as e:
                        print(f"Could not accept cookies: {e}")
                soup = BeautifulSoup(driver.page_source, "html.parser")
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
                                print(f"[DEBUG] {label}: {value}")
                car["informationScraped"] = True
                with open(cars_file, "w", encoding="utf-8") as f:
                    json.dump(cars, f, ensure_ascii=False, indent=2)
            idx -= 1
        driver.quit()
        with open(cars_file, "w", encoding="utf-8") as f:
            json.dump(cars, f, ensure_ascii=False, indent=2)

# Example usage:
# scraper = Scraper(base_url="https://example.com")
# scraper.run()