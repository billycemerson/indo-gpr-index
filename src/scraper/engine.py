import requests
import time
from .parser import AntaraParser

class ScraperEngine:
    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers
        self.parser = AntaraParser()

    def _classify_date(self, date_text):
        """Determines if the article is from today, yesterday, or older."""
        text = date_text.lower()
        if any(x in text for x in ['menit', 'jam', 'detik']):
            return 'today'
        if 'kemarin' in text:
            return 'yesterday'
        return 'older'

    def scrape_category(self, category, target_date='yesterday', max_pages=10):
        """Scrapes articles until it hits a date older than the target."""
        all_results = []
        page = 1
        
        while page <= max_pages:
            url = f"{self.base_url}/{category}/{page}" if page > 1 else f"{self.base_url}/{category}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            articles = self.parser.parse_list_page(response.text)
            if not articles:
                break
                
            stop_signal = False
            for art in articles:
                age = self._classify_date(art['date_text'])
                
                if age == target_date:
                    all_results.append(art)
                elif age == 'older':
                    # Assuming articles are sorted by newest first,
                    # once we hit 'older', we can stop.
                    stop_signal = True
                    break
            
            if stop_signal:
                break
                
            page += 1
            time.sleep(1) # Respectful delay
            
        return all_results