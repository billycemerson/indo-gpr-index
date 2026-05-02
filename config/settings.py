import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
APP_ENV = os.getenv("APP_ENV", default= "prod")

class Config:
    ROOT_DIR = Path(__file__).resolve().parent.parent

    # Environment split
    DATA_DIR     = ROOT_DIR / "data" / APP_ENV   # data/production or data/development
    RAW_DATA_DIR = DATA_DIR / "raw"
    DB_PATH      = DATA_DIR / "gpr_index.db"

    # Ensure directories exist
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Credentials (shared across envs — same Google Sheet key)
    CREDENTIALS_DIR = ROOT_DIR / "config" / "credentials"
    GSHEET_KEY_PATH = CREDENTIALS_DIR / "gsheet_key.json"

    @classmethod
    def get_raw_scrape_path(cls, target_date: str = None) -> Path:
        if target_date is None:
            target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return cls.RAW_DATA_DIR / f"scrape_{target_date}.json"