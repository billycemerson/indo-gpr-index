import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

class GSheetClient:
    """A utility class for interacting with Google Sheets."""
    def __init__(self, credentials_path: Path):
        """Initialize the GSheetClient."""
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        if not credentials_path.exists():
            raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

        self.creds = ServiceAccountCredentials.from_json_keyfile_name(
            str(credentials_path), self.scope
        )
        self.client = gspread.authorize(self.creds)

    def get_worksheet(self, spreadsheet_name: str, worksheet_name: str):
        """Connect to a worksheet in a spreadsheet."""
        try:
            spreadsheet = self.client.open(spreadsheet_name)
            return spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            raise Exception(f"Spreadsheet {spreadsheet_name} not found")
        except gspread.exceptions.WorksheetNotFound:
            raise Exception(f"Worksheet {worksheet_name} not found in {spreadsheet_name}")

    def get_existing_column_values(self, worksheet, col_index: int = 1, skip_header: bool = True):
        """Retrieve all values from a specific column in the worksheet."""
        values = worksheet.col_values(col_index)
        if skip_header and len(values) > 0:
            return values[1:]
        return values

    def append_rows(self, worksheet, data_matrix: list):
        """Append rows to a worksheet."""
        if not data_matrix:
            return 0
        
        worksheet.append_rows(data_matrix)
        return len(data_matrix)