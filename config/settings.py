from pathlib import Path
from datetime import datetime

class Config:
    # Get project root (2 levels up from this file)
    ROOT_DIR = Path(__file__).resolve().parent.parent
    
    # Data directories
    DATA_DIR = ROOT_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    
    # Ensure directories exist
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_raw_scrape_path(cls):
        """Generates path: data/raw/scrape_YYYY-MM-DD.json"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        return cls.RAW_DATA_DIR / f"scrape_{today_str}.json"

    BASE_URL = "https://www.antaranews.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }