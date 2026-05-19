"""
parsers/tribunnews.py
=====================
Parser for Tribunnews.
Target:
  page 1 : https://www.tribunnews.com/index-news/[category]
  page 2+: https://www.tribunnews.com/index-news/[category]?date=&page=N

  Note: ?date= param appears in the URL when paginating but is not used by
  the server for filtering — Tribunnews always returns a mixed-date list.
  We filter to target_date ourselves by parsing the <time> tag.

Date format in HTML: "Sabtu, 16 Mei 2026 10:37 WIB" (inside <time class="grey">)
Title             : use <a title="..."> attr — avoids picking up <i> icon text
Stop condition    : first article older than target_date ends pagination
                    (articles are newest-first)
"""

import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from src.scraper.base_parser import BaseParser


class TribunnewsParser(BaseParser):

    BASE_URL      = "https://www.tribunnews.com/index-news"
    CATEGORY      = ["nasional", "internasional"]
    MAX_PAGES     = 20
    REQUEST_DELAY = 1

    _MONTHS = {
        "januari": 1, "februari": 2, "maret": 3, "april": 4,
        "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
        "september": 9, "oktober": 10, "november": 11, "desember": 12,
    }

    def __init__(self):
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept":          "text/html,application/xhtml+xml",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
            "Referer":         "https://www.tribunnews.com/",
        }

    #  BaseParser contract

    @property
    def source_name(self) -> str:
        return "tribunnews"

    def fetch_news(self, target_date: str) -> list[dict]:
        """
        Paginates each category index, collects articles matching target_date,
        stops when an article older than target_date is encountered.

        Args:
            target_date (str): Date in YYYY-MM-DD format.

        Returns:
            list[dict]: Stamped article list.
        """
        all_articles = []

        for category in self.CATEGORY:
            print(f"  [Tribunnews] Processing category: {category}")
            
            category_results = []
            
            for page in range(1, self.MAX_PAGES + 1):
                url = self._build_url(category, page)
                print(f"    [Tribunnews] Fetching page {page}: {url}")

                try:
                    response = requests.get(url, headers=self._headers, timeout=10)
                    response.raise_for_status()
                except requests.exceptions.RequestException as exc:
                    print(f"    [Tribunnews] Error fetching page {page}: {exc}")
                    break

                articles, stop, found_any = self._parse_index_page(response.text, target_date, category)
                category_results.extend(articles)

                if stop:
                    print(f"    [Tribunnews] Reached older articles at page {page}, stopping category.")
                    break

                if not found_any:
                    print(f"    [Tribunnews] Empty page at {page}, stopping category.")
                    break

                time.sleep(self.REQUEST_DELAY)
            
            print(f"    [Tribunnews] Collected {len(category_results)} articles for category '{category}'")
            all_articles.extend(category_results)

        print(f"  [Tribunnews] Total collected across all categories: {len(all_articles)}")
        return self._stamp(all_articles)

    
    #  Internal helpers

    def _build_url(self, category: str, page: int) -> str:
        """
        Builds URL for specific category and page.
        
        Page 1: https://www.tribunnews.com/index-news/[category]
        Page 2+: https://www.tribunnews.com/index-news/[category]?date=&page=N
        
        The date param is required by Tribunnews to avoid a redirect 
        but is not used for filtering.
        """
        if page == 1:
            return f"{self.BASE_URL}/{category}"
        return f"{self.BASE_URL}/{category}?date=&page={page}"
 
    def _parse_index_page(self, html: str, target_date: str, category: str) -> tuple[list[dict], bool, bool]:
        """
        Parses one Tribunnews index page.
 
        Returns:
            (articles, stop, found_any)
            articles  : list of article dicts matching target_date
            stop      : True when an article older than target_date is found
            found_any : True when the page had parseable articles at all —
                        distinguishes "page full of today articles, keep going"
                        from "page empty, stop"
        """
        soup      = BeautifulSoup(html, "html.parser")
        articles  = []
        stop      = False
        found_any = False
 
        for item in soup.select("li.ptb15"):
            time_tag = item.find("time", class_="grey")
            a_tag    = item.select_one("h3.f16.fbo a")
 
            if not time_tag or not a_tag:
                continue
 
            date_text    = time_tag.get_text(strip=True)
            article_date = self._parse_date(date_text)
 
            if article_date is None:
                continue
 
            found_any = True  # page has real articles — do not stop early
 
            if article_date == target_date:
                articles.append({
                    "title":     a_tag.get("title", "").strip(),
                    "link":      a_tag["href"],
                    "category":  category,  # Use the specific category
                    "date_text": date_text,
                })
 
            elif article_date < target_date:
                # Articles are newest-first — older means nothing below matches
                stop = True
                break
 
            # article_date > target_date → today's article, skip and continue
 
        return articles, stop, found_any
 
    def _parse_date(self, date_text: str) -> str | None:
        """
        Converts Tribunnews date string to YYYY-MM-DD.
 
        Input : "Sabtu, 16 Mei 2026 10:37 WIB"
        Output: "2026-05-16"
        Returns None if parsing fails — article is skipped.
        """
        try:
            parts = date_text.replace(",", "").split()
            # ['Sabtu', '16', 'Mei', '2026', '10:37', 'WIB']
            day   = int(parts[1])
            month = self._MONTHS[parts[2].lower()]
            year  = int(parts[3])
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except (IndexError, KeyError, ValueError) as exc:
            print(f"  [Tribunnews] Warning: could not parse date '{date_text}': {exc}")
            return None