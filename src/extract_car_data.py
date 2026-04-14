from bs4 import BeautifulSoup
import json
import re

def extract_car_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    cars = []
    # Use data-testid="advertCard-N" — Autotrader now indexes cards (advertCard-0, advertCard-1, ...)
    for card in soup.find_all('div', {'data-testid': re.compile(r'^advertCard(-\d+)?$')}):
        car = {}
        # Title, subtitle, URL and car_id
        title_tag = card.find('a', {'data-testid': 'search-listing-title'})
        if title_tag:
            car['title'] = title_tag.contents[0].strip()
            subtitle = title_tag.find('span')
            if subtitle:
                car['subtitle'] = subtitle.text.strip()
            car_url = title_tag.get('href', '')
            if car_url:
                match = re.search(r'/car-details/(\d+)', car_url)
                if match:
                    car['car_id'] = match.group(1)
                car['listing_url'] = 'https://www.autotrader.co.uk' + car_url.split('?')[0]
        # Price — extract from the title link text (e.g. "Vauxhall Corsa..., £1,650")
        title_full_text = title_tag.get_text(strip=True) if title_tag else ''
        price_match = re.search(r'£[\d,]+', title_full_text)
        if price_match:
            car['price'] = price_match.group(0)
        # Mileage — use stable data-testid
        mileage_tag = card.find('li', {'data-testid': 'mileage'})
        if mileage_tag:
            car['mileage'] = mileage_tag.text.strip()
        # Year/reg — use stable data-testid
        year_tag = card.find('li', {'data-testid': 'registered_year'})
        if year_tag:
            car['year_reg'] = year_tag.text.strip()
        # Write-off category — use stable data-testid
        writeoff_tag = card.find('li', {'data-testid': 'write_off_category'})
        if writeoff_tag:
            car['write_off_category'] = writeoff_tag.text.strip()
        # Attention grabber
        attn = card.find('p', {'data-testid': 'search-listing-attention-grabber'})
        if attn:
            car['attention_grabber'] = attn.text.strip()
        # Images
        images = []
        for img in card.find_all('img', class_='main-image'):
            images.append(img['src'])
        car['images'] = images
        car['informationScraped'] = False
        if car.get('car_id'):  # Only add cars with a valid ID
            cars.append(car)
    return cars

# After extracting car data:
# car_list = extract_car_data(html)  # html is your HTML string

# with open('cars.json', 'w', encoding='utf-8') as f:
#     json.dump(car_list, f, ensure_ascii=False, indent=2)