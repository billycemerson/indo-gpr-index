import pytest
from src.scraper.parser import AntaraParser

def test_antara_parser_success():
    """Test if the parser correctly extracts title and link from mock HTML."""
    mock_html = """
    <div class="row">
        <h2 class="post_title">
            <a href="https://www.antaranews.com/news/123/berita-politik">Berita Politik Penting</a>
        </h2>
        <span class="text-secondary">9 menit lalu</span>
    </div>
    """
    
    parser = AntaraParser()
    results = parser.parse_list_page(mock_html)
    
    assert len(results) == 1
    assert results[0]['title'] == "Berita Politik Penting"
    assert results[0]['date_text'] == "9 menit lalu"
    assert "123" in results[0]['link']

def test_antara_parser_no_data():
    """Test parser behavior when no articles are found."""
    mock_html = "<div>No news here</div>"
    parser = AntaraParser()
    results = parser.parse_list_page(mock_html)
    
    assert results == []