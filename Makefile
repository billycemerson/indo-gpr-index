# Define phony targets for pipeline step
.PHONY test scrape load transform export run_all

# Run all pytest tests
test:
	uv run pytest

# Execute the scraper
scrape:
	uv run python src/scraper/main_scraper.py

# Load scraped JSON into DuckDB
load:
	uv run python src/load_to_db.py

# Run dbt transformations
transform:
	cd dbt_project && uv run dbt run --profiles-dir .

# Export the gold layer to Google Sheets
export:
	uv run python src/export_table.py

# Run all step as pipeline
run_all: test scrape load transform export