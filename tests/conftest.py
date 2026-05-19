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
def detik_valid_html():
    """Single valid Detik article with absolute date."""
    return """
    <article class="list-content__item">
        <div class="media media--left media--image-radius block-link">
            <div class="media__text">
                <h3 class="media__title">
                    <a href="https://news.detik.com/internasional/d-8483801/berita-detik"
                       class="media__link">
                        Berita Detik Internasional Penting
                    </a>
                </h3>
                <div class="media__date">
                    <span d-time="1778472431" title="Jumat, 15 Mei 2026 11:07 WIB">
                        Jumat, 15 Mei 2026 11:07 WIB
                    </span>
                </div>
            </div>
        </div>
    </article>
    """

@pytest.fixture
def detik_multi_html():
    """Multiple Detik articles on one page."""
    return """
    <article class="list-content__item">
        <div class="media__text">
            <h3 class="media__title">
                <a href="https://news.detik.com/internasional/d-8483801/artikel-1">Artikel Detik 1</a>
            </h3>
            <div class="media__date"><span>Jumat, 15 Mei 2026 10:00 WIB</span></div>
        </div>
    </article>
    <article class="list-content__item">
        <div class="media__text">
            <h3 class="media__title">
                <a href="https://news.detik.com/internasional/d-8483802/artikel-2">Artikel Detik 2</a>
            </h3>
            <div class="media__date"><span>Jumat, 15 Mei 2026 09:30 WIB</span></div>
        </div>
    </article>
    <article class="list-content__item">
        <div class="media__text">
            <h3 class="media__title">
                <a href="https://news.detik.com/internasional/d-8483803/artikel-3">Artikel Detik 3</a>
            </h3>
            <div class="media__date"><span>Jumat, 15 Mei 2026 08:15 WIB</span></div>
        </div>
    </article>
    """

@pytest.fixture
def detik_relative_date_html():
    """Detik article with relative date (for testing date parsing fallback)."""
    return """
    <article class="list-content__item">
        <div class="media__text">
            <h3 class="media__title">
                <a href="https://news.detik.com/internasional/d-8483801/artikel-baru">
                    Artikel Baru
                </a>
            </h3>
            <div class="media__date"><span>18 jam yang lalu</span></div>
        </div>
    </article>
    """

@pytest.fixture
def detik_empty_html():
    """HTML with no article items — simulates empty page."""
    return "<div>No articles found</div>"

@pytest.fixture
def detik_with_pagination_html():
    """HTML with pagination next button."""
    return """
    <article class="list-content__item">
        <div class="media__text">
            <h3 class="media__title">
                <a href="https://news.detik.com/internasional/d-8483801/artikel-halaman-1">
                    Artikel Halaman 1
                </a>
            </h3>
            <div class="media__date"><span>Jumat, 15 Mei 2026 10:00 WIB</span></div>
        </div>
    </article>
    <a href="?page=2" class="next">Next</a>
    """

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
def kompas_multi_html():
    """Multiple Kompas articles on one page."""
    return """
    <a href="https://nasional.kompas.com/read/2025/01/01/berita-nasional-1">
        <div class="articleItem-wrap">
            <h2 class="articleTitle">Berita Nasional Satu</h2>
            <div class="articlePost-date">Rabu, 1 Januari 2025 08:00 WIB</div>
        </div>
    </a>
    <a href="https://global.kompas.com/read/2025/01/01/berita-global-2">
        <div class="articleItem-wrap">
            <h2 class="articleTitle">Berita Global Dua</h2>
            <div class="articlePost-date">Rabu, 1 Januari 2025 10:30 WIB</div>
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

@pytest.fixture
def tribunnews_valid_html():
    """Single valid Tribunnews article with time tag and title attribute."""
    return """
    <li class="ptb15">
        <h3 class="f16 fbo">
            <a href="https://www.tribunnews.com/nasional/2026/05/15/berita-nasional-1"
               title="Berita Nasional Penting Hari Ini">
                Berita Nasional Penting Hari Ini
            </a>
        </h3>
        <time class="grey">Jumat, 15 Mei 2026 14:30 WIB</time>
    </li>
    """

@pytest.fixture
def tribunnews_multi_html():
    """Multiple Tribunnews articles in newest-first order."""
    return """
    <li class="ptb15">
        <h3 class="f16 fbo">
            <a href="https://www.tribunnews.com/nasional/2026/05/15/artikel-hari-ini"
               title="Artikel 15 Mei 2026">Artikel 15 Mei 2026</a>
        </h3>
        <time class="grey">Jumat, 15 Mei 2026 10:00 WIB</time>
    </li>
    <li class="ptb15">
        <h3 class="f16 fbo">
            <a href="https://www.tribunnews.com/nasional/2026/05/14/artikel-kemarin"
               title="Artikel 14 Mei 2026">Artikel 14 Mei 2026</a>
        </h3>
        <time class="grey">Kamis, 14 Mei 2026 20:00 WIB</time>
    </li>
    <li class="ptb15">
        <h3 class="f16 fbo">
            <a href="https://www.tribunnews.com/nasional/2026/05/13/artikel-lebih-lama"
               title="Artikel 13 Mei 2026">Artikel 13 Mei 2026</a>
        </h3>
        <time class="grey">Rabu, 13 Mei 2026 15:00 WIB</time>
    </li>
    """

@pytest.fixture
def tribunnews_empty_html():
    """HTML with no article items — simulates empty page."""
    return "<div>Tidak ada berita</div>"

@pytest.fixture
def tribunnews_no_title_html():
    """Article with missing title (a tag without title attribute)."""
    return """
    <li class="ptb15">
        <h3 class="f16 fbo">
            <a href="https://www.tribunnews.com/nasional/2026/05/15/berita-no-title">
                <!-- no title attribute -->
            </a>
        </h3>
        <time class="grey">Jumat, 15 Mei 2026 14:30 WIB</time>
    </li>
    """

@pytest.fixture
def tribunnews_no_link_html():
    """Article with missing link."""
    return """
    <li class="ptb15">
        <h3 class="f16 fbo">
            <a title="Berita Tanpa Link"></a>
        </h3>
        <time class="grey">Jumat, 15 Mei 2026 14:30 WIB</time>
    </li>
    """