"""
base_parser.py
==============
The Blueprint. Every media parser MUST inherit from BaseParser and implement
all abstract methods. This enforces a uniform interface so main_scraper.py
never needs to know the internal mechanics of any specific source.

Adding a new source = create a new file in parsers/, inherit BaseParser, done.
"""

from abc import ABC, abstractmethod


class BaseParser(ABC):
    """
    Abstract base class (contract) for all media parsers.

    Concrete parsers (AntaraParser, KompasParser, etc.) must implement:
        - source_name  : str property identifying the media source
        - fetch_news() : core scraping logic, always returns a list of dicts

    Guaranteed article dict shape (all parsers must produce this):
        {
            "title"     : str,
            "link"      : str,
            "category"  : str,
            "date_text" : str,
            "source"    : str,  <- auto-stamped by fetch_news via _stamp()
        }
    """

    #  Abstract interface — subclasses MUST implement these

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Returns the canonical lowercase name of this media source.
        Example: "antara", "kompas", "detik"
        Used to auto-stamp the 'source' field on every article.
        """
        ...

    @abstractmethod
    def fetch_news(self, target_date: str) -> list[dict]:
        """
        Main entry point called by main_scraper.py.

        Args:
            target_date (str): Date in YYYY-MM-DD format.
                               Parsers that don't need it (e.g. Antara uses
                               relative terms) may ignore it internally.

        Returns:
            list[dict]: List of article dicts with the guaranteed shape above.
                        The 'source' field is stamped automatically by _stamp().
        """
        ...

    #  Shared helpers — available to all subclasses, no need to override

    def _stamp(self, articles: list[dict]) -> list[dict]:
        """
        Stamps 'source' onto every article dict using this parser's source_name.
        Call this at the end of fetch_news() before returning.

        Example:
            return self._stamp(results)
        """
        for article in articles:
            article["source"] = self.source_name
        return articles

    def __repr__(self) -> str:
        return f"<Parser: {self.source_name}>"
