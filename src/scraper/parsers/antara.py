"""
parsers/antara.py
=================
Parser for Antara News Agency.

CRITICAL: Relative dates must be converted to ACTUAL dates (based on CURRENT date),
then compared with target_date. NOT converted to target_date directly.

How it works:
- "X menit/jam/detik lalu" → TODAY (current date)
- "Kemarin" → YESTERDAY (current date - 1 day)
- "18 Mei 2026" → absolute date (2026-05-18)

Then filter to keep only articles where converted_date == target_date
"""

import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from src.scraper.base_parser import BaseParser

class AntaraParser(BaseParser):

    CATEGORIES = ["politik", "ekonomi", "hukum", "dunia"]
    MAX_PAGES = 20
    REQUEST_DELAY = 1

    _MONTHS = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
        'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
        'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
    }

    def __init__(self):
        self._base_url = "https://antaranews.com"
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

    @property
    def source_name(self) -> str:
        return "antara"

    def fetch_news(self, target_date: str) -> list[dict]:
        """
        Fetch articles matching target_date (YYYY-MM-DD).
        Converts relative dates to ACTUAL dates using CURRENT date.
        """
        all_articles = []
        current_date = datetime.now()  # Use ACTUAL current date for conversion

        for category in self.CATEGORIES:
            print(f"  [Antara] Processing category: {category} for date {target_date}")
            try:
                articles = self._scrape_category(category, target_date, current_date)
                all_articles.extend(articles)
                print(f"  [Antara] Found {len(articles)} articles from '{category}' on {target_date}")
            except Exception as exc:
                print(f"  [Antara] Error scraping '{category}': {exc}")

        return self._stamp(all_articles)

    def _scrape_category(self, category: str, target_date: str, current_date: datetime) -> list[dict]:
        """Paginate through category and return articles matching target_date."""
        results = []
        
        for page in range(1, self.MAX_PAGES + 1):
            url = self._build_url(category, page)
            print(f"    [Antara] Fetching page {page}: {url}")
            
            try:
                response = requests.get(url, headers=self._headers, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"    [Antara] Failed to fetch page {page}: {e}")
                break
            
            # Parse page and convert dates to ACTUAL dates using current_date
            articles_on_page = self._parse_list_page(response.text, current_date)
            
            if not articles_on_page:
                print(f"    [Antara] No articles found on page {page}")
                break
            
            # Filter articles that match target_date exactly
            for article in articles_on_page:
                if article["article_date"] == target_date:
                    results.append({
                        "title": article["title"],
                        "link": article["link"],
                        "category": category,
                        "date_text": article["raw_date_text"],
                    })
            
            # Stop pagination if we've passed target_date
            # Get the oldest article date in this page
            oldest_date = min(article["date_obj"] for article in articles_on_page)
            oldest_date_str = oldest_date.strftime("%Y-%m-%d")
            
            print(f"    [Antara] Page {page}: Found {len([a for a in articles_on_page if a['article_date'] == target_date])} target articles. Oldest date: {oldest_date_str}")
            
            # If oldest article is older than target_date, we've seen all target articles
            if oldest_date_str < target_date:
                print(f"    [Antara] Reached articles older than target_date, stopping")
                break
            
            time.sleep(self.REQUEST_DELAY)
        
        return results

    def _build_url(self, category: str, page: int) -> str:
        """Build URL for specific page."""
        if page == 1:
            return f"{self._base_url}/{category}"
        return f"{self._base_url}/{category}/{page}"
    
    def _parse_list_page(self, html: str, current_date: datetime) -> list[dict]:
        """
        Parse a single page and convert ALL dates to YYYY-MM-DD format.
        
        CRITICAL: Uses current_date (NOW) for converting relative dates.
        
        Returns list of dicts with:
        - title: article title
        - link: article URL
        - raw_date_text: original date string (for debugging)
        - article_date: YYYY-MM-DD format string
        - date_obj: datetime object for comparison
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        for row in soup.select("div.row"):
            title_tag = row.select_one("h2.post_title a")
            date_tag = row.select_one("span.text-secondary")
            
            if not title_tag or not date_tag:
                continue
            
            raw_date = date_tag.get_text(strip=True)
            
            # Convert relative date to ACTUAL date using current_date
            article_date_str = self._convert_to_actual_date(raw_date, current_date)
            
            if article_date_str is None:
                print(f"    [Antara] Warning: Could not parse date: {raw_date}")
                continue
            
            # Parse to datetime for comparison
            article_date_obj = datetime.strptime(article_date_str, "%Y-%m-%d")
            
            articles.append({
                "title": title_tag.get_text(strip=True),
                "link": title_tag.get("href", ""),
                "raw_date_text": raw_date,
                "article_date": article_date_str,
                "date_obj": article_date_obj,
            })
        
        return articles

    def _convert_to_actual_date(self, date_text: str, current_date: datetime) -> str | None:
        """
        Convert Antara date formats to ACTUAL YYYY-MM-DD string.
        
        Conversion rules using CURRENT date:
        1. "X menit/jam/detik lalu" → current_date (TODAY)
        2. "Kemarin" → current_date - 1 day (YESTERDAY)
        3. "18 Mei 2026" → absolute date (2026-05-18)
        
        Args:
            date_text: Raw date string from Antara
            current_date: ACTUAL current date (datetime.now())
        
        Returns:
            YYYY-MM-DD formatted date string, or None if parsing fails
        """
        text = date_text.lower().strip()
        
        # Rule 1: "X menit/jam/hari/detik lalu" → TODAY
        if "lalu" in text and "kemarin" not in text:
            # These are articles from today
            return current_date.strftime("%Y-%m-%d")
        
        # Rule 2: "Kemarin" → YESTERDAY
        if "kemarin" in text:
            yesterday = current_date - timedelta(days=1)
            return yesterday.strftime("%Y-%m-%d")
        
        # Rule 3: Absolute Indonesian date (e.g., "18 Mei 2026" or "18 Mei 2026 15:30")
        abs_match = re.match(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})', text)
        if abs_match:
            day = int(abs_match.group(1))
            month_name = abs_match.group(2)
            year = int(abs_match.group(3))
            
            if month_name in self._MONTHS:
                month = self._MONTHS[month_name]
                
                # Validate date is real
                try:
                    date_obj = datetime(year, month, day)
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    return None
        
        # Rule 4: Direct YYYY-MM-DD format (fallback)
        ymd_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
        if ymd_match:
            return ymd_match.group(0)
        
        return None