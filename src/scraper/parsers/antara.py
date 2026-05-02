"""
parsers/antara.py
=================
Parser for Antara News Agency.
Target: https://<BASE_URL>/<category>[/<page>]

Antara uses relative date labels ("5 menit lalu", "kemarin") instead of
explicit date strings, so category-looping and date-classification logic
lives here — completely hidden from main_scraper.py.
"""

import time
import requests
from bs4 import BeautifulSoup

from src.scraper.base_parser import BaseParser

class AntaraParser(BaseParser):

    CATEGORIES = ["politik", "ekonomi", "hukum"]
    MAX_PAGES = 10
    REQUEST_DELAY = 1  # seconds between page requests

    def __init__(self):
        self._base_url = "https://antaranews.com"
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

    #  BaseParser contract

    @property
    def source_name(self) -> str:
        return "antara"

    def fetch_news(self, target_date: str) -> list[dict]:
        """
        Scrapes all configured categories and returns deduplicated articles
        from yesterday. `target_date` is accepted for API consistency but
        Antara's pagination uses relative time labels, not explicit dates.
        """
        all_articles = []

        for category in self.CATEGORIES:
            print(f"  [Antara] Processing category: {category}")
            try:
                articles = self._scrape_category(category)
                for article in articles:
                    article["category"] = category
                all_articles.extend(articles)
                print(f"  [Antara] Fetched {len(articles)} articles from '{category}'")
            except Exception as exc:
                print(f"  [Antara] Error scraping '{category}': {exc}")

        return self._stamp(all_articles)

    #  Internal helpers

    def _scrape_category(self, category: str, target_age: str = "yesterday") -> list[dict]:
        """Paginates through a category until articles become too old."""
        results = []

        for page in range(1, self.MAX_PAGES + 1):
            url = (
                f"{self._base_url}/{category}/{page}"
                if page > 1
                else f"{self._base_url}/{category}"
            )

            response = requests.get(url, headers=self._headers, timeout=10)
            response.raise_for_status()

            articles = self._parse_list_page(response.text)
            if not articles:
                break

            stop = False
            for article in articles:
                age = self._classify_date(article["date_text"])
                if age == target_age:
                    results.append(article)
                elif age == "older":
                    stop = True
                    break

            if stop:
                break

            time.sleep(self.REQUEST_DELAY)

        return results

    @staticmethod
    def _parse_list_page(html: str) -> list[dict]:
        """Extracts article metadata from an Antara list page."""
        soup = BeautifulSoup(html, "html.parser")
        articles = []

        for row in soup.select("div.row"):
            title_tag = row.select_one("h2.post_title a")
            date_tag = row.select_one("span.text-secondary")

            if not title_tag:
                continue

            articles.append({
                "title":     title_tag.get_text(strip=True),
                "link":      title_tag.get("href", ""),
                "date_text": date_tag.get_text(strip=True) if date_tag else "",
            })

        return articles

    @staticmethod
    def _classify_date(date_text: str) -> str:
        """Maps Antara's relative date labels to 'today', 'yesterday', or 'older'."""
        text = date_text.lower()
        if any(token in text for token in ["menit", "jam", "detik"]):
            return "today"
        if "kemarin" in text:
            return "yesterday"
        return "older"
