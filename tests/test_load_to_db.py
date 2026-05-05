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
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from src.load_to_db import process_single_file


#  Helpers

def write_json(tmp_path: Path, filename: str, data: list) -> Path:
    path = tmp_path / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def make_mock_con(existing_links: list = None):
    """
    Builds a MagicMock connection where:
      - execute("SELECT ...").fetchdf() returns a DataFrame of existing links
      - execute("INSERT ...") succeeds silently

    This matches the two-call pattern added by the dedup guard:
      call 1: SELECT link FROM raw_news WHERE published_date = ?
      call 2: INSERT INTO raw_news BY NAME SELECT * FROM df_new
    """
    mock_con = MagicMock()

    # Return an empty DataFrame by default (no existing rows = first load)
    existing_df = pd.DataFrame({"link": existing_links or []})
    mock_con.execute.return_value.fetchdf.return_value = existing_df

    return mock_con


#  Tests

class TestProcessSingleFile:

    def test_inserts_rows_for_valid_file(self, tmp_path, sample_articles):
        """Happy path: valid file triggers SELECT dedup check then INSERT."""
        json_path = write_json(tmp_path, "news_2025-01-12.json", sample_articles)
        mock_con = make_mock_con()

        process_single_file(json_path, mock_con)

        # Two calls: SELECT (dedup) + INSERT
        assert mock_con.execute.call_count == 2
        last_sql = mock_con.execute.call_args_list[-1][0][0]
        assert "INSERT" in last_sql

    def test_date_extracted_from_filename(self, tmp_path, sample_articles):
        """published_date must be parsed from the filename, not from article data."""
        json_path = write_json(tmp_path, "news_2025-06-15.json", sample_articles)
        mock_con = make_mock_con()

        process_single_file(json_path, mock_con)

        # SELECT call must include the correct date from filename
        select_call_args = mock_con.execute.call_args_list[0][0]
        from datetime import date
        assert date(2025, 6, 15) in select_call_args[1]

    def test_skips_nonexistent_file(self, tmp_path):
        """Missing file should not raise — just print and return."""
        missing = tmp_path / "ghost_2025-01-01.json"
        mock_con = make_mock_con()

        process_single_file(missing, mock_con)

        mock_con.execute.assert_not_called()

    def test_skips_empty_json_file(self, tmp_path):
        """Empty JSON array should not trigger any DB calls."""
        json_path = write_json(tmp_path, "news_2025-01-12.json", [])
        mock_con = make_mock_con()

        process_single_file(json_path, mock_con)

        mock_con.execute.assert_not_called()

    def test_fallback_date_when_no_date_in_filename(self, tmp_path, sample_articles):
        """If filename has no YYYY-MM-DD pattern, fall back to yesterday's date."""
        json_path = write_json(tmp_path, "news_latest.json", sample_articles)
        mock_con = make_mock_con()

        process_single_file(json_path, mock_con)

        # Should still reach INSERT — fallback date doesn't prevent loading
        assert mock_con.execute.call_count == 2

    def test_skips_insert_when_all_links_already_exist(self, tmp_path, sample_articles):
        """Dedup guard: if all links already in DB, INSERT must not be called."""
        json_path = write_json(tmp_path, "news_2025-01-12.json", sample_articles)
        existing_links = [a["link"] for a in sample_articles]
        mock_con = make_mock_con(existing_links=existing_links)

        process_single_file(json_path, mock_con)

        # Only the SELECT should be called — no INSERT
        assert mock_con.execute.call_count == 1
        only_sql = mock_con.execute.call_args_list[0][0][0]
        assert "SELECT" in only_sql

    def test_inserts_only_new_links_when_partial_overlap(self, tmp_path, sample_articles):
        """Dedup guard: only articles with new links get inserted."""
        json_path = write_json(tmp_path, "news_2025-01-12.json", sample_articles)
        # Mark first article as already existing
        existing_links = [sample_articles[0]["link"]]
        mock_con = make_mock_con(existing_links=existing_links)

        process_single_file(json_path, mock_con)

        # Both SELECT and INSERT are called
        assert mock_con.execute.call_count == 2

    def test_published_date_is_date_type(self, tmp_path, sample_articles):
        """published_date passed to SELECT must be a date object, not a string."""
        json_path = write_json(tmp_path, "news_2025-03-20.json", sample_articles)
        mock_con = make_mock_con()

        process_single_file(json_path, mock_con)

        from datetime import date
        select_args = mock_con.execute.call_args_list[0][0]
        assert select_args[1] == [date(2025, 3, 20)]