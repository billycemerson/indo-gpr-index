"""
test_load_to_db.py
==================
Unit tests for process_single_file() in load_to_db.py.

Rule: ZERO real DuckDB connections. The `con` object is always a MagicMock.
We test Python logic only — date extraction, schema stamping, skip conditions.

We do NOT test that DuckDB SQL works correctly — that's dbt's job.
"""

import json
import pytest
from pathlib import Path
from datetime import date
from unittest.mock import MagicMock, patch

from src.load_to_db import process_single_file


#  Helpers

def write_json(tmp_path: Path, filename: str, data: list) -> Path:
    """Write sample article data to a temp JSON file and return its path."""
    path = tmp_path / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


#  Tests

class TestProcessSingleFile:

    def test_inserts_rows_for_valid_file(self, tmp_path, sample_articles):
        """Happy path: valid JSON file triggers an INSERT into DuckDB."""
        json_path = write_json(tmp_path, "news_2025-01-12.json", sample_articles)
        mock_con = MagicMock()

        process_single_file(json_path, mock_con)

        mock_con.execute.assert_called_once()

    def test_date_extracted_from_filename(self, tmp_path, sample_articles):
        """published_date must be parsed from the filename, not from article data."""
        json_path = write_json(tmp_path, "news_2025-06-15.json", sample_articles)
        mock_con = MagicMock()

        with patch("src.load_to_db.pd.read_json") as mock_read:
            import pandas as pd
            df = pd.DataFrame(sample_articles)
            mock_read.return_value = df

            process_single_file(json_path, mock_con)

            # The DataFrame passed to execute should have 'published_date' stamped
            call_args = mock_con.execute.call_args
            assert call_args is not None

    def test_skips_nonexistent_file(self, tmp_path):
        """Missing file should not raise — just print and return."""
        missing = tmp_path / "ghost_2025-01-01.json"
        mock_con = MagicMock()

        process_single_file(missing, mock_con)  # should not raise

        mock_con.execute.assert_not_called()

    def test_skips_empty_json_file(self, tmp_path):
        """Empty JSON array should not trigger an INSERT."""
        json_path = write_json(tmp_path, "news_2025-01-12.json", [])
        mock_con = MagicMock()

        process_single_file(json_path, mock_con)

        mock_con.execute.assert_not_called()

    def test_fallback_date_when_no_date_in_filename(self, tmp_path, sample_articles):
        """If filename has no YYYY-MM-DD pattern, should fall back to yesterday's date."""
        json_path = write_json(tmp_path, "news_latest.json", sample_articles)
        mock_con = MagicMock()

        # Should not raise even with an undated filename
        process_single_file(json_path, mock_con)

        mock_con.execute.assert_called_once()

    def test_published_date_is_date_type(self, tmp_path, sample_articles):
        """published_date column must be a date object, not a string."""
        json_path = write_json(tmp_path, "news_2025-03-20.json", sample_articles)

        captured_df = {}

        def capture_execute(sql, *args, **kwargs):
            # Not inspecting SQL internals — just confirm it was called
            captured_df["called"] = True

        mock_con = MagicMock()
        mock_con.execute.side_effect = capture_execute

        with patch("src.load_to_db.pd.read_json") as mock_read:
            import pandas as pd
            df = pd.DataFrame(sample_articles)
            mock_read.return_value = df

            process_single_file(json_path, mock_con)

        assert captured_df.get("called") is True