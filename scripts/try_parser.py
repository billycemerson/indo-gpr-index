# scripts/try_parser.py
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import Config

# swap this import to test a different parser
from src.scraper.parsers.tempo import TempoParser
parser = TempoParser()

target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

print(f"Testing: {parser}")
print(f"Target date: {target_date}\n")

results = parser.fetch_news(target_date)

print(f"\nTotal fetched: {len(results)}")
print(f"Sample (first 3):")
print(json.dumps(results[:3], indent=2, ensure_ascii=False))

# Quick field validation
required = {"title", "link", "category", "date_text", "source"}
for i, article in enumerate(results):
    missing = required - article.keys()
    if missing:
        print(f"WARNING: article[{i}] missing fields: {missing}")