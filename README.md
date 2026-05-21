# Indonesia Geopolitical Risk (GPR) Index

An automated data pipeline that scrapes Indonesian political news daily, calculates a Geopolitical Risk Index, and exports results to Google Sheets.

---

## Pipeline Overview

```
Scrape (3 sources)
    ↓
Raw JSON → DuckDB (raw_news)
    ↓
dbt staging (stg_scraped_news) — dedup + clean
    ↓
dbt mart (mart_gpr_daily) — keyword flagging + index calculation
    ↓
Export → Google Sheets
```

**Runs daily at 08:00 WIB via GitHub Actions.**

---

## Sources

| Source | Type | Categories | Method |
|--------|------|------------|--------|
| Antara | State agency | politik, ekonomi, hukum, dunia | requests |
| Detik | Mainstream | internasional, bbc | requests |
| Kompas | Mainstream | nasional, global | requests |
| Tempo | Independent | politik, hukum, ekonomi, internasional | requests |
| Tribunnews | Mainstream | nasional, internasional | requests |

---

## GPR Index Methodology

Each article title is matched against keyword dictionaries across 5 dimensions:

| Component | Measures |
|-----------|----------|
| `idx_war_threat` | Conflict rhetoric, sanctions, border disputes |
| `idx_peace_threat` | Failed diplomacy, ceasefire breakdown |
| `idx_military_buildup` | Arms, troop movements, defence procurement |
| `idx_war_act` | Active clashes, strikes, casualties |
| `idx_terror_act` | Terrorism, extremism, counter-terror |

Index formula: `(keyword_match_count / total_articles) × 100`

Composite:
- `gpr_threats_index` = war_threat + peace_threat + military_buildup
- `gpr_acts_index` = war_act + terror_act
- `total_gpr_index` = all five components

---

## Project Structure

```
.
├── .github/workflows/
│   └── pipeline.yml          ← CI/CD daily schedule
├── config/
│   └── settings.py           ← APP_ENV-aware config
├── dbt_project/
│   ├── models/
│   │   ├── staging/          ← stg_scraped_news (dedup + clean)
│   │   └── marts/            ← mart_gpr_daily (index calculation)
│   └── macros/
│       └── match_keywords.sql
├── scripts/
│   └── try_parser.py         ← manual parser testing tool
├── src/
│   ├── scraper/
│   │   ├── base_parser.py    ← ABC blueprint
│   │   ├── main_scraper.py   ← orchestrator
│   │   └── parsers/
│   │       ├── antara.py
│   │       ├── kompas.py
│   │       └── tempo.py
│   ├── database/
│   │   └── connection.py
│   ├── exports/
│   │   └── gsheet_client.py
│   ├── load_to_db.py
│   └── export_table.py
└── tests/
    ├── conftest.py
    ├── test_parsers.py
    ├── test_load_to_db.py
    └── test_export.py
```

---

## Local Setup

```bash
# 1. Clone and install
git clone https://github.com/billycemerson/indo-gpr-index.git
cd indo-gpr-index
uv sync

# 2. Add credentials
cp config/credentials/gsheet_key.json.example config/credentials/gsheet_key.json
# paste your Google service account key

# 3. Set environment
echo "APP_ENV=dev" > config/.env
```

---

## Running Locally

```bash
# Test all parsers individually before running the full pipeline
APP_ENV=dev uv run python scripts/try_parser.py

# Run full pipeline
APP_ENV=dev uv run python run_pipeline.py

# Or step by step
uv run pytest                                          # tests
uv run python src/scraper/main_scraper.py              # scrape
uv run python src/load_to_db.py                        # load
cd dbt_project && uv run dbt run --profiles-dir .      # transform
uv run python src/export_table.py                      # export
```

---

## Adding a New Source

See [CONTRIBUTTING.md](./CONTRIBUTTING.md) for the full guide.

Short version: create `src/scraper/parsers/<media>.py` inheriting `BaseParser`, register in `parsers/__init__.py` and `build_parsers()`, add tests to `tests/test_parsers.py`.

---

## Environment Variables

| Variable | Values | Default |
|----------|--------|---------|
| `APP_ENV` | `dev`, `prod` | `prod` |

Data paths:
- `dev` → `data/dev/`
- `prod` → `data/prod/`

---

## CI/CD

GitHub Actions workflow at `.github/workflows/pipeline.yml`.

Required secret: `GSHEET_KEY_JSON` — full contents of `gsheet_key.json`.

See [CI_SETUP.md](.github/CI_SETUP.md) for setup instructions.