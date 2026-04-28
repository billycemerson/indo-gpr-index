import sys
from pathlib import Path

# Ensure project root is in the system path to allow absolute imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import Config
from src.database.connection import get_duckdb_connection
from src.exports.gsheet_client import GSheetClient

def export_gpr_daily_to_gsheet():
    """
    Reads the 'mart_gpr_daily' table from DuckDB and appends new records 
    to the 'indo_gpr_index' Google Sheet incrementally.
    """
    print("Initiating incremental export to Google Sheets...")
    
    # Initialize the Google Sheets Client
    try:
        # Assuming you added GSHEET_KEY_PATH to your config/settings.py
        gsheet = GSheetClient(Config.GSHEET_KEY_PATH)
        worksheet = gsheet.get_worksheet("indo_gpr_index", "daily_data")
        
        # Get existing dates from Column 1 (A) to prevent duplicates
        existing_dates = gsheet.get_existing_column_values(worksheet, col_index=1)
        
    except Exception as e:
        print(f"Google Sheets Connection Error: {e}")
        return

    # Fetch Gold Layer Data from DuckDB
    try:
        con = get_duckdb_connection()
        
        # Query the data, ordered chronologically
        query = "SELECT * FROM mart_gpr_daily ORDER BY published_date ASC"
        df_gold = con.sql(query).df()
        
        # Format the date column to string (YYYY-MM-DD) for Google Sheets compatibility
        df_gold['published_date'] = df_gold['published_date'].astype(str)
        
    except Exception as e:
        print(f"DuckDB Extraction Error: {e}")
        return
    finally:
        if 'con' in locals():
            con.close()

    # Filter for New Data Only
    new_rows = []
    for _, row in df_gold.iterrows():
        date_str = row['published_date']
        
        # Incremental check: Only add if the date is not already in the sheet
        if date_str not in existing_dates:
            # Replace NaNs or Nulls with 0, then convert to a standard Python list
            row_values = row.fillna(0).tolist()
            new_rows.append(row_values)
            
    # Execute the Batch Append
    if not new_rows:
        print("No new data found. Google Sheets is already up to date.")
        return
        
    try:
        rows_added = gsheet.append_rows(worksheet, new_rows)
        print(f"Successfully appended {rows_added} new day(s) of data to Google Sheets.")
    except Exception as e:
        print(f"Failed to append data to Google Sheets: {e}")

if __name__ == "__main__":
    export_gpr_daily_to_gsheet()