# Indonesia Geopolitical Risk (GPR) Index - dbt Transformations

This dbt project handles the transformation, deduplication, and index calculation for the Indonesia Geopolitical Risk (GPR) Index. It operates on a local DuckDB database and follows the Medallion Architecture (Bronze -> Silver -> Gold).

## Architecture & Models

### 1. Source (Bronze Layer)
* **`raw_news`**: The raw data ingested daily from the Python web scraper. It contains JSON data with article titles, links, categories, and raw date text.

### 2. Staging (Silver Layer)
* **`stg_antara_news`**: A virtual view that cleans the raw data. 
  * Converts titles to lowercase for easier keyword matching.
  * Normalizes the publication date.
  * **Deduplication:** Uses window functions (`ROW_NUMBER()`) to ensure articles cross-posted in multiple categories (e.g., `/nasional` and `/politik`) are only counted once based on their URL.

### 3. Marts (Gold Layer)
* **`mart_gpr_daily`**: The final output table materialized **incrementally**. 
  * Uses the Caldara & Iacoviello methodology, adapted for Indonesian vocabulary.
  * Flags articles into sub-categories (War Threats, Peace Threats, Military Buildups, War Acts, Terror Acts).
  * Calculates the daily percentage share of these risk-related articles against the total volume of news for that day.
  * *Note: Runs incrementally using `published_date` as the unique key to save memory and compute time.*

## Macros

* **`match_keywords`**: A custom Jinja macro that simplifies complex SQL `CASE WHEN` statements. Instead of writing dozens of `OR column ILIKE '%keyword%'` lines, this macro accepts a list of Indonesian root words (e.g., `['konflik', 'perang', 'ancaman']`) and dynamically compiles the SQL logic for substring matching.

## Data Quality & Tests

To ensure the statistical integrity of the GPR index, this project utilizes `schema.yml` tests combined with `dbt_utils`:
* **Unique & Not Null**: Ensures `published_date` never has duplicates or missing values.
* **Division by Zero Protection**: Tests that `total_articles` is at least 1 using `dbt_utils.accepted_range`.
* **Logical Index Bounds**: Tests that the final calculated `total_gpr_index` is never a negative number.

---

## How to Run

**CRITICAL:** This project is configured to use a local `profiles.yml` file located in the project root to manage memory limits and database paths safely. **Do not use the global `~/.dbt/profiles.yml`.** You must always pass the `--profiles-dir .` flag.

### 1. Install Dependencies
Because this project uses the `dbt_utils` package for testing, you must install dependencies first:
```bash
uv run dbt deps
```

### 2. Verify Connection
Ensure dbt can read the local `profiles.yml` and connect to your DuckDB database:
```bash
uv run dbt debug --profiles-dir .
```

### 3. Run the Pipeline
To run the daily incremental load (processes only new data):
```bash
uv run dbt run --profiles-dir .
```

To run a full refresh (drops the table and recalculates all historical data from scratch):
```bash
uv run dbt run --full-refresh --profiles-dir .
```

### 4. Run Data Tests
To execute the QA checks defined in `schema.yml`:
```bash
uv run dbt test --profiles-dir .
```