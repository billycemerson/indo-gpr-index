"""
main_scraper.py
===============
The Orchestrator. This file runs the full scraping pipeline.

Design principle: this module is DUMB by design. It does not know how
Antara or Kompas work internally. It only knows that every parser has
a fetch_news(target_date) method — the contract enforced by BaseParser.

To add a new media source, register it in the PARSERS list below.
No other changes are needed in this file.
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config.settings import Config
from src.scraper.parsers.antara import AntaraParser
from src.scraper.parsers.detik import DetikParser
from src.scraper.parsers.kompas import KompasParser
from src.scraper.parsers.tempo import TempoParser
from src.scraper.parsers.tribunnews import TribunnewsParser

#  Parser registry — add new sources here only

def build_parsers() -> list:
    """
    Instantiates and returns all active parsers.
    Each parser receives whatever constructor args it needs;
    the orchestration loop below treats them all identically.
    """
    return [
        AntaraParser(),
        DetikParser(),
        KompasParser(),
        TempoParser(),
        TribunnewsParser()
    ]


#  Orchestrator

def main():
    parser = argparse.ArgumentParser(description="Multi-Source Scraper")
    parser.add_argument(
        "--date",
        type=str,
        help="Target date in YYYY-MM-DD format (defaults to yesterday)."
    )
    args = parser.parse_args()

    if args.date:
        target_date = args.date
    else:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Multi-Source Scraper — Target Date: {target_date}\n")

    all_articles: list[dict] = []
    parsers = build_parsers()

    for parser in parsers:
        print(f"--- Starting Source: {parser.source_name.title()} ---")
        try:
            articles = parser.fetch_news(target_date)
            all_articles.extend(articles)
            print(f"--- Completed {parser.source_name.title()}: {len(articles)} articles ---\n")
        except Exception as exc:
            print(f"--- Error scraping {parser.source_name}: {exc} ---\n")

    if not all_articles:
        print("Critical Warning: No data collected from any source.")
        return

    # Deduplicate by URL
    unique: dict[str, dict] = {a["link"]: a for a in all_articles}
    duplicates_removed = len(all_articles) - len(unique)
    print(f"Deduplication: removed {duplicates_removed} duplicate(s). "
          f"{len(unique)} unique articles remain.\n")

    # Persist to JSON
    output_path: Path = Config.get_raw_scrape_path(target_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(list(unique.values()), fh, ensure_ascii=False, indent=4)

    print(f"Saved {len(unique)} articles -> {output_path}")


if __name__ == "__main__":
    main()