import pytest
from unittest.mock import patch, AsyncMock
from scraper import scrape_make, ScraperConfig


MAKE = "porsche"
CONFIG = ScraperConfig()

VALID_FIRST_PAGE = {
  "totalCount": 1,
  "items": [{"make": "Porsche", "model": "911"}],
}

REDIRECTED_FIRST_PAGE = {
  "totalCount": 100,
  "items": [{"make": "Toyota", "model": "Camry"}],
}


HTML_COUNT = 100


class TestScrapeMake:
  async def test_raises_when_api_returns_nothing(self):
    with patch("scraper.check_make_exists", AsyncMock(return_value=HTML_COUNT)):
      with patch("scraper.fetch_page", return_value=None):
        with pytest.raises(RuntimeError, match=MAKE):
          await scrape_make(CONFIG, MAKE)

  async def test_returns_zero_when_api_redirects_to_wrong_make(self):
    with patch("scraper.check_make_exists", AsyncMock(return_value=HTML_COUNT)):
      with patch("scraper.fetch_page", return_value=REDIRECTED_FIRST_PAGE):
        result = await scrape_make(CONFIG, MAKE)

    assert result["scraped_count"] == 0
    assert result["total_count"] == 100

  async def test_returns_results_on_success(self):
    with patch("scraper.check_make_exists", AsyncMock(return_value=HTML_COUNT)):
      with patch("scraper.fetch_page", return_value=VALID_FIRST_PAGE):
        result = await scrape_make(CONFIG, MAKE)

    assert result["scraped_count"] == 1
    assert result["html_count"] == HTML_COUNT
