"""
parsers/detik.py
=================
Parser for Detik News Agency.
Detik URL pattern: 
  Page 1: https://news.detik.com/<category>/indeks?date=<date>
  Page 2+: https://news.detik.com/<category>/indeks?page=2&date=<date>
  
Date format in URL: MM%2FDD%2FYYYY (e.g., 05%2F15%2F2026)
The server respects this date parameter and returns articles from that specific date.
No need to parse HTML dates - trust the URL parameter.
"""

import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from src.scraper.base_parser import BaseParser


class DetikParser(BaseParser):

    BASE_URL = "https://news.detik.com"
    CATEGORIES = ["internasional", "hukum", "berita"]
    MAX_PAGES = 20
    REQUEST_DELAY = 1

    def __init__(self):
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
            "Referer": "https://news.detik.com/",
        }

    # BaseParser contract

    @property
    def source_name(self) -> str:
        return "detik"

    def fetch_news(self, target_date: str) -> list[dict]:
        """
        Scrapes all configured categories for articles matching target_date.
        Uses the URL date parameter - server returns articles for that date.
        
        Args:
            target_date (str): Date in YYYY-MM-DD format.
            
        Returns:
            list[dict]: Stamped article list.
        """
        all_articles = []

        for category in self.CATEGORIES:
            print(f"  [Detik] Processing category: {category}")
            
            category_results = self._scrape_category(category, target_date)
            all_articles.extend(category_results)
            
            print(f"  [Detik] Collected {len(category_results)} articles for category '{category}'")

        print(f"  [Detik] Total collected across all categories: {len(all_articles)}")
        return self._stamp(all_articles)

    # Internal helpers

    def _scrape_category(self, category: str, target_date: str) -> list[dict]:
        """
        Paginates through a category for a specific date.
        Since Detik respects the date parameter, we collect all articles
        from pages until we hit an empty page.
        """
        results = []
        
        # Convert target_date to URL format (MM/DD/YYYY)
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        url_date = f"{date_obj.month:02d}%2F{date_obj.day:02d}%2F{date_obj.year}"
        
        for page in range(1, self.MAX_PAGES + 1):
            url = self._build_url(category, page, url_date)
            print(f"    [Detik] Fetching page {page}: {url}")

            try:
                response = requests.get(url, headers=self._headers, timeout=10)
                response.raise_for_status()
            except requests.exceptions.RequestException as exc:
                print(f"    [Detik] Error fetching page {page}: {exc}")
                break

            articles, has_more = self._parse_index_page(response.text, category, target_date)
            
            if not articles:
                # No more articles for this date
                break
                
            results.extend(articles)
            
            if not has_more:
                # This was the last page
                break

            time.sleep(self.REQUEST_DELAY)

        return results

    def _build_url(self, category: str, page: int, url_date: str) -> str:
        """
        Builds URL for specific category, page, and date.
        
        Page 1: https://news.detik.com/<category>/indeks?date=<date>
        Page 2+: https://news.detik.com/<category>/indeks?page=<page>&date=<date>
        """
        base = f"{self.BASE_URL}/{category}/indeks"
        
        if page == 1:
            return f"{base}?date={url_date}"
        else:
            return f"{base}?page={page}&date={url_date}"

    def _parse_index_page(self, html: str, category: str, target_date: str) -> tuple[list[dict], bool]:
        """
        Parses one Detik index page.
        
        Since Detik respects the date parameter, we trust that all articles
        on this page are from the target_date. We just extract metadata.
        
        Returns:
            (articles, has_more)
            articles : list of article dicts from this page
            has_more : True if there might be more pages (based on pagination indicator)
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        has_more = False

        # Find all article items
        article_items = soup.select("article.list-content__item")
        
        if not article_items:
            # Try alternative selector for different Detik layouts
            article_items = soup.select(".list-content__item")
        
        for article in article_items:
            # Extract title and link
            title_tag = article.select_one("h3.media__title a")
            if not title_tag:
                # Fallback to alternative selector
                title_tag = article.select_one(".media__title a")
            
            if not title_tag:
                continue
            
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            
            if not link:
                continue
            
            articles.append({
                "title": title,
                "link": link,
                "category": category,
                "date_text": target_date,  # Use target_date since server filters by it
            })
        
        # Check if there's a "next page" indicator
        next_button = soup.select_one("a.next, a.pagination__next, li.pagination__next a")
        if next_button and not next_button.get("disabled"):
            has_more = True
        
        # Also check if there are any articles - if page has articles but no next button,
        # assume this is the last page (has_more = False)
        
        return articles, has_more