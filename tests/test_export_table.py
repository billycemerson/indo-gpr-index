import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.exports.gsheet_client import GSheetClient

def test_gsheet_client_missing_credentials():
    """
    Test 1: Failsafe initialization.
    Ensures the client immediately raises an error if the JSON key is missing,
    preventing the script from hanging or throwing confusing API errors later.
    """
    fake_path = Path("non_existent_key.json")
    
    with pytest.raises(FileNotFoundError):
        GSheetClient(fake_path)

@patch("src.exports.gsheet_client.ServiceAccountCredentials")
@patch("src.exports.gsheet_client.gspread")
def test_get_existing_column_values(mock_gspread, mock_creds, tmp_path):
    """
    Test 2: Data extraction logic.
    Ensures the utility correctly extracts dates and skips the header row
    so we don't accidentally treat the word "published_date" as a data point.
    """
    # Setup: Create a temporary dummy credentials file to pass the init check
    dummy_cred_file = tmp_path / "dummy.json"
    dummy_cred_file.touch()

    # Initialize client
    client = GSheetClient(dummy_cred_file)

    # Setup: Mock a Google Worksheet object
    mock_worksheet = MagicMock()
    # Simulate Google Sheets returning a column with a header and two dates
    mock_worksheet.col_values.return_value = ["published_date", "2026-04-25", "2026-04-26"]

    # Action 1: Test default behavior (skip header)
    values_no_header = client.get_existing_column_values(mock_worksheet, col_index=1)
    
    # Assert 1: Header should be removed
    assert values_no_header == ["2026-04-25", "2026-04-26"]

    # Action 2: Test keeping the header
    values_with_header = client.get_existing_column_values(mock_worksheet, col_index=1, skip_header=False)
    
    # Assert 2: Header should remain
    assert values_with_header == ["published_date", "2026-04-25", "2026-04-26"]

@patch("src.exports.gsheet_client.ServiceAccountCredentials")
@patch("src.exports.gsheet_client.gspread")
def test_append_rows_logic(mock_gspread, mock_creds, tmp_path):
    """
    Test 3: Append logic and empty state handling.
    Ensures we don't send empty requests to the Google API, which saves bandwidth
    and prevents potential API quota errors.
    """
    # Setup: Create temporary file and client
    dummy_cred_file = tmp_path / "dummy.json"
    dummy_cred_file.touch()
    
    client = GSheetClient(dummy_cred_file)
    mock_worksheet = MagicMock()

    # Action 1: Pass an empty list (meaning no new daily data)
    empty_result = client.append_rows(mock_worksheet, [])
    
    # Assert 1: Should return 0 and NEVER call the Google API
    assert empty_result == 0
    mock_worksheet.append_rows.assert_not_called()

    # Action 2: Pass valid mock data (2 days worth of data)
    dummy_data = [
        ["2026-04-27", 100, 15.0], 
        ["2026-04-28", 120, 18.0]
    ]
    valid_result = client.append_rows(mock_worksheet, dummy_data)
    
    # Assert 2: Should return 2 and call the Google API exactly once
    assert valid_result == 2
    mock_worksheet.append_rows.assert_called_once_with(dummy_data)