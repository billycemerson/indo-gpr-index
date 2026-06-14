import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config.settings import Config
from prefect import flow, task, get_run_logger

def run_subprocess(cmd: list[str], cwd: str = None, env: dict = None):
    """
    Executes a shell command as a subprocess, streams stdout/stderr
    line-by-line to the Prefect logger in real-time, and raises
    an exception if the command exits with a non-zero code.
    """
    logger = get_run_logger()
    logger.info(f"Executing subprocess: {' '.join(cmd)} (cwd: {cwd or '.'})")
    
    # Inherit current env and update if custom variables are provided
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
        
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=cwd,
        env=full_env
    )
    
    # Stream stdout/stderr in real-time
    for line in iter(process.stdout.readline, ""):
        stripped_line = line.strip()
        if stripped_line:
            logger.info(stripped_line)
            
    process.stdout.close()
    return_code = process.wait()
    
    if return_code != 0:
        raise RuntimeError(f"Command failed with exit code {return_code}: {' '.join(cmd)}")


@task(
    name="Scrape News",
    retries=2,
    retry_delay_seconds=60,
    description="Scrapes news articles using Playwright and saves them to a raw JSON file."
)
def scrape_task(target_date: str):
    cmd = ["uv", "run", "python", "src/scraper/main_scraper.py", "--date", target_date]
    run_subprocess(cmd)


@task(
    name="Load to DuckDB",
    description="Loads raw scraped JSON news articles into the raw_news table in DuckDB."
)
def load_task(target_date: str, load_all: bool = False):
    cmd = ["uv", "run", "python", "src/load_to_db.py"]
    if load_all:
        cmd.append("--all")
    else:
        cmd.extend(["--date", target_date])
    run_subprocess(cmd)


@task(
    name="dbt Run",
    description="Runs dbt models to transform raw data in DuckDB."
)
def dbt_task():
    app_env = os.getenv("APP_ENV", "prod")
    target = "dev" if app_env.lower() == "dev" else "prod"
    cmd = ["uv", "run", "dbt", "run", "--target", target]
    run_subprocess(cmd, cwd="dbt_project")


@task(
    name="Export to Google Sheets",
    description="Exports mart_gpr_daily table from DuckDB to Google Sheets."
)
def export_task():
    cmd = ["uv", "run", "python", "src/export_table.py"]
    run_subprocess(cmd)


@flow(name="Indo GPR Index Pipeline")
def gpr_pipeline(target_date: str | None = None, load_all: bool = False):
    logger = get_run_logger()
    
    # Default target_date to yesterday's date if not provided
    if not target_date:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
    logger.info(f"Starting Indo GPR Index Pipeline for date: {target_date} (load_all={load_all})")
    
    # 1. Scrape (network intensive, with retries)
    scrape_future = scrape_task(target_date)
    
    # 2. Load to DuckDB
    load_future = load_task(target_date, load_all, wait_for=[scrape_future])
    
    # 3. dbt transformations and assertions (dbt build)
    dbt_future = dbt_task(wait_for=[load_future])
    
    # 4. Export results to Google Sheets
    export_future = export_task(wait_for=[dbt_future])
    
    logger.info("Indo GPR Index Pipeline completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Indo GPR Index Prefect Flow")
    parser.add_argument(
        "--date", 
        type=str, 
        help="Target date in YYYY-MM-DD format (defaults to yesterday)."
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Load all JSON files in the raw directory."
    )
    args = parser.parse_args()
    
    gpr_pipeline(target_date=args.date, load_all=args.all)
