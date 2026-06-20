"""
test_export.py
==============
Unit tests for GSheetClient and the export_mart_to_gsheet() pipeline.

Rule: ZERO real Google Sheets or DuckDB connections. Both are fully mocked.
We test the incremental upsert logic — the only non-trivial Python here.

We do NOT test gspread internals — that's the library's own test suite.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.exports.gsheet_client import GSheetClient


# ──────────────────────────────────────────────────────────────────
#  GSheetClient unit tests
# ──────────────────────────────────────────────────────────────────

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


class TestGSheetClientUpdateRows:

    def _make_client(self, tmp_path):
        fake_creds = tmp_path / "creds.json"
        fake_creds.write_text("{}")
        with patch("src.exports.gsheet_client.ServiceAccountCredentials.from_json_keyfile_name"):
            with patch("src.exports.gsheet_client.gspread.authorize"):
                return GSheetClient(fake_creds)

    def test_updates_rows_and_returns_count(self, tmp_path):
        client = self._make_client(tmp_path)
        mock_ws = MagicMock()
        updates = [(3, ["2025-01-01", 99]), (5, ["2025-01-03", 42])]

        count = client.update_rows(mock_ws, updates)

        assert mock_ws.update.call_count == 2
        assert count == 2

    def test_returns_zero_and_skips_call_on_empty_updates(self, tmp_path):
        client = self._make_client(tmp_path)
        mock_ws = MagicMock()

        count = client.update_rows(mock_ws, [])

        mock_ws.update.assert_not_called()
        assert count == 0


# ──────────────────────────────────────────────────────────────────
#  export_mart_to_gsheet() integration logic
# ──────────────────────────────────────────────────────────────────

class TestExportMartUpsert:
    """
    Tests the incremental upsert logic inside export_mart_to_gsheet().
    GSheetClient and DuckDB are fully mocked — only Python logic is tested.

    Only mart_gpr_daily is registered in MART_CONFIG. Weekly and monthly
    aggregations are handled by Google Sheets formulas (SUMPRODUCT on the
    daily_data tab) to avoid incorrect calculations caused by DuckDB being
    reset on every GitHub Actions run.
    """

    def _run_export(
        self,
        table_name: str,
        df_gold: pd.DataFrame,
        existing_keys: list,
        existing_change_values: list = None,
    ):
        """
        Helper: runs export_mart_to_gsheet with injected mock data.

        get_existing_column_values is called twice in the real function:
          1st call → existing keys (col_index=1)
          2nd call → existing change_column values (col_index=N)
        side_effect supplies both responses in order.
        """
        from src.export_table import export_mart_to_gsheet

        mock_gsheet = MagicMock()
        mock_gsheet.get_worksheet.return_value = MagicMock()
        mock_gsheet.get_existing_column_values.side_effect = [
            existing_keys,
            existing_change_values if existing_change_values is not None else [],
        ]
        mock_gsheet.append_rows.return_value = len(df_gold)
        mock_gsheet.update_rows.return_value = 0

        mock_con = MagicMock()
        mock_con.sql.return_value.df.return_value = df_gold

        with patch("src.export_table.GSheetClient", return_value=mock_gsheet):
            with patch("src.export_table.get_duckdb_connection", return_value=mock_con):
                with patch("src.export_table.Config") as mock_cfg:
                    mock_cfg.GSHEET_KEY_PATH = Path("/fake/key.json")
                    export_mart_to_gsheet(table_name)

        return mock_gsheet

    def test_unknown_mart_name_does_not_crash(self):
        """An unregistered table name should print a warning and return, not raise."""
        from src.export_table import export_mart_to_gsheet

        # Should not raise — just logs and returns
        export_mart_to_gsheet("mart_does_not_exist")

    def test_new_dates_are_appended(self):
        """Dates not in the sheet must be sent to append_rows."""
        df = pd.DataFrame({
            "published_date": ["2025-01-01", "2025-01-02"],
            "total_articles": [10, 12],
        })
        mock_gsheet = self._run_export("mart_gpr_daily", df, existing_keys=[])

        mock_gsheet.append_rows.assert_called_once()
        rows_sent = mock_gsheet.append_rows.call_args[0][1]
        assert len(rows_sent) == 2

    def test_existing_dates_with_same_value_are_skipped(self):
        """Dates already in the sheet with unchanged total_articles must be skipped entirely."""
        df = pd.DataFrame({
            "published_date": ["2025-01-01"],
            "total_articles": [10],
        })
        mock_gsheet = self._run_export(
            "mart_gpr_daily", df,
            existing_keys=["2025-01-01"],
            existing_change_values=["10"],
        )

        mock_gsheet.append_rows.assert_not_called()
        mock_gsheet.update_rows.assert_not_called()

    def test_existing_dates_with_different_value_are_updated(self):
        """Dates already in the sheet with changed total_articles must be sent to update_rows."""
        df = pd.DataFrame({
            "published_date": ["2025-01-01"],
            "total_articles": [25],  # changed from 10 -> 25, e.g. re-scrape added more articles
        })
        mock_gsheet = self._run_export(
            "mart_gpr_daily", df,
            existing_keys=["2025-01-01"],
            existing_change_values=["10"],
        )

        mock_gsheet.append_rows.assert_not_called()
        mock_gsheet.update_rows.assert_called_once()
        rows_updated = mock_gsheet.update_rows.call_args[0][1]
        assert len(rows_updated) == 1

    def test_mixed_new_and_existing_dates(self):
        """A batch with both new and unchanged dates must append only the new ones."""
        df = pd.DataFrame({
            "published_date": ["2025-01-01", "2025-01-02"],
            "total_articles": [10, 15],
        })
        mock_gsheet = self._run_export(
            "mart_gpr_daily", df,
            existing_keys=["2025-01-01"],
            existing_change_values=["10"],  # 2025-01-01 unchanged
        )

        rows_sent = mock_gsheet.append_rows.call_args[0][1]
        assert len(rows_sent) == 1  # only 2025-01-02 is new

    def test_empty_db_result_exits_cleanly(self):
        """Empty DuckDB result should not crash or call append_rows."""
        df = pd.DataFrame({"published_date": [], "total_articles": []})
        mock_gsheet = self._run_export("mart_gpr_daily", df, existing_keys=[])

        mock_gsheet.append_rows.assert_not_called()
        mock_gsheet.update_rows.assert_not_called()

    def test_weekly_mart_is_not_registered(self):
        """
        mart_gpr_weekly must NOT be in MART_CONFIG.

        Weekly aggregation is now calculated directly in Google Sheets using
        SUMPRODUCT formulas on the accumulated daily_data tab, because DuckDB
        is reset on every GitHub Actions run — meaning only 1 day of data
        exists in the database at export time, making a dbt-based weekly
        rollup incorrect.
        """
        from src.export_table import MART_CONFIG
        assert "mart_gpr_weekly" not in MART_CONFIG

    def test_monthly_mart_is_not_registered(self):
        """
        mart_gpr_monthly must NOT be in MART_CONFIG.

        Same reason as weekly: DuckDB resets each run, so the monthly dbt
        rollup would only see a single day of data. Monthly aggregation is
        handled in Google Sheets instead.
        """
        from src.export_table import MART_CONFIG
        assert "mart_gpr_monthly" not in MART_CONFIG


class TestStringifyDates:
    """
    Tests _stringify_dates() — the fix for the 'Timestamp is not JSON
    serializable' error that occurred when weekly/monthly marts' extra
    date columns (first_day_in_week, last_day_in_month, etc.) were left
    as datetime64/Timestamp objects.
    """

    def test_converts_datetime64_column_to_string(self):
        from src.export_table import _stringify_dates

        df = pd.DataFrame({
            "week_start": pd.to_datetime(["2026-05-04", "2026-05-11"]),
            "total_articles": [27, 12],
        })
        result = _stringify_dates(df)

        assert result["week_start"].tolist() == ["2026-05-04", "2026-05-11"]
        assert isinstance(result["week_start"].iloc[0], str)

    def test_converts_object_dtype_date_objects_to_string(self):
        from src.export_table import _stringify_dates
        from datetime import date

        df = pd.DataFrame({
            "published_date": pd.array([date(2026, 5, 4), date(2026, 5, 5)], dtype="object"),
            "total_articles": [10, 12],
        })
        result = _stringify_dates(df)

        assert result["published_date"].tolist() == ["2026-05-04", "2026-05-05"]

    def test_leaves_non_date_columns_unchanged(self):
        from src.export_table import _stringify_dates

        df = pd.DataFrame({
            "total_articles": [10, 12],
            "idx_war_threat": [1.5, 2.3],
        })
        result = _stringify_dates(df)

        assert result["total_articles"].tolist() == [10, 12]
        assert result["idx_war_threat"].tolist() == [1.5, 2.3]

    def test_handles_multiple_date_columns_independently(self):
        """The original bug: only key_column was stringified, not ALL date columns."""
        from src.export_table import _stringify_dates

        df = pd.DataFrame({
            "week_start": pd.to_datetime(["2026-05-04"]),
            "first_day_in_week": pd.to_datetime(["2026-05-04"]),
            "last_day_in_week": pd.to_datetime(["2026-05-10"]),
            "total_articles": [27],
        })
        result = _stringify_dates(df)

        assert all(isinstance(result[col].iloc[0], str)
                   for col in ["week_start", "first_day_in_week", "last_day_in_week"])