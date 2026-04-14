import pytest
from .scraper import Scraper

# test_scraper.py

@pytest.fixture
def scraper():
    return Scraper(base_url="http://example.com")

def test_parse_dealer_info_basic(scraper):
    html = """
    <html>
      <body>
        <h1 class="dealer-title">Test Dealer</h1>
        <button>View 42 cars</button>
        <h3>Address</h3>
        <ul>
          <li>123 Main St</li>
          <li>Townsville</li>
        </ul>
        <a href="tel:123456789">123456789</a>
      </body>
    </html>
    """
    url = "http://example.com/dealer/1"
    info = scraper.parse_dealer_info(html, url)
    assert info['dealer_name'] == "Test Dealer"
    assert info['stock_count'] == 42
    assert info['address'] == "123 Main St, Townsville"
    assert info['phone'] == "123456789"
    assert info['url'] == url
    assert isinstance(info['dealer_id'], int)

def test_parse_dealer_info_jsonld(scraper):
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "name": "Structured Dealer",
          "telephone": "555-0000",
          "address": {
            "streetAddress": "456 Elm St",
            "addressLocality": "Metro City",
            "addressRegion": "MC",
            "postalCode": "99999"
          }
        }
        </script>
      </head>
      <body>
        <h1 class="dealer-title">Fallback Dealer</h1>
      </body>
    </html>
    """
    url = "http://example.com/dealer/2"
    info = scraper.parse_dealer_info(html, url)
    assert info['dealer_name'] == "Structured Dealer"
    assert info['phone'] == "555-0000"
    assert "456 Elm St" in info['address']
    assert "Metro City" in info['address']
    assert "MC" in info['address']
    assert "99999" in info['address']

def test_parse_dealer_info_missing_fields(scraper):
    html = """
    <html>
      <body>
        <h1 class="dealer-title"></h1>
      </body>
    </html>
    """
    url = "http://example.com/dealer/3"
    info = scraper.parse_dealer_info(html, url)
    assert info['dealer_name'] == ""
    assert info['stock_count'] is None
    assert info['address'] == ""
    assert info['phone'] is None

# We recommend installing an extension to run python tests.