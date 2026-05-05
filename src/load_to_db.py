import sys
import re
import argparse
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# Ensure project root is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.database.connection import get_duckdb_connection
from config.settings import Config

def process_single_file(json_path: Path, con) -> None:
    """
    Reads a single JSON file, extracts the date, and appends it to DuckDB.
    """
    if not json_path.exists():
        print(f"File {json_path.name} not found. Skipping.")
        return

    print(f"Processing {json_path.name}...")
    
    # Extract: Load NEW data into memory
    df_new = pd.read_json(json_path)
    
    if df_new.empty:
        print(f"JSON file {json_path.name} is empty. Skipping.")
        return

    # Search for a YYYY-MM-DD pattern in the filename
    date_match = re.search(r'\d{4}-\d{2}-\d{2}', json_path.name)

    if date_match:
        published_date_str = date_match.group(0)
    else:
        print(f"Warning: Could not find date in {json_path.name}. Using yesterday's date.")
        published_date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Convert to datetime.date object, NOT string
    published_date = datetime.strptime(published_date_str, '%Y-%m-%d').date()
    
    # Stamp the dataframe with the immutable date
    df_new['published_date'] = published_date

    # Dedup guard: filter out links already loaded for this data
    # Prevents duplicate row ip pipeline re-runs on the same day
    existing = con.execute(
        "SELECT link FROM raw_news WHERE published_date = ?", [published_date]
    ).fetchdf()

    if not existing.empty:
        df_new = df_new[~df_new["link"].isin(existing["link"])]

    if df_new.empty:
        print(f"All rows for {published_date} alrady loaded. Skipping")
        return

    # Append: Insert the data mapping columns by name to avoid order mismatch
    con.execute("INSERT INTO raw_news BY NAME SELECT * FROM df_new")
    print(f"Successfully appended {len(df_new)} rows stamped as {published_date}.")


def load_data(load_all: bool = False):
    """
    Orchestrates the loading process. Handles connection and determines 
    whether to load a single daily file or all historical files.
    """
    try:
        con = get_duckdb_connection()

        # Create table with explicit schema (Removed 'content' and 'PRIMARY KEY')
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw_news (
                title VARCHAR,
                link VARCHAR,
                category VARCHAR,
                date_text VARCHAR,
                published_date DATE,
                source VARCHAR
            )
        """)
        
        if load_all:
            raw_dir = Config.get_raw_scrape_path().parent
            print(f"Scanning directory {raw_dir} for historical data...")
            
            # Use glob to find all JSON files and sort them chronologically
            json_files = sorted(raw_dir.glob("*.json"))
            
            if not json_files:
                print("No JSON files found to process.")
                return
                
            for file_path in json_files:
                process_single_file(file_path, con)
                
        else:
            # Default behavior: Process only the specific daily file
            target_file = Config.get_raw_scrape_path()
            process_single_file(target_file, con)
            
    except Exception as e:
        print(f"Error during database operation: {e}")
        
    finally:
        # Cleanup: Ensure connection is closed
        if 'con' in locals():
            con.close()
            print("Database connection closed.")

if __name__ == "__main__":
    # Setup command line argument parsing
    parser = argparse.ArgumentParser(description="Load scraped JSON data into DuckDB.")
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Load all JSON files in the raw directory. If omitted, loads only today's target file."
    )
    
    args = parser.parse_args()
    
    # Execute with the provided flag
    load_data(load_all=args.all)