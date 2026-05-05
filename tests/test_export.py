"""
test_export.py
==============
Unit tests for GSheetClient and the export_gpr_daily_to_gsheet() pipeline.

Rule: ZERO real Google Sheets or DuckDB connections. Both are fully mocked.
We test the incremental dedup logic — the only non-trivial Python here.

We do NOT test gspread internals — that's the library's own test suite.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.exports.gsheet_client import GSheetClient


#  GSheetClient unit tests

class TestGSheetClientInit:

    def test_raises_if_credentials_file_missing(self, tmp_path):
        """Should raise FileNotFoundError immediately — no silent failures."""
        missing_creds = tmp_path / "no_such_key.json"

        with pytest.raises(FileNotFoundError):
            GSheetClient(missing_creds)

    def test_initializes_with_valid_credentials_file(self, tmp_path):
        """A valid (mocked) credentials path should not raise."""
        fake_creds = tmp_path / "service_account.json"
        fake_creds.write_text("{}")  # content doesn't matter — oauth is mocked

        with patch("src.exports.gsheet_client.ServiceAccountCredentials.from_json_keyfile_name"):
            with patch("src.exports.gsheet_client.gspread.authorize"):
                client = GSheetClient(fake_creds)  # should not raise

        assert client is not None


class TestGSheetClientGetExistingColumnValues:

    def _make_client(self, tmp_path):
        fake_creds = tmp_path / "creds.json"
        fake_creds.write_text("{}")
        with patch("src.exports.gsheet_client.ServiceAccountCredentials.from_json_keyfile_name"):
            with patch("src.exports.gsheet_client.gspread.authorize"):
                return GSheetClient(fake_creds)

    def test_skips_header_row_by_default(self, tmp_path):
        client = self._make_client(tmp_path)
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = ["published_date", "2025-01-01", "2025-01-02"]

        result = client.get_existing_column_values(mock_ws, col_index=1)

        assert result == ["2025-01-01", "2025-01-02"]

    def test_includes_header_when_skip_false(self, tmp_path):
        client = self._make_client(tmp_path)
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = ["published_date", "2025-01-01"]

        result = client.get_existing_column_values(mock_ws, col_index=1, skip_header=False)

        assert result[0] == "published_date"

    def test_returns_empty_list_on_empty_column(self, tmp_path):
        client = self._make_client(tmp_path)
        mock_ws = MagicMock()
        mock_ws.col_values.return_value = []

        result = client.get_existing_column_values(mock_ws)

        assert result == []


class TestGSheetClientAppendRows:

    def _make_client(self, tmp_path):
        fake_creds = tmp_path / "creds.json"
        fake_creds.write_text("{}")
        with patch("src.exports.gsheet_client.ServiceAccountCredentials.from_json_keyfile_name"):
            with patch("src.exports.gsheet_client.gspread.authorize"):
                return GSheetClient(fake_creds)

    def test_appends_rows_and_returns_count(self, tmp_path):
        client = self._make_client(tmp_path)
        mock_ws = MagicMock()
        rows = [["2025-01-01", 10.5], ["2025-01-02", 11.2]]

        count = client.append_rows(mock_ws, rows)

        mock_ws.append_rows.assert_called_once_with(rows)
        assert count == 2

    def test_returns_zero_and_skips_call_on_empty_data(self, tmp_path):
        client = self._make_client(tmp_path)
        mock_ws = MagicMock()

        count = client.append_rows(mock_ws, [])

        mock_ws.append_rows.assert_not_called()
        assert count == 0


#  export_gpr_daily_to_gsheet() integration logic

class TestExportPipelineDedup:
    """
    Tests the incremental dedup logic inside export_gpr_daily_to_gsheet().
    GSheetClient and DuckDB are fully mocked — only Python logic is tested.
    """

    def _run_export(self, df_gold: pd.DataFrame, existing_dates: list[str]):
        """Helper: runs the export pipeline with injected mock data."""
        from src.export_table import export_gpr_daily_to_gsheet

        mock_gsheet = MagicMock()
        mock_gsheet.get_worksheet.return_value = MagicMock()
        mock_gsheet.get_existing_column_values.return_value = existing_dates
        mock_gsheet.append_rows.return_value = len(df_gold)

        mock_con = MagicMock()
        mock_con.sql.return_value.df.return_value = df_gold

        with patch("src.export_table.GSheetClient", return_value=mock_gsheet):
            with patch("src.export_table.get_duckdb_connection", return_value=mock_con):
                with patch("src.export_table.Config") as mock_cfg:
                    mock_cfg.GSHEET_KEY_PATH = Path("/fake/key.json")
                    export_gpr_daily_to_gsheet()

        return mock_gsheet

    def test_new_dates_are_appended(self):
        """Dates not in the sheet must be sent to append_rows."""
        df = pd.DataFrame({"published_date": ["2025-01-01", "2025-01-02"], "score": [1.0, 2.0]})
        existing = []  # sheet is empty

        mock_gsheet = self._run_export(df, existing)

        mock_gsheet.append_rows.assert_called_once()
        rows_sent = mock_gsheet.append_rows.call_args[0][1]
        assert len(rows_sent) == 2

    def test_existing_dates_are_not_duplicated(self):
        """Dates already in the sheet must be filtered out."""
        df = pd.DataFrame({"published_date": ["2025-01-01", "2025-01-02"], "score": [1.0, 2.0]})
        existing = ["2025-01-01"]  # one date already uploaded

        mock_gsheet = self._run_export(df, existing)

        rows_sent = mock_gsheet.append_rows.call_args[0][1]
        assert len(rows_sent) == 1  # only the new date

    def test_no_append_when_fully_up_to_date(self):
        """If all dates exist in the sheet, append_rows must not be called."""
        df = pd.DataFrame({"published_date": ["2025-01-01"], "score": [1.0]})
        existing = ["2025-01-01"]

        mock_gsheet = self._run_export(df, existing)

        mock_gsheet.append_rows.assert_not_called()

    def test_empty_db_result_exits_cleanly(self):
        """Empty DuckDB result should not crash or call append_rows."""
        df = pd.DataFrame({"published_date": [], "score": []})
        existing = []

        mock_gsheet = self._run_export(df, existing)

        mock_gsheet.append_rows.assert_not_called()