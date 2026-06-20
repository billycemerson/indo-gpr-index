import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import Config
from src.database.connection import get_duckdb_connection
from src.exports.gsheet_client import GSheetClient


# ──────────────────────────────────────────────────────────────────
# Mart → Worksheet registry
# Each entry maps a DuckDB table to its target worksheet tab and the
# column used as the unique key for upsert. Column name and dtype
# differ between daily/weekly/monthly granularity.
# ──────────────────────────────────────────────────────────────────
MART_CONFIG = {
    "mart_gpr_daily": {
        "worksheet": "daily_data",
        "key_column": "published_date",
        "change_column": "total_articles",
    },
    "mart_gpr_weekly": {
        "worksheet": "weekly_data",
        "key_column": "week_start",
        "change_column": "total_articles",
    },
    "mart_gpr_monthly": {
        "worksheet": "monthly_data",
        "key_column": "month_start",
        "change_column": "total_articles",
    },
}


def _stringify_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts every date/datetime/Timestamp column to plain string.

    gspread serializes row values to JSON before sending to the Sheets API.
    pandas/DuckDB return DATE columns as datetime64 or python date objects,
    neither of which are JSON serializable — this must run on ALL such
    columns, not just the key column, since weekly/monthly marts have
    extra date columns (first_day_in_week, last_day_in_month, etc).
    """
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
        elif df[col].dtype == "object":
            # Catches python date/Timestamp objects stored as object dtype
            # (common when DuckDB's .df() doesn't infer datetime64 directly)
            df[col] = df[col].apply(
                lambda v: v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else v
            )
    return df


def export_mart_to_gsheet(table_name: str, spreadsheet_name: str = "indo_gpr_index"):
    """
    Reads a single mart table from DuckDB and upserts it to its mapped
    Google Sheets worksheet.

    Strategy:
      - New key   → append as new row
      - Existing key with different change_column value → update row in place
      - Existing key with same change_column value → skip (already up to date)

    This handles the case where a period is re-run with more sources or
    after a scraper/keyword fix, producing a different article count and
    revised index.
    """
    if table_name not in MART_CONFIG:
        print(f"Unknown mart '{table_name}'. Must be one of: {list(MART_CONFIG.keys())}")
        return

    cfg            = MART_CONFIG[table_name]
    worksheet_name = cfg["worksheet"]
    key_column     = cfg["key_column"]
    change_column  = cfg["change_column"]

    print(f"Initiating incremental export: {table_name} -> '{worksheet_name}'...")

    # Initialize Google Sheets client
    try:
        gsheet    = GSheetClient(Config.GSHEET_KEY_PATH)
        worksheet = gsheet.get_worksheet(spreadsheet_name, worksheet_name)
        existing_keys = gsheet.get_existing_column_values(worksheet, col_index=1)
    except Exception as e:
        print(f"  Google Sheets Connection Error: {e}")
        return

    # Fetch mart data from DuckDB
    try:
        con     = get_duckdb_connection()
        df_gold = con.sql(f"SELECT * FROM {table_name} ORDER BY {key_column} ASC").df()
        df_gold = _stringify_dates(df_gold)   # convert ALL date-like columns, not just the key

    except Exception as e:
        print(f"  DuckDB Extraction Error: {e}")
        return
    finally:
        if 'con' in locals():
            con.close()

    if df_gold.empty:
        print(f"  No data in {table_name}. Nothing to export.")
        return

    # Fetch current change_column values per key from sheet for change detection
    try:
        change_col_index = list(df_gold.columns).index(change_column) + 1
        existing_changes = gsheet.get_existing_column_values(worksheet, col_index=change_col_index)
        # Build map: key → (sheet_row_number, change_value_in_sheet)
        # Row numbers are 1-indexed; +2 accounts for header row and 0-index offset
        key_to_row = {
            key: (idx + 2, int(existing_changes[idx]) if idx < len(existing_changes) and existing_changes[idx] else 0)
            for idx, key in enumerate(existing_keys)
        }
    except Exception as e:
        print(f"  Warning: could not fetch existing '{change_column}' values — will append only: {e}")
        key_to_row = {}

    new_rows    = []
    update_rows = []  # list of (row_number, row_values)

    for _, row in df_gold.iterrows():
        key_val    = row[key_column]
        row_values = row.fillna(0).tolist()

        if key_val not in existing_keys:
            # New period — append
            new_rows.append(row_values)

        else:
            # Period exists — check if change_column value changed
            sheet_row_num, sheet_value = key_to_row.get(key_val, (None, 0))
            db_value = row.get(change_column, 0)
            try:
                db_value = int(db_value)
            except (ValueError, TypeError):
                db_value = 0

            if db_value != sheet_value and sheet_row_num:
                # Data changed — update row in place
                update_rows.append((sheet_row_num, row_values))
            else:
                print(f"    [{key_val}] Already up to date ({db_value} articles). Skipping.")

    # Execute appends
    if new_rows:
        try:
            rows_added = gsheet.append_rows(worksheet, new_rows)
            print(f"  Appended {rows_added} new row(s) to '{worksheet_name}'.")
        except Exception as e:
            print(f"  Failed to append new rows: {e}")

    # Execute updates
    if update_rows:
        try:
            updated = gsheet.update_rows(worksheet, update_rows)
            print(f"  Updated {updated} existing row(s) in '{worksheet_name}'.")
        except Exception as e:
            print(f"  Failed to update existing rows: {e}")

    if not new_rows and not update_rows:
        print(f"  No changes detected. '{worksheet_name}' is already up to date.")


def export_all_marts_to_gsheet():
    """
    Exports daily, weekly, and monthly marts to their respective worksheets.
    Call this from the daily pipeline.
    """
    for table_name in MART_CONFIG:
        export_mart_to_gsheet(table_name)
        print()  # blank line between marts in logs


if __name__ == "__main__":
    export_all_marts_to_gsheet()