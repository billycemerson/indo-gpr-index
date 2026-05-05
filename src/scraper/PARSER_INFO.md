# Scraper Architecture

## Directory Structure

```
src/
├── scraper/
│   ├── base_parser.py          ← The Blueprint (Abstract Base Class)
│   ├── main_scraper.py         ← Orchestrator (dumb runner)
│   └── parsers/
│       ├── __init__.py         ← Parser registry
│       ├── antara.py           ← AntaraParser
│       ├── kompas.py           ← KompasParser
│       └── detik.py            ← DetikParser (template)
├── database/
│   └── connection.py
├── exports/
│   └── gsheet_client.py
├── load_to_db.py
└── export_table.py
```

---

## How to Add a New Media Source

**3 steps, no other files need to change:**

### 1. Create `src/scraper/parsers/<media>.py`

```python
from src.scraper.base_parser import BaseParser

class MediaNameParser(BaseParser):

    @property
    def source_name(self) -> str:
        return "medianame"          # lowercase, used as the 'source' field

    def fetch_news(self, target_date: str) -> list[dict]:
        results = []

        # --- your scraping logic here ---
        # each dict must have: title, link, category, date_text

        return self._stamp(results)  # auto-adds 'source' field
```

### 2. Register in `src/scraper/parsers/__init__.py`

```python
from src.scraper.parsers.medianame import MediaNameParser
__all__ = [..., "MediaNameParser"]
```

### 3. Add to `build_parsers()` in `main_scraper.py`

```python
def build_parsers():
    return [
        AntaraParser(...),
        KompasParser(),
        MediaNameParser(),   # ← add here
    ]
```

That's it. The orchestrator loop treats all parsers identically.

---

## Design Principles

| Principle | Applied Where |
|-----------|--------------|
| **ABC / Polymorphism** | `BaseParser` enforces `source_name` + `fetch_news()` on every parser |
| **Encapsulation** | Category loops, pagination, date logic live *inside* each parser |
| **Open/Closed** | Add sources by extension (new file), not modification |
| **Single Responsibility** | `main_scraper.py` only orchestrates; parsers only scrape |

---

## Guaranteed Article Shape

Every parser's `fetch_news()` returns a list of dicts with this shape:

```python
{
    "title":     str,
    "link":      str,   # used for deduplication
    "category":  str,
    "date_text": str,
    "source":    str,   # auto-stamped by BaseParser._stamp()
}
```