import sys
from pathlib import Path
import json

# Ensure project root is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import Config
from src.scraper.engine import ScraperEngine

def main():
    engine = ScraperEngine(Config.BASE_URL, Config.HEADERS)
    
    # Define categories you want to scrape here
    categories = ['politik', 'ekonomi', 'hukum']
    
    all_scraped_data = []

    for category in categories:
        print(f"Processing category: {category}")
        try:
            articles = engine.scrape_category(category)
            
            # Add category metadata to each article for downstream analysis
            for article in articles:
                article['category'] = category
                
            all_scraped_data.extend(articles)
            print(f"  Fetched {len(articles)} articles")
            
        except Exception as e:
            print(f"  Error scraping {category}: {e}")

    # Output management
    output_path = Config.get_raw_scrape_path()
    
    if all_scraped_data:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_scraped_data, f, ensure_ascii=False, indent=4)
        print(f"\nTotal: {len(all_scraped_data)} articles saved to {output_path}")
    else:
        print("\nNo data was collected.")

if __name__ == "__main__":
    main()