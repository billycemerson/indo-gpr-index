"""
parsers/tempo.py
================
Parser for Tempo.co Indeks.
Target: https://www.tempo.co/indeks?rubric_slug=politik&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        page=N appended only for page > 1

Tempo uses Nuxt.js (CSR) — Playwright required for rendered DOM.

Pagination strategy:
  - Fetch page 1 first
  - Read total page count from <button data-type="page"> in the nav
  - Loop only up to that count — avoids infinite loop when Tempo returns
    stale data for out-of-range page numbers

Install once:
    pip install playwright
    playwright install chromium
"""

import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from src.scraper.base_parser import BaseParser


class TempoParser(BaseParser):

    BASE_URL      = "https://www.tempo.co/indeks"
    CATEGORIES    = ["politik", "hukum", "ekonomi"]
    REQUEST_DELAY = 2

    #  BaseParser contract

    @property
    def source_name(self) -> str:
        return "tempo"

    def fetch_news(self, target_date: str) -> list[dict]:
        all_articles = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]  # required on Linux CI
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )

            for category in self.CATEGORIES:
                print(f"  [Tempo] Processing category: {category}")
                try:
                    articles = self._scrape_category(ctx, category, target_date)
                    all_articles.extend(articles)
                    print(f"  [Tempo] Fetched {len(articles)} articles from '{category}'")
                except Exception as exc:
                    print(f"  [Tempo] Error scraping '{category}': {exc}")

            browser.close()

        return self._stamp(all_articles)

    #  Internal helpers

    def _scrape_category(self, ctx, category: str, target_date: str) -> list[dict]:
        """
        Fetches page 1 first to determine total page count,
        then iterates only up to that number.
        """
        results = []

        # --- Page 1: fetch + detect total pages ---
        url_p1 = self._build_url(category, target_date, 1)
        print(f"  [Tempo] Fetching: {url_p1}")

        html = self._render_page(ctx, url_p1)
        if html is None:
            return results

        total_pages = self._get_total_pages(html)
        print(f"  [Tempo] Total pages for '{category}': {total_pages}")

        articles = self._parse_index_page(html, category, target_date)
        results.extend(articles)

        # --- Page 2..N ---
        for page_num in range(2, total_pages + 1):
            time.sleep(self.REQUEST_DELAY)
            url = self._build_url(category, target_date, page_num)
            print(f"  [Tempo] Fetching: {url}")

            html = self._render_page(ctx, url)
            if html is None:
                break

            articles = self._parse_index_page(html, category, target_date)
            results.extend(articles)

        return results

    def _get_total_pages(self, html: str) -> int:
        """
        Reads max page number from the pagination nav.

        Looks for: <button data-type="page" value="N">N</button>
        Returns 1 if nav is absent (single-page result).
        """
        soup         = BeautifulSoup(html, "html.parser")
        page_buttons = soup.select('button[data-type="page"]')

        if not page_buttons:
            return 1

        try:
            return max(int(b["value"]) for b in page_buttons)
        except (KeyError, ValueError):
            return 1

    def _render_page(self, ctx, url: str) -> str | None:
        """
        Opens URL in a new Playwright page and returns rendered HTML.

        Strategy: wait for the page container first (always present),
        then do a short optional wait for articles. If no articles appear
        within the short window, return the HTML anyway so _parse_index_page
        can return [] cleanly — instead of raising a timeout error.

        Returns None only on hard failures (navigation error, crash).
        """
        page = ctx.new_page()
        try:
            page.goto(url, timeout=30000)

            # Wait for the page shell — always present even when 0 articles
            page.wait_for_selector("nav", timeout=15000)

            # Short grace period for articles to hydrate
            try:
                page.wait_for_selector("aside.flex", timeout=3000)
            except PlaywrightTimeoutError:
                # No articles found — valid empty result, not an error
                print(f"  [Tempo] No articles found (empty category or date): {url}")

            return page.content()
        except PlaywrightTimeoutError:
            print(f"  [Tempo] Timeout loading page: {url}")
            return None
        except Exception as exc:
            print(f"  [Tempo] Error rendering page: {exc}")
            return None
        finally:
            page.close()

    def _build_url(self, category: str, target_date: str, page: int) -> str:
        url = (
            f"{self.BASE_URL}"
            f"?rubric_slug={category}"
            f"&start_date={target_date}"
            f"&end_date={target_date}"
        )
        if page > 1:
            url += f"&page={page}"
        return url

    def _parse_index_page(self, html: str, category: str, target_date: str) -> list[dict]:
        """
        Parses rendered HTML. Date injected from target_date —
        Tempo articles have no date element in the DOM.
        """
        soup     = BeautifulSoup(html, "html.parser")
        articles = []

        for aside in soup.select("aside.flex"):
            figcaption = aside.find("figcaption")
            if not figcaption:
                continue

            title_tag = figcaption.find("a", href=True)
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            if not title:
                continue

            link = (
                title_tag.get("data-mrf-link")
                or f"https://www.tempo.co{title_tag['href']}"
            )

            articles.append({
                "title":     title,
                "link":      link,
                "category":  category,
                "date_text": target_date,
            })

        return articles