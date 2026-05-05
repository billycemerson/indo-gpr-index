import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

class GSheetClient:
    """A utility class for interacting with Google Sheets."""

    def __init__(self, credentials_path: Path):
        if not credentials_path.exists():
            raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds  = ServiceAccountCredentials.from_json_keyfile_name(
            str(credentials_path), self.scope
        )
        self.client = gspread.authorize(self.creds)

    def get_worksheet(self, spreadsheet_name: str, worksheet_name: str):
        try:
            return self.client.open(spreadsheet_name).worksheet(worksheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            raise Exception(f"Spreadsheet '{spreadsheet_name}' not found")
        except gspread.exceptions.WorksheetNotFound:
            raise Exception(f"Worksheet '{worksheet_name}' not found in '{spreadsheet_name}'")

    def get_existing_column_values(self, worksheet, col_index: int = 1, skip_header: bool = True):
        """Returns all values from a column. Skips header row by default."""
        values = worksheet.col_values(col_index)
        if skip_header and values:
            return values[1:]
        return values

    def append_rows(self, worksheet, data_matrix: list) -> int:
        """Appends rows to the end of the worksheet. Returns count appended."""
        if not data_matrix:
            return 0
        worksheet.append_rows(data_matrix)
        return len(data_matrix)

    def update_rows(self, worksheet, updates: list[tuple]) -> int:
        """
        Updates existing rows in place.

        Args:
            updates: list of (row_number, row_values) tuples
                     row_number is 1-indexed (matches Google Sheets row numbers)

        Returns:
            Count of rows updated.
        """
        if not updates:
            return 0

        for row_number, row_values in updates:
            # gspread range notation: row N, col 1 to len(row_values)
            cell_range = f"A{row_number}"
            worksheet.update(cell_range, [row_values])

        return len(updates)