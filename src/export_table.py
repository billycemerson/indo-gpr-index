import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import Config
from src.database.connection import get_duckdb_connection
from src.exports.gsheet_client import GSheetClient

def export_gpr_daily_to_gsheet():
    """
    Reads mart_gpr_daily from DuckDB and upserts to Google Sheets.

    Strategy:
      - New date   → append as new row
      - Existing date with different total_articles → update row in place
      - Existing date with same total_articles → skip (already up to date)

    This handles the case where a day is re-run with more sources or
    after a scraper fix, producing a higher article count and revised index.
    """
    print("Initiating incremental export to Google Sheets...")

    # Initialize Google Sheets client
    try:
        gsheet    = GSheetClient(Config.GSHEET_KEY_PATH)
        worksheet = gsheet.get_worksheet("indo_gpr_index", "daily_data")
        existing_dates = gsheet.get_existing_column_values(worksheet, col_index=1)
    except Exception as e:
        print(f"Google Sheets Connection Error: {e}")
        return

    # Fetch mart data from DuckDB
    try:
        con     = get_duckdb_connection()
        df_gold = con.sql("SELECT * FROM mart_gpr_daily ORDER BY published_date ASC").df()
        df_gold['published_date'] = df_gold['published_date'].astype(str)
    except Exception as e:
        print(f"DuckDB Extraction Error: {e}")
        return
    finally:
        if 'con' in locals():
            con.close()

    if df_gold.empty:
        print("No data in mart_gpr_daily. Nothing to export.")
        return

    # Fetch current total_articles per date from sheet for change detection
    # Column index for total_articles — matches mart_gpr_daily column order
    try:
        existing_totals = gsheet.get_existing_column_values(worksheet, col_index=2)
        # Build map: date_str → (sheet_row_number, total_articles_in_sheet)
        # Row numbers are 1-indexed; +2 accounts for header row and 0-index offset
        date_to_row = {
            date: (idx + 2, int(existing_totals[idx]) if idx < len(existing_totals) else 0)
            for idx, date in enumerate(existing_dates)
        }
    except Exception as e:
        print(f"Warning: could not fetch existing totals — will append only: {e}")
        date_to_row = {}

    new_rows    = []
    update_rows = []  # list of (row_number, row_values)

    for _, row in df_gold.iterrows():
        date_str   = row['published_date']
        row_values = row.fillna(0).tolist()

        if date_str not in existing_dates:
            # New date — append
            new_rows.append(row_values)

        else:
            # Date exists — check if total_articles changed
            sheet_row_num, sheet_total = date_to_row.get(date_str, (None, 0))
            db_total = int(row.get('total_articles', 0))

            if db_total != sheet_total and sheet_row_num:
                # Data changed — update row in place
                update_rows.append((sheet_row_num, row_values))
            else:
                print(f"  [{date_str}] Already up to date ({db_total} articles). Skipping.")

    # Execute appends
    if new_rows:
        try:
            rows_added = gsheet.append_rows(worksheet, new_rows)
            print(f"Appended {rows_added} new day(s) to Google Sheets.")
        except Exception as e:
            print(f"Failed to append new rows: {e}")

    # Execute updates
    if update_rows:
        try:
            updated = gsheet.update_rows(worksheet, update_rows)
            print(f"Updated {updated} existing day(s) in Google Sheets.")
        except Exception as e:
            print(f"Failed to update existing rows: {e}")

    if not new_rows and not update_rows:
        print("No changes detected. Google Sheets is already up to date.")


if __name__ == "__main__":
    export_gpr_daily_to_gsheet()