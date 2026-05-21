"""
parsers/__init__.py
===================
Central registry of all available parsers.

To add a new source:
  1. Create parsers/<media>.py with a class <Media>Parser(BaseParser)
  2. Import and add it to __all__ below — that's the only change needed here.
"""

from src.scraper.parsers.antara import AntaraParser
from src.scraper.parsers.kompas import KompasParser
from src.scraper.parsers.detik import DetikParser
from src.scraper.parsers.tempo import TempoParser
from src.scraper.parsers.tribunnews import TribunnewsParser

__all__ = ["AntaraParser", "DetikParser", "KompasParser", "TempoParser", "TribunnewsParser"]