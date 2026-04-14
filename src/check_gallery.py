import sys, time, re
sys.path.insert(0, r'c:\Users\zq09a\Documents\FIN - DealerVehicleScraper\car-dealership-scraper\src')
from scraperUtils import create_undetected_chrome_driver
from selenium_utils import accept_cookies
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

driver = create_undetected_chrome_driver()
driver.get('https://www.autotrader.co.uk/car-details/202603271056528')
time.sleep(6)
try:
    accept_cookies(driver)
    time.sleep(3)
except Exception as e:
    print('Cookies:', e)

print('\n=== BEFORE clicking gallery ===')
soup = BeautifulSoup(driver.page_source, 'html.parser')

# Find the gallery button
gallery_section = soup.find('section', {'data-testid': 'gallery'})
print('gallery section found:', gallery_section is not None)

# Find all buttons in gallery section
if gallery_section:
    for btn in gallery_section.find_all('button')[:5]:
        print('  btn class:', btn.get('class'), '| text:', btn.get_text(strip=True)[:40])

# Also search broadly
for btn in soup.find_all('button'):
    t = btn.get_text(strip=True)
    if 'gallery' in t.lower() or 'Gallery' in t:
        print('  Found gallery btn:', btn.get('class'), btn.get('data-testid'), repr(t))

print('\n=== Trying to click gallery button ===')
clicked = False

# Try by span text "Gallery"
try:
    btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Gallery']]"))
    )
    btn.click()
    print('Clicked by span text "Gallery"')
    clicked = True
    time.sleep(3)
except Exception as e:
    print('span text failed:', str(e)[:100])

if not clicked:
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.sc-1imjpi3-1"))
        )
        btn.click()
        print('Clicked by class sc-1imjpi3-1')
        clicked = True
        time.sleep(3)
    except Exception as e:
        print('class selector failed:', str(e)[:100])

print('\n=== AFTER clicking gallery ===')
soup2 = BeautifulSoup(driver.page_source, 'html.parser')

# Check for image elements
print('button.image-gallery-item imgs:', len(soup2.select('button.image-gallery-item img')))
print('All img tags total:', len(soup2.find_all('img')))

# Find images in gallery/modal context
for img in soup2.find_all('img')[:20]:
    src = img.get('src', '')
    if 'atcdn' in src or 'autotrader' in src:
        print('  img src:', src[:100], '| class:', img.get('class'))

# Check data-testid on images
for img in soup2.find_all('img', attrs={'data-testid': True}):
    print('  testid img:', img.get('data-testid'), img.get('src', '')[:80])

# Save the post-click HTML
with open(r'c:\Users\zq09a\Documents\FIN - DealerVehicleScraper\car-dealership-scraper\src\detail_gallery.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
print('\nSaved post-click HTML')

driver.quit()
