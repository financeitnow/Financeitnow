import sys, time
sys.path.insert(0, r'c:\Users\zq09a\Documents\FIN - DealerVehicleScraper\car-dealership-scraper\src')
from scraperUtils import create_undetected_chrome_driver
from selenium_utils import accept_cookies
from bs4 import BeautifulSoup
import re

driver = create_undetected_chrome_driver()
driver.get('https://www.autotrader.co.uk/car-details/202603080512981')
time.sleep(6)
try:
    accept_cookies(driver)
    time.sleep(3)
except Exception as e:
    print('Cookies:', e)

html = driver.page_source
driver.quit()

with open(r'c:\Users\zq09a\Documents\FIN - DealerVehicleScraper\car-dealership-scraper\src\detail_page_rendered.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Saved {len(html)} chars')

soup = BeautifulSoup(html, 'html.parser')

print('\n=== GEARBOX/FUEL UL (at__sc-1ebejir-0) ===')
ul = soup.find('ul', class_=re.compile(r'at__sc-1ebejir-0'))
print('Found:', ul is not None)
if ul:
    print([li.get_text(strip=True) for li in ul.find_all('li')])

print('\n=== OVERVIEW SECTION (at__sc-efqqw2-0) ===')
sec = soup.find('section', class_=re.compile(r'at__sc-efqqw2-0'))
print('Found:', sec is not None)

print('\n=== data-testid attributes containing useful keywords ===')
testids = set(el.get('data-testid') for el in soup.find_all(attrs={'data-testid': True}))
for t in sorted(testids):
    if any(k in t.lower() for k in ['engine','fuel','gear','body','door','seat','emission','owner','spec','key','detail','overview','info','tech']):
        print(' ', t)

print('\n=== Label text: Engine/Gearbox/Fuel type/Body type/Doors/Seats/Owners/Emission ===')
for el in soup.find_all(string=re.compile(r'^(Engine|Gearbox|Fuel type|Body type|Doors|Seats|Owners|Emission class)$', re.I)):
    parent = el.parent
    grandparent = parent.parent if parent else None
    print('  label:', repr(str(el).strip()))
    print('    parent:', parent.name, parent.get('class'), parent.get('data-testid'))
    if grandparent:
        print('    grandparent:', grandparent.name, grandparent.get('class'), grandparent.get('data-testid'))
    print()

print('\n=== ALL section data-testids ===')
for s in soup.find_all('section'):
    if s.get('data-testid'):
        print(' ', s.get('data-testid'), s.get('class'))
