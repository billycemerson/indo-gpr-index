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
    time.sleep is patched at class level — no real delays.
    """

    @pytest.fixture(autouse=True)
    def no_sleep(self):
        """Eliminates REQUEST_DELAY waits across all tests in this class."""
        with patch("src.scraper.parsers.antara.time.sleep"):
            yield

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
    """fetch_news: pagination + _stamp. Network mocked. time.sleep patched."""

    @pytest.fixture(autouse=True)
    def no_sleep(self):
        """Eliminates REQUEST_DELAY waits across all tests in this class."""
        with patch("src.scraper.parsers.kompas.time.sleep"):
            yield

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


#  TempoParser

# Tempo uses Playwright instead of requests.
# Mock strategy: patch _render_page (the Playwright layer) directly.
# This keeps tests fast and dependency-free — no browser needed in CI.

@pytest.fixture
def tempo():
    from src.scraper.parsers.tempo import TempoParser
    return TempoParser()


class TestTempoParseIndexPage:
    """_parse_index_page: rendered HTML string → list of article dicts."""

    def test_extracts_title_link_category(self, tempo, tempo_valid_html):
        results = tempo._parse_index_page(tempo_valid_html, "politik", "2026-05-01")

        assert len(results) == 1
        assert results[0]["title"] == "Unhas Ungkap Biaya Bangun Dapur MBG Mencapai Rp 2 Miliar"
        assert results[0]["link"] == "https://www.tempo.co/politik/unhas-ungkap-biaya-bangun-dapur-mbg-2132971"
        assert results[0]["category"] == "politik"
        assert results[0]["date_text"] == "2026-05-01"

    def test_prefers_data_mrf_link_over_href(self, tempo, tempo_valid_html):
        """data-mrf-link is the full absolute URL — should be preferred over relative href."""
        results = tempo._parse_index_page(tempo_valid_html, "politik", "2026-05-01")
        assert results[0]["link"].startswith("https://www.tempo.co")

    def test_falls_back_to_href_when_no_mrf_link(self, tempo):
        html = """
        <aside class="flex flex-row">
            <figure class="contents">
                <figcaption>
                    <p><a href="/politik/artikel-tanpa-mrf">Artikel Tanpa MRF Link</a></p>
                </figcaption>
            </figure>
        </aside>
        """
        results = tempo._parse_index_page(html, "politik", "2026-05-01")
        assert results[0]["link"] == "https://www.tempo.co/politik/artikel-tanpa-mrf"

    def test_returns_empty_on_no_asides(self, tempo, tempo_empty_html):
        results = tempo._parse_index_page(tempo_empty_html, "politik", "2026-05-01")
        assert results == []

    def test_skips_aside_without_figcaption(self, tempo):
        html = """<aside class="flex flex-row"><figure></figure></aside>"""
        results = tempo._parse_index_page(html, "politik", "2026-05-01")
        assert results == []

    def test_skips_aside_without_link(self, tempo):
        html = """
        <aside class="flex flex-row">
            <figure class="contents">
                <figcaption><p>Teks tanpa link</p></figcaption>
            </figure>
        </aside>
        """
        results = tempo._parse_index_page(html, "politik", "2026-05-01")
        assert results == []

    def test_date_text_is_injected_from_target_date(self, tempo, tempo_valid_html):
        """Tempo has no date in HTML — date_text must equal the passed target_date."""
        results = tempo._parse_index_page(tempo_valid_html, "politik", "2026-05-01")
        assert results[0]["date_text"] == "2026-05-01"

    def test_parses_multiple_articles(self, tempo, tempo_multi_html):
        results = tempo._parse_index_page(tempo_multi_html, "politik", "2026-05-01")
        assert len(results) == 2


class TestTempoGetTotalPages:
    """_get_total_pages: reads max page count from pagination nav."""

    def test_returns_max_page_from_nav(self, tempo, tempo_pagination_html):
        assert tempo._get_total_pages(tempo_pagination_html) == 2

    def test_returns_1_when_no_nav(self, tempo, tempo_valid_html):
        """Single-page result has no nav — should default to 1."""
        assert tempo._get_total_pages(tempo_valid_html) == 1

    def test_returns_1_on_empty_html(self, tempo, tempo_empty_html):
        assert tempo._get_total_pages(tempo_empty_html) == 1


class TestTempoSourceName:
    def test_source_name(self, tempo):
        assert tempo.source_name == "tempo"


class TestTempoFetchNews:
    """
    fetch_news: full flow with Playwright fully mocked.

    Root cause of slow tests: patch.object(tempo, "_render_page") mocks the
    method but sync_playwright() still launches a real Chromium process before
    _render_page is ever called. Fix: mock sync_playwright itself so no browser
    is started at all.

    Pattern used in every test:
        with patch("src.scraper.parsers.tempo.sync_playwright") as mock_pw:
            mock_pw.return_value.__enter__.return_value = mock_playwright_instance
            mock_playwright_instance.chromium.launch.return_value.new_context.return_value = mock_ctx
            patch.object(tempo, "_render_page", ...)
    """

    @pytest.fixture
    def mock_pw(self):
        """
        Shared fixture: fully mocked sync_playwright context manager.
        No Chromium process is launched. Tests finish in milliseconds.
        """
        with patch("src.scraper.parsers.tempo.sync_playwright") as mock_sync_pw:
            mock_instance   = MagicMock()
            mock_browser    = MagicMock()
            mock_ctx        = MagicMock()

            mock_sync_pw.return_value.__enter__.return_value = mock_instance
            mock_instance.chromium.launch.return_value      = mock_browser
            mock_browser.new_context.return_value           = mock_ctx

            yield mock_sync_pw

    def test_source_field_is_stamped(self, tempo, mock_pw, tempo_valid_html):
        with patch.object(tempo, "_render_page", return_value=tempo_valid_html):
            results = tempo.fetch_news("2026-05-01")

        assert all(a["source"] == "tempo" for a in results)

    def test_all_categories_are_scraped(self, tempo, mock_pw, tempo_valid_html):
        """fetch_news must iterate all CATEGORIES — each returns at least 1 article."""
        with patch.object(tempo, "_render_page", return_value=tempo_valid_html):
            results = tempo.fetch_news("2026-05-01")

        assert {a["category"] for a in results} == set(tempo.CATEGORIES)

    def test_pagination_respects_total_pages(self, tempo, mock_pw, tempo_pagination_html, tempo_valid_html):
        """page 1 has 2-page nav → _render_page called twice per category."""
        responses = [tempo_pagination_html, tempo_valid_html] * len(tempo.CATEGORIES)

        with patch.object(tempo, "_render_page", side_effect=responses):
            with patch("src.scraper.parsers.tempo.time.sleep"):
                results = tempo.fetch_news("2026-05-01")

        assert len(results) >= len(tempo.CATEGORIES) * 2

    def test_returns_empty_list_when_render_fails(self, tempo, mock_pw):
        """_render_page returning None must not crash — return empty list."""
        with patch.object(tempo, "_render_page", return_value=None):
            results = tempo.fetch_news("2026-05-01")

        assert results == []

    def test_category_error_does_not_stop_other_categories(self, tempo, mock_pw, tempo_valid_html):
        """Exception in one category must not prevent remaining categories."""
        call_count = 0

        def side_effect(ctx, url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated network error")
            return tempo_valid_html

        with patch.object(tempo, "_render_page", side_effect=side_effect):
            results = tempo.fetch_news("2026-05-01")

        assert len(results) > 0