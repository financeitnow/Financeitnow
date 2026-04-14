from bs4 import BeautifulSoup
import re

with open(r'c:\Users\zq09a\Documents\FIN - DealerVehicleScraper\car-dealership-scraper\src\detail_page.html', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')

print('=== GEARBOX/FUEL UL (at__sc-1ebejir-0) ===')
ul = soup.find('ul', class_=re.compile(r'at__sc-1ebejir-0'))
print('Found:', ul is not None)
if ul:
    print([li.get_text(strip=True) for li in ul.find_all('li')])

print()
print('=== OVERVIEW SECTION (at__sc-efqqw2-0) ===')
sec = soup.find('section', class_=re.compile(r'at__sc-efqqw2-0'))
print('Found:', sec is not None)

print()
print('=== ALL data-testid on page (relevant ones) ===')
testids = set(el.get('data-testid') for el in soup.find_all(attrs={'data-testid': True}))
for t in sorted(testids):
    if any(k in t.lower() for k in ['engine','fuel','gear','body','door','seat','emission','owner','spec','key','detail','overview','info']):
        print(' ', t)

print()
print('=== ALL section tags ===')
for s in soup.find_all('section'):
    print(' ', s.get('class'), s.get('data-testid'))

print()
print('=== Look for Engine/Doors/Seats/Gearbox label text ===')
for el in soup.find_all(string=re.compile(r'^(Engine|Gearbox|Fuel type|Body type|Doors|Seats|Owners|Emission class)$', re.I)):
    parent = el.parent
    grandparent = parent.parent if parent else None
    print('  label:', repr(str(el).strip()))
    print('    parent:', parent.name, parent.get('class'), parent.get('data-testid'))
    if grandparent:
        print('    grandparent:', grandparent.name, grandparent.get('class'), grandparent.get('data-testid'))
        # print value sibling
        siblings = list(grandparent.children)
        for i, s in enumerate(siblings):
            if hasattr(s, 'get_text') and s.get_text(strip=True) == str(el).strip():
                # next sibling with text
                for j in range(i+1, len(siblings)):
                    t = siblings[j]
                    if hasattr(t, 'get_text') and t.get_text(strip=True):
                        print('    value sibling:', t.name, t.get('class'), repr(t.get_text(strip=True)[:50]))
                        break
    print()
