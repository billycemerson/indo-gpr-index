
"""
parsers/kompas.py
=================
Parser for Kompas Indeks.
Target URL: https://indeks.kompas.com/?site=nasional&date=YYYY-MM-DD&page=N

Kompas uses explicit date-based URLs and paginates until a page returns
no articles. All of this is encapsulated here — main_scraper.py only
calls fetch_news(target_date).
"""

import time
import requests
from bs4 import BeautifulSoup

from src.scraper.base_parser import BaseParser


class KompasParser(BaseParser):

    BASE_URL = "https://indeks.kompas.com/"
    CATEGORY = "nasional"
    REQUEST_DELAY = 1  # seconds between page requests

    def __init__(self):
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
        return "kompas"

    def fetch_news(self, target_date: str) -> list[dict]:
        """
        Scrapes all paginated results for `target_date` from Kompas Indeks.

        Args:
            target_date (str): Date in YYYY-MM-DD format.

        Returns:
            list[dict]: Stamped article list.
        """
        results = []
        page = 1

        while True:
            print(f"  [Kompas] Scraping page {page} for {target_date}...")
            url = f"{self.BASE_URL}?site={self.CATEGORY}&date={target_date}&page={page}"

            try:
                response = requests.get(url, headers=self._headers, timeout=10)
                response.raise_for_status()
            except requests.exceptions.RequestException as exc:
                print(f"  [Kompas] Error fetching page {page}: {exc}")
                break

            articles = self._parse_index_page(response.text)

            if not articles:
                print(f"  [Kompas] Pagination complete at page {page} (no articles found).")
                break

            results.extend(articles)
            time.sleep(self.REQUEST_DELAY)
            page += 1

        return self._stamp(results)

    #  Internal helpers

    def _parse_index_page(self, html: str) -> list[dict]:
        """Parses a single Kompas Indeks page and returns article dicts."""
        soup = BeautifulSoup(html, "html.parser")
        articles = []

        for wrap in soup.find_all("div", class_="articleItem-wrap"):
            title_tag = wrap.find("h2", class_="articleTitle")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)

            date_tag = wrap.find("div", class_="articlePost-date")
            date_text = date_tag.get_text(strip=True) if date_tag else "Date not available"

            # Kompas wraps articleItem-wrap inside an <a> tag
            parent_a = wrap.find_parent("a")
            if parent_a and parent_a.get("href"):
                link = parent_a["href"]
            else:
                child_a = wrap.find("a", href=True)
                link = child_a.get("href") if child_a else None

            if not link:
                print(f"  [Kompas] Warning: no link found for '{title[:40]}...'")
                continue

            articles.append({
                "title":     title,
                "link":      link,
                "category":  self.CATEGORY,
                "date_text": date_text,
            })

        return articles