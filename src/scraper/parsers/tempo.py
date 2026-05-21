"""
parsers/tempo.py
================
Parser for Tempo.co using HTML sitemap tables.
Targets: 
  - https://www.tempo.co/politik-sitemap.xml
  - https://www.tempo.co/hukum-sitemap.xml
  - https://www.tempo.co/ekonomi-sitemap.xml
  - https://www.tempo.co/internasional-sitemap.xml

Each sitemap contains an HTML table with structure:
  <table id="sitemap">
    <tbody>
      <tr>
        <td><a href="[article_url]">[url]</a></td>
        <td>0</td>
        <td>2026-05-19 20:37 Z</td>
      </tr>
    </tbody>
  </table>

This approach completely avoids blocking, pagination, and Playwright.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from src.scraper.base_parser import BaseParser


class TempoParser(BaseParser):
    
    # Category-specific sitemap URLs (HTML format)
    SITEMAPS = {
        "politik": "https://www.tempo.co/politik-sitemap.xml",
        "hukum": "https://www.tempo.co/hukum-sitemap.xml",
        "ekonomi": "https://www.tempo.co/ekonomi-sitemap.xml",
        "internasional": "https://www.tempo.co/internasional-sitemap.xml",
    }
    
    @property
    def source_name(self) -> str:
        return "tempo"
    
    def fetch_news(self, target_date: str) -> list[dict]:
        """
        Fetch articles by parsing HTML sitemap tables.
        target_date format: YYYY-MM-DD
        """
        all_articles = []
        
        for category, sitemap_url in self.SITEMAPS.items():
            print(f"  [Tempo] Processing {category} sitemap: {sitemap_url}")
            
            try:
                articles = self._scrape_sitemap(sitemap_url, category, target_date)
                all_articles.extend(articles)
                print(f"  [Tempo] Found {len(articles)} articles from {category} on {target_date}")
            except Exception as exc:
                print(f"  [Tempo] Error scraping {category} sitemap: {exc}")
        
        print(f"  [Tempo] Total articles for {target_date}: {len(all_articles)}")
        return self._stamp(all_articles)
    
    def _scrape_sitemap(self, sitemap_url: str, category: str, target_date: str) -> list[dict]:
        """
        Scrape raw XML sitemap and filter by target date.
        """
        articles = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            # Use response.content for XML parsing, which is safer than .text
            response = requests.get(sitemap_url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"    [Tempo] Failed to fetch {sitemap_url}: {e}")
            return articles
        
        # Parse using lxml as XML (not HTML)
        soup = BeautifulSoup(response.content, 'xml')
        
        # Find all <url> elements
        urls = soup.find_all('url')
        
        if not urls:
            print(f"    [Tempo] No <url> tags found in {sitemap_url}")
            return articles
        
        for url_node in urls:
            # Extract <loc> (URL) and <lastmod> (Date) tags
            loc_tag = url_node.find('loc')
            lastmod_tag = url_node.find('lastmod')
            
            if not loc_tag or not loc_tag.text:
                continue
                
            article_url = loc_tag.text.strip()
            date_str = lastmod_tag.text.strip() if lastmod_tag else ""
            
            # Format the date
            article_date = self._extract_date_from_string(date_str)
            
            # Filter based on the target date
            if article_date != target_date:
                continue
            
            # Check if Google News sitemap provides <news:title>
            news_title = url_node.find('news:title')
            if news_title and news_title.text:
                title = news_title.text.strip()
            else:
                # If not available, extract the title directly from the URL slug
                title = self._extract_title(article_url)
                
            articles.append({
                "title": title,
                "link": article_url,
                "category": category,
                "date_text": article_date,
            })
            
        return articles

    def _extract_title(self, article_url: str) -> str:
        """
        Extract title from URL slug because standard XML sitemaps lack title tags.
        """
        import re
        
        # Extract the last part of the URL path (e.g., /politik/.../article-title-1234567)
        url_path = article_url.split('?')[0]
        slug = url_path.rstrip('/').split('/')[-1]
        
        # Remove trailing numeric IDs if present (e.g., "-123456") and ".html" extensions
        slug = re.sub(r'-\d+$', '', slug)
        slug = slug.replace('.html', '')
        
        # Replace hyphens with spaces and capitalize
        title = slug.replace('-', ' ').title()
        return title
    
    def _extract_date_from_string(self, date_str: str) -> str:
        """
        Convert date string from sitemap to YYYY-MM-DD format.
        
        Examples:
        - "2026-05-18T21:30:01Z" -> "2026-05-18"
        - "2026-05-19 20:37 Z" -> "2026-05-19"
        """
        date_str = date_str.strip()
        
        # Try standard YYYY-MM-DD format (with optional time separated by space)
        if ' ' in date_str:
            date_part = date_str.split(' ')[0]
            if len(date_part) == 10 and date_part[4] == '-' and date_part[7] == '-':
                return date_part
        
        # Try to parse with datetime, including the XML 'T' and 'Z' format
        for fmt in [
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M %Z', 
            '%Y-%m-%d', 
            '%d %B %Y', 
            '%B %d, %Y'
        ]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If all else fails, try to extract YYYY-MM-DD pattern using Regex
        import re
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        
        print(f"    [Tempo] Warning: Could not parse date: {date_str}")
        return date_str  # Return as-is