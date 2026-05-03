import subprocess
import sys

def run_command(command: str, step_name: str) -> None:
    """
    Executes a shell command as a step in the data pipeline.
    If the command fails, it catches the error, logs it, and stops the entire pipeline.
    
    Args:
        command (str): The terminal command to execute.
        step_name (str): A human-readable name for the pipeline step.
    """
    print(f"\n{'-'*60}")
    print(f"[STARTING] Step: {step_name}")
    print(f"Command: {command}")
    print(f"{'-'*60}\n")
    
    try:
        # shell=True allows running complex commands (like cd folder && command)
        # check=True forces the subprocess to raise a CalledProcessError if the exit code is non-zero
        subprocess.run(
            command, 
            shell=True, 
            check=True, 
            text=True
        )
        print(f"\n[SUCCESS] Completed: {step_name}")
        
    except subprocess.CalledProcessError as error:
        print(f"\n[ERROR] Pipeline failed at step: {step_name}")
        print(f"Exit Status Code: {error.returncode}")
        print("Halting pipeline execution to prevent downstream data corruption.")
        sys.exit(1)

def main():
    """
    Main orchestrator function defining the sequence of the ELT pipeline.
    """
    print("Initializing Indonesia GPR Index Pipeline...")
    
    # Step 1: Quality Assurance (Testing)
    # Validates the scraper logic and API connection handlers before touching real data
    run_command(
        command="uv run pytest", 
        step_name="Unit Tests"
    )
    
    # Step 2: Extract (Web Scraping)
    # Fetches yesterday's news from Antara
    run_command(
        command="uv run python src/scraper/main_scraper.py", 
        step_name="Data Extraction (Scraper)"
    )
    
    # Step 3: Load (DuckDB)
    # Appends the raw JSON data to the Bronze layer in DuckDB
    run_command(
        command="uv run python src/load_to_db.py", 
        step_name="Data Load (Bronze Layer)"
    )
    
    # Step 4: Transform (dbt)
    # Moves into the dbt directory and runs the Medallion architecture transformations
    # Calculates the keyword indices incrementally
    run_command(
        command="cd dbt_project && uv run dbt run --profiles-dir .", 
        step_name="Data Transformation (Silver & Gold Layers)"
    )
    
    # Step 5: Reverse ETL (Google Sheets)
    # Exports the newly calculated Gold layer data to the external dashboard
    run_command(
        command="uv run python src/export_table.py", 
        step_name="Data Export (Reverse ETL)"
    )
    
    print("\n[FINISHED] Pipeline executed successfully from end-to-end.")

if __name__ == "__main__":
    main()