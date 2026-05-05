"""
conftest.py
===========
Shared fixtures available to ALL test files automatically.
pytest loads this file before running any test — no import needed.

Fixtures here answer: "what sample data does every test start with?"
"""

import pytest


#  HTML fixtures — raw strings that simulate real website responses

@pytest.fixture
def antara_valid_html():
    """Single valid Antara article row."""
    return """
    <div class="row">
        <h2 class="post_title">
            <a href="https://www.antaranews.com/news/123/berita-politik">
                Berita Politik Penting
            </a>
        </h2>
        <span class="text-secondary">9 menit lalu</span>
    </div>
    """

@pytest.fixture
def antara_multi_html():
    """Multiple Antara rows — yesterday + today + older, to test filtering."""
    return """
    <div class="row">
        <h2 class="post_title">
            <a href="https://antaranews.com/news/1/artikel-kemarin">Artikel Kemarin</a>
        </h2>
        <span class="text-secondary">kemarin</span>
    </div>
    <div class="row">
        <h2 class="post_title">
            <a href="https://antaranews.com/news/2/artikel-hari-ini">Artikel Hari Ini</a>
        </h2>
        <span class="text-secondary">30 menit lalu</span>
    </div>
    <div class="row">
        <h2 class="post_title">
            <a href="https://antaranews.com/news/3/artikel-lama">Artikel Lama</a>
        </h2>
        <span class="text-secondary">12 Januari 2025</span>
    </div>
    """

@pytest.fixture
def antara_empty_html():
    """HTML with no article rows — simulates empty page or end of pagination."""
    return "<div>Tidak ada berita</div>"


@pytest.fixture
def kompas_valid_html():
    """Single valid Kompas article — link is on the parent <a> tag."""
    return """
    <a href="https://nasional.kompas.com/read/2025/01/01/berita-nasional">
        <div class="articleItem-wrap">
            <h2 class="articleTitle">Berita Nasional Kompas</h2>
            <div class="articlePost-date">Rabu, 1 Januari 2025</div>
        </div>
    </a>
    """

@pytest.fixture
def kompas_empty_html():
    """HTML with no Kompas article wrappers — triggers pagination stop."""
    return "<div class='empty-page'>Tidak ada artikel</div>"


#  Data fixtures — clean article dicts to feed loader/export tests

@pytest.fixture
def sample_articles():
    """Minimal valid article list — the guaranteed shape from BaseParser."""
    return [
        {
            "title":     "Berita Satu",
            "link":      "https://antaranews.com/news/1/berita-satu",
            "category":  "politik",
            "date_text": "kemarin",
            "source":    "antara",
        },
        {
            "title":     "Berita Dua",
            "link":      "https://kompas.com/read/2/berita-dua",
            "category":  "nasional",
            "date_text": "Rabu, 1 Januari 2025",
            "source":    "kompas",
        },
    ]

@pytest.fixture
def sample_articles_with_duplicate(sample_articles):
    """Same list with an extra duplicate link — to test dedup logic."""
    duplicate = sample_articles[0].copy()
    return sample_articles + [duplicate]

@pytest.fixture
def tempo_valid_html():
    """Single valid Tempo article — rendered HTML after Playwright JS execution."""
    return """
    <aside class="flex flex-row gap-3 py-4 container">
        <figure class="contents">
            <a href="/politik/unhas-ungkap-biaya-bangun-dapur-mbg-2132971"
               data-mrf-link="https://www.tempo.co/politik/unhas-ungkap-biaya-bangun-dapur-mbg-2132971">
                <img src="thumb.jpg">
            </a>
            <figcaption>
                <p class="text-neutral-1200">
                    <a href="/politik/unhas-ungkap-biaya-bangun-dapur-mbg-2132971"
                       data-mrf-link="https://www.tempo.co/politik/unhas-ungkap-biaya-bangun-dapur-mbg-2132971">
                        Unhas Ungkap Biaya Bangun Dapur MBG Mencapai Rp 2 Miliar
                    </a>
                </p>
            </figcaption>
        </figure>
    </aside>
    """

@pytest.fixture
def tempo_multi_html():
    """Multiple Tempo articles on one page."""
    return """
    <aside class="flex flex-row gap-3 py-4 container">
        <figure class="contents">
            <figcaption>
                <p><a href="/politik/artikel-satu"
                      data-mrf-link="https://www.tempo.co/politik/artikel-satu">
                    Artikel Politik Satu
                </a></p>
            </figcaption>
        </figure>
    </aside>
    <aside class="flex flex-row gap-3 py-4 container">
        <figure class="contents">
            <figcaption>
                <p><a href="/hukum/artikel-dua"
                      data-mrf-link="https://www.tempo.co/hukum/artikel-dua">
                    Artikel Hukum Dua
                </a></p>
            </figcaption>
        </figure>
    </aside>
    """

@pytest.fixture
def tempo_empty_html():
    """HTML with no aside.flex — simulates no articles found."""
    return "<div>Tidak ada artikel ditemukan</div>"

@pytest.fixture
def tempo_pagination_html():
    """HTML with pagination nav showing 2 pages."""
    return """
    <aside class="flex flex-row gap-3">
        <figure class="contents">
            <figcaption>
                <p><a href="/politik/artikel"
                      data-mrf-link="https://www.tempo.co/politik/artikel">
                    Artikel Dengan Paginasi
                </a></p>
            </figcaption>
        </figure>
    </aside>
    <nav>
        <button data-type="page" value="1">1</button>
        <button data-type="page" value="2">2</button>
    </nav>
    """