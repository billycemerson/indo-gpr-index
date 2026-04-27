import duckdb
from config.settings import Config

def get_duckdb_connection():
    """Connect to or create the local DuckDB database file."""
    db_path = Config.DATA_DIR / "gpr_index.db"
    return duckdb.connect(str(db_path))