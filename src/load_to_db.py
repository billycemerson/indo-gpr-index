import sys
from pathlib import Path
import pandas as pd

# Ensure project root is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.database.connection import get_duckdb_connection
from config.settings import Config

def load_json_to_duckdb():
    """
    Loads the daily scraped JSON file into the DuckDB raw_news table.
    Acts as the 'Load' step in the ELT pipeline.
    """
    json_path = Config.get_raw_scrape_path()
    
    # Safety Check: Does the file exist?
    if not json_path.exists():
        print(f"File {json_path} not found. Skipping load.")
        return

    print(f"Loading data from {json_path}...")
    
    try:
        # Extract: Load NEW data into memory
        df_new = pd.read_json(json_path)
        
        if df_new.empty:
            print("JSON file is empty. Nothing to load.")
            return

        # Connect: Use the centralized connection manager
        con = get_duckdb_connection()
        
        # Load: Create table if it doesn't exist (Day 1)
        con.execute("""
            CREATE TABLE IF NOT EXISTS raw_news AS 
            SELECT * FROM df_new WHERE 1=0
        """)
        
        # Append: Insert the new daily data
        con.execute("INSERT INTO raw_news SELECT * FROM df_new")
        
        print(f"Successfully appended {len(df_new)} rows to DuckDB 'raw_news' table.")
        
    except Exception as e:
        print(f"Error loading data to DuckDB: {e}")
        
    finally:
        # Cleanup: Ensure connection is closed even if an error occurs
        if con is not None:
            con.close()
            print("Connection closed.")

if __name__ == "__main__":
    load_json_to_duckdb()