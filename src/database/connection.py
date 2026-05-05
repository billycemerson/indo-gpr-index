import duckdb
from config.settings import Config

def get_duckdb_connection():
    """Connect to or create the local DuckDB database file."""
    return duckdb.connect(str(Config.DB_PATH))