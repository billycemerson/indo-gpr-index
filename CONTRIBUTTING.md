# Contributing Guide

## Adding a New Parser

### 1. Create the parser file

```
src/scraper/parsers/<media>.py
```

Rules:
- Filename: `snake_case`, media name only — `tribunnews.py`, not `tribunnews_scraper_parser.py`
- Class: `PascalCase` + `Parser` suffix — `TribunnewsParser`
- Must inherit `BaseParser` and implement both abstract members

```python
from src.scraper.base_parser import BaseParser

class TribunnewsParser(BaseParser):

    @property
    def source_name(self) -> str:
        return "tribunnews"          # lowercase, no spaces

    def fetch_news(self, target_date: str) -> list[dict]:
        results = []
        # ... scraping logic ...
        return self._stamp(results)  # always call _stamp() — never set 'source' manually
```

### 2. Guaranteed article shape

Every dict in the returned list **must** contain exactly these keys:

| Key | Type | Notes |
|-----|------|-------|
| `title` | `str` | Clean text, no trailing whitespace |
| `link` | `str` | Full absolute URL |
| `category` | `str` | Lowercase, e.g. `"nasional"`, `"politik"` |
| `date_text` | `str` | Raw date string from HTML, or `target_date` if HTML has none |
| `source` | `str` | Auto-set by `_stamp()` — do not set manually |

### 3. Register in two places

```python
# src/scraper/parsers/__init__.py
from src.scraper.parsers.tribunnews import TribunnewsParser
__all__ = [..., "TribunnewsParser"]

# src/scraper/main_scraper.py → build_parsers()
def build_parsers():
    return [
        ...
        TribunnewsParser(),
    ]
```

### 4. Validate locally before registering

```bash
APP_ENV=dev python scripts/try_parser.py
```

Parser is ready to register when:
- [ ] `len(results) > 0`
- [ ] All 5 fields present in every article (no WARNING lines printed)
- [ ] `source` field matches `source_name`
- [ ] All `link` values are full absolute URLs
- [ ] No crash when the target date has no articles (e.g. far future date)

---

## Adding Tests for a New Parser

Every parser **must** have tests before merging. No exceptions.

### File location

```
tests/test_parsers.py   ← append to this file, do not create a new one
tests/conftest.py       ← add HTML fixtures here
```

### Rule: zero real I/O in tests

| Parser type | Mock target |
|-------------|-------------|
| `requests`-based (Antara, Kompas, Tribunnews) | `patch("src.scraper.parsers.<media>.requests.get")` |
| Playwright-based (Tempo) | `patch("src.scraper.parsers.<media>.sync_playwright")` |

Never let a real HTTP request or browser process run in tests. If a test takes more than 1 second, something is not mocked.

### Required test groups per parser

#### 1. `Test<Media>ParsePage` — pure HTML parsing, no mocks needed

Test the private `_parse_*` method directly with mock HTML strings.

```python
class TestTribunnewsParseIndexPage:
    def test_extracts_title_link_date(self, tribunnews, tribunnews_valid_html): ...
    def test_returns_empty_on_no_items(self, tribunnews, tribunnews_empty_html): ...
    def test_skips_item_without_title(self, tribunnews): ...
    def test_skips_item_without_link(self, tribunnews): ...
```

#### 2. `Test<Media>SourceName` — one line, catches copy-paste bugs

```python
class TestTribunnewsSourceName:
    def test_source_name(self, tribunnews):
        assert tribunnews.source_name == "tribunnews"
```

#### 3. `Test<Media>FetchNews` — full flow, I/O fully mocked

```python
class TestTribunnewsFetchNews:

    @pytest.fixture(autouse=True)       # mandatory — eliminates time.sleep delays
    def no_sleep(self):
        with patch("src.scraper.parsers.tribunnews.time.sleep"):
            yield

    def test_source_field_is_stamped(self, ...): ...
    def test_returns_empty_on_no_articles(self, ...): ...
    def test_error_does_not_crash_run(self, ...): ...   # network exception handled gracefully
```

### HTML fixtures go in `conftest.py`

```python
# tests/conftest.py
@pytest.fixture
def tribunnews_valid_html():
    """Real HTML copied from the target page — single valid article."""
    return """<li class="ptb15">...</li>"""

@pytest.fixture
def tribunnews_empty_html():
    """HTML with no articles — simulates empty page or end of pagination."""
    return "<div>Tidak ada berita</div>"
```

Rule: fixtures use **real HTML copied from the live site**, not invented structure.
This ensures tests break when the site changes its HTML — which is the whole point.

### Performance rule

Patch `time.sleep` at class level using `autouse=True`. This is not optional:

```python
# WRONG — sleep runs, test takes seconds
def test_something(self, parser):
    with patch("...requests.get", ...):
        parser.fetch_news("2025-01-01")   # sleeps between pages

# RIGHT — autouse fixture kills all sleeps in the class
@pytest.fixture(autouse=True)
def no_sleep(self):
    with patch("src.scraper.parsers.<media>.time.sleep"):
        yield
```

Target: `uv run pytest` completes in under 60 seconds total.

---

## Checklist before opening a PR

- [ ] Parser file at `src/scraper/parsers/<media>.py`
- [ ] Registered in `parsers/__init__.py` and `build_parsers()`
- [ ] `try_parser.py` passes all 5 validation checks in `development` env
- [ ] HTML fixtures added to `conftest.py`
- [ ] All 3 test groups added to `test_parsers.py`
- [ ] `uv run pytest` passes with no failures
- [ ] `uv run pytest` completes in under 60 seconds