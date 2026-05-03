"""
test_parsers.py
===============
Unit tests for AntaraParser and KompasParser.

Rule: ZERO network calls. Every test feeds mock HTML directly into the
private parse methods. requests.get is never called here.

Test groups:
  - _parse_list_page   : HTML → list[dict] (Antara)
  - _classify_date     : date label → age string (Antara)
  - _parse_index_page  : HTML → list[dict] (Kompas)
  - _stamp             : inherited from BaseParser, tested via fetch_news mock
"""

import pytest
from unittest.mock import patch, MagicMock

from src.scraper.parsers.antara import AntaraParser
from src.scraper.parsers.kompas import KompasParser


#  Shared parser instances

@pytest.fixture
def antara():
    return AntaraParser()

@pytest.fixture
def kompas():
    return KompasParser()


#  AntaraParser

class TestAntaraParseListPage:
    """_parse_list_page: HTML string → list of raw article dicts."""

    def test_extracts_title_link_date(self, antara, antara_valid_html):
        results = antara._parse_list_page(antara_valid_html)

        assert len(results) == 1
        assert results[0]["title"] == "Berita Politik Penting"
        assert results[0]["link"] == "https://www.antaranews.com/news/123/berita-politik"
        assert results[0]["date_text"] == "9 menit lalu"

    def test_returns_empty_on_no_rows(self, antara, antara_empty_html):
        results = antara._parse_list_page(antara_empty_html)
        assert results == []

    def test_skips_row_without_title_tag(self, antara):
        html = """
        <div class="row">
            <span class="text-secondary">kemarin</span>
        </div>
        """
        results = antara._parse_list_page(html)
        assert results == []

    def test_date_text_empty_string_when_missing(self, antara):
        html = """
        <div class="row">
            <h2 class="post_title">
                <a href="https://antaranews.com/news/99/no-date">Tanpa Tanggal</a>
            </h2>
        </div>
        """
        results = antara._parse_list_page(html)
        assert results[0]["date_text"] == ""

    def test_parses_multiple_rows(self, antara, antara_multi_html):
        results = antara._parse_list_page(antara_multi_html)
        assert len(results) == 3


class TestAntaraClassifyDate:
    """_classify_date: maps Antara's relative labels to age buckets."""

    @pytest.mark.parametrize("label,expected", [
        ("9 menit lalu",   "today"),
        ("2 jam lalu",     "today"),
        ("30 detik lalu",  "today"),
        ("kemarin",        "yesterday"),
        ("12 Januari 2025","older"),
        ("",               "older"),      # empty → treat as older
    ])
    def test_classification(self, label, expected):
        # _classify_date is a static method — callable without instance
        assert AntaraParser._classify_date(label) == expected


class TestAntaraFetchNews:
    """
    fetch_news: full integration of _scrape_category + _stamp.
    Network call (requests.get) is mocked — no real HTTP.
    """

    def test_source_field_is_stamped(self, antara, antara_valid_html):
        mock_response = MagicMock()
        mock_response.text = antara_valid_html
        mock_response.raise_for_status = MagicMock()

        with patch("src.scraper.parsers.antara.requests.get", return_value=mock_response):
            results = antara.fetch_news("2025-01-01")

        assert all(a["source"] == "antara" for a in results)

    def test_category_field_is_set(self, antara, antara_valid_html):
        mock_response = MagicMock()
        mock_response.text = antara_valid_html
        mock_response.raise_for_status = MagicMock()

        with patch("src.scraper.parsers.antara.requests.get", return_value=mock_response):
            results = antara.fetch_news("2025-01-01")

        # Every article must have a category set to one of the configured values
        valid_categories = set(AntaraParser.CATEGORIES)
        assert all(a["category"] in valid_categories for a in results)

    def test_returns_empty_list_on_empty_pages(self, antara, antara_empty_html):
        mock_response = MagicMock()
        mock_response.text = antara_empty_html
        mock_response.raise_for_status = MagicMock()

        with patch("src.scraper.parsers.antara.requests.get", return_value=mock_response):
            results = antara.fetch_news("2025-01-01")

        assert results == []

    def test_handles_request_exception_gracefully(self, antara):
        """A network error on one category should not crash the whole run."""
        import requests as req
        with patch(
            "src.scraper.parsers.antara.requests.get",
            side_effect=req.exceptions.ConnectionError("timeout")
        ):
            # Should not raise — errors are caught inside fetch_news
            results = antara.fetch_news("2025-01-01")

        assert isinstance(results, list)


#  KompasParser

class TestKompasParseIndexPage:
    """_parse_index_page: HTML string → list of raw article dicts."""

    def test_extracts_title_link_date(self, kompas, kompas_valid_html):
        results = kompas._parse_index_page(kompas_valid_html)

        assert len(results) == 1
        assert results[0]["title"] == "Berita Nasional Kompas"
        assert results[0]["link"] == "https://nasional.kompas.com/read/2025/01/01/berita-nasional"
        assert results[0]["date_text"] == "Rabu, 1 Januari 2025"
        assert results[0]["category"] == "nasional"

    def test_returns_empty_on_no_wrappers(self, kompas, kompas_empty_html):
        results = kompas._parse_index_page(kompas_empty_html)
        assert results == []

    def test_skips_article_without_title(self, kompas):
        html = """
        <a href="https://kompas.com/read/no-title">
            <div class="articleItem-wrap">
                <div class="articlePost-date">1 Januari 2025</div>
            </div>
        </a>
        """
        results = kompas._parse_index_page(html)
        assert results == []

    def test_skips_article_without_link(self, kompas):
        html = """
        <div class="articleItem-wrap">
            <h2 class="articleTitle">Judul Tanpa Link</h2>
        </div>
        """
        results = kompas._parse_index_page(html)
        assert results == []

    def test_date_fallback_when_missing(self, kompas):
        html = """
        <a href="https://kompas.com/read/no-date">
            <div class="articleItem-wrap">
                <h2 class="articleTitle">Tanpa Tanggal</h2>
            </div>
        </a>
        """
        results = kompas._parse_index_page(html)
        assert results[0]["date_text"] == "Date not available"


class TestKompasSourceName:
    def test_source_name(self, kompas):
        assert kompas.source_name == "kompas"


class TestKompasFetchNews:
    """fetch_news: pagination + _stamp. Network mocked."""

    def test_stops_pagination_on_empty_page(self, kompas, kompas_valid_html, kompas_empty_html):
        """Should stop looping when a page returns no articles."""
        responses = [
            MagicMock(text=kompas_valid_html, raise_for_status=MagicMock()),
            MagicMock(text=kompas_empty_html, raise_for_status=MagicMock()),
        ]

        with patch("src.scraper.parsers.kompas.requests.get", side_effect=responses):
            with patch("src.scraper.parsers.kompas.time.sleep"):  # skip delay in tests
                results = kompas.fetch_news("2025-01-01")

        assert len(results) == 1

    def test_source_field_is_stamped(self, kompas, kompas_valid_html, kompas_empty_html):
        responses = [
            MagicMock(text=kompas_valid_html, raise_for_status=MagicMock()),
            MagicMock(text=kompas_empty_html, raise_for_status=MagicMock()),
        ]

        with patch("src.scraper.parsers.kompas.requests.get", side_effect=responses):
            with patch("src.scraper.parsers.kompas.time.sleep"):
                results = kompas.fetch_news("2025-01-01")

        assert all(a["source"] == "kompas" for a in results)