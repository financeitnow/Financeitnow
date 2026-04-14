from bs4 import BeautifulSoup
import re

with open(r'c:\Users\zq09a\Documents\FIN - DealerVehicleScraper\car-dealership-scraper\src\detail_page_rendered.html', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')

print('=== OVERVIEW SECTION ===')
overview = soup.find('section', {'data-testid': 'overview'})
if overview:
    # Find the repeating card divs
    for card in overview.find_all('div', recursive=False)[:2]:
        print('  card div:', card.get('class'))
        for child in card.children:
            if hasattr(child, 'get_text'):
                t = child.get_text(strip=True)
                if t:
                    print('    child:', child.name, child.get('class'), child.get('data-testid'), repr(t[:60]))
    # Full dump of first 2 cards
    cards = overview.find_all('div', class_=re.compile(r'sc-tqnfbs-4'))
    print(f'\n  Cards with sc-tqnfbs-4: {len(cards)}')
    if cards:
        card = cards[0]
        print('  First card HTML:')
        print(card.prettify()[:800])

print()
print('=== KEY-INFORMATION SECTION ===')
keyinfo = soup.find('section', {'data-testid': 'key-information'})
if keyinfo:
    print(keyinfo.prettify()[:1500])
