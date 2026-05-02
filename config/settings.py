from pathlib import Path
from datetime import datetime, timedelta

class Config:
    # Get project root (2 levels up from this file)
    ROOT_DIR = Path(__file__).resolve().parent.parent
    
    # Data directories
    DATA_DIR = ROOT_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"

    # Google Sheet credentials
    CREDENTIALS_DIR = ROOT_DIR / "config" / "credentials"
    GSHEET_KEY_PATH = CREDENTIALS_DIR / "gsheet_key.json"
    
    # Ensure directories exist
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_raw_scrape_path(cls, target_date: str = None) -> Path:
        """
        Returns the path for the JSON file.
        If target_date is not provided, it defaults to yesterday's date.
        """
        if target_date is None:
            # Default to yesterday because we always scrape yesterday's news
            target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
        filename = f"scrape_{target_date}.json"
        return cls.RAW_DATA_DIR / filename

    BASE_URL = "https://www.antaranews.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }