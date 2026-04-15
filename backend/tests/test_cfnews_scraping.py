"""
EdRCF 6.0 — CFNEWS Scraping Unit Tests
Tests for mcp_cfnews.py: extraction, company detection, URL parsing, error handling.
"""

import sys
import os
import re

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_cfnews import (
    _extract_articles,
    _extract_category,
    _extract_company_from_title,
    _is_valid_company,
    _find_date_near,
)
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Helpers: build minimal HTML that mirrors cfnews.net structure
# ---------------------------------------------------------------------------

def _make_soup(articles_html: str) -> BeautifulSoup:
    return BeautifulSoup(f"<html><body>{articles_html}</body></html>", "html.parser")


def _article_link(title: str, href: str) -> str:
    return f'<a href="{href}">{title}</a>'


SAMPLE_ARTICLES_HTML = """
<a href="/L-actualite/Capital-developpement/Operations/Augmentation-de-capital/Tra-C-Industrie-soude-son-capital-645731">Tra-C Industrie soude son capital</a>
<a href="/L-actualite/International/Operations/LBO/Blue-communique-de-l-autre-cote-de-la-Manche-645118">Blue communique de l'autre côté de la Manche</a>
<a href="/L-actualite/Capital-innovation/Operations/Amorcage/Mirabelle-recolte-les-fruits-de-son-amorcage-645038">Mirabelle récolte les fruits de son amorçage</a>
<a href="/L-actualite/M-A-Corporate/Operations/Majoritaire/Maison-Cadiou-ouvre-ses-portes-a-un-tourangeau-645748">Maison Cadiou ouvre ses portes à un tourangeau</a>
<a href="/L-actualite/Nominations/Avocat/Bird-Bird-se-renforce-en-droit-social-645685">Bird &amp; Bird se renforce en droit social</a>
<a href="/L-actualite/Marche-General/Paroles-d-expert/Startuppers-le-financement-n-est-plus-un-sprint-645699">Startuppers, le financement n'est plus un sprint</a>
"""

NOISY_HTML = """
<a href="/L-actualite/Capital-developpement/Operations/LBO/Netco-fait-son-LBO-ter-645100">14/04/2026Capital développementNetco fait son LBO ter</a>
<a href="/L-actualite/International/Operations/Capital-innovation/Un-fonds-biotech-francais-monte-chez-Adcendo-645658">Un fonds biotech français monte chez Adcendo</a>
<a href="/L-actualite/Marche-General/Etudes/Retail-les-actifs-prives-confirment-leur-essor-645481">TECH |Retail : les actifs privés confirment leur essor</a>
"""


# =========================================================================
# 1. _extract_articles — core extraction
# =========================================================================

class TestExtractArticles:
    def test_extracts_correct_count(self):
        soup = _make_soup(SAMPLE_ARTICLES_HTML)
        articles = _extract_articles(soup)
        assert len(articles) == 6

    def test_article_has_required_fields(self):
        soup = _make_soup(SAMPLE_ARTICLES_HTML)
        articles = _extract_articles(soup)
        for a in articles:
            assert "id" in a
            assert "titre" in a
            assert "entreprise" in a
            assert "categorie" in a
            assert "url" in a

    def test_article_id_is_numeric(self):
        soup = _make_soup(SAMPLE_ARTICLES_HTML)
        articles = _extract_articles(soup)
        for a in articles:
            assert a["id"].isdigit()

    def test_url_is_absolute(self):
        soup = _make_soup(SAMPLE_ARTICLES_HTML)
        articles = _extract_articles(soup)
        for a in articles:
            assert a["url"].startswith("https://www.cfnews.net/")

    def test_deduplication_by_id(self):
        """Same article linked twice should appear only once."""
        html = SAMPLE_ARTICLES_HTML + '\n<a href="/L-actualite/Capital-developpement/Operations/Augmentation-de-capital/Tra-C-Industrie-soude-son-capital-645731">Tra-C Industrie soude son capital (dupe)</a>'
        soup = _make_soup(html)
        articles = _extract_articles(soup)
        ids = [a["id"] for a in articles]
        assert ids.count("645731") == 1

    def test_filters_short_titles(self):
        """Links with text < 10 chars should be filtered out."""
        html = '<a href="/L-actualite/Capital/Operations/LBO/Short-12345">Short</a>'
        soup = _make_soup(html)
        articles = _extract_articles(soup)
        assert len(articles) == 0

    def test_filters_non_article_urls(self):
        """URLs without numeric ID suffix are not articles."""
        html = '<a href="/L-actualite/Capital-developpement">Capital développement section</a>'
        soup = _make_soup(html)
        articles = _extract_articles(soup)
        assert len(articles) == 0

    def test_none_soup_returns_empty(self):
        articles = _extract_articles(None)
        assert articles == []

    def test_cleans_date_prefix(self):
        """Date+category prefix should be stripped from title."""
        soup = _make_soup(NOISY_HTML)
        articles = _extract_articles(soup)
        netco = next((a for a in articles if "645100" in a["id"]), None)
        assert netco is not None
        assert not netco["titre"].startswith("14/04/2026")
        assert "Netco" in netco["titre"]

    def test_cleans_tech_prefix(self):
        """TECH | prefix should be stripped."""
        soup = _make_soup(NOISY_HTML)
        articles = _extract_articles(soup)
        retail = next((a for a in articles if "645481" in a["id"]), None)
        assert retail is not None
        assert not retail["titre"].startswith("TECH")


# =========================================================================
# 2. _extract_category — URL → category
# =========================================================================

class TestExtractCategory:
    def test_capital_developpement(self):
        cat = _extract_category("/L-actualite/Capital-developpement/Operations/LBO/Foo-123456")
        assert cat == "Capital developpement"

    def test_international(self):
        cat = _extract_category("/L-actualite/International/Operations/M-A/Foo-123456")
        assert cat == "International"

    def test_nominations(self):
        cat = _extract_category("/L-actualite/Nominations/Avocat/Foo-123456")
        assert cat == "Nominations"

    def test_m_a_corporate(self):
        cat = _extract_category("/L-actualite/M-A-Corporate/Operations/Foo-123456")
        assert cat == "M A Corporate"

    def test_short_url_fallback(self):
        cat = _extract_category("/L-actualite")
        assert cat != ""


# =========================================================================
# 3. _extract_company_from_title — NLP-lite extraction
# =========================================================================

class TestExtractCompany:
    def test_verb_pattern(self):
        assert _extract_company_from_title("Tra-C Industrie soude son capital") == "Tra-C Industrie"

    def test_verb_leve(self):
        assert _extract_company_from_title("TerraSpark lève 10M EUR") == "TerraSpark"

    def test_verb_acquiert(self):
        assert _extract_company_from_title("Maison Cadiou acquiert un concurrent") == "Maison Cadiou"

    def test_verb_renforce(self):
        assert _extract_company_from_title("Bird & Bird se renforce en droit social") == "Bird & Bird"

    def test_colon_pattern(self):
        result = _extract_company_from_title("Retail : les actifs privés confirment leur essor")
        assert result == "Retail"

    def test_comma_pattern(self):
        result = _extract_company_from_title("Startuppers, le financement n'est plus un sprint")
        assert result == "Startuppers"

    def test_no_company_returns_empty(self):
        """Titles starting with generic words should return empty."""
        result = _extract_company_from_title("Un fonds biotech français monte chez Adcendo")
        assert result == ""

    def test_short_name_rejected(self):
        result = _extract_company_from_title("A lance une opération massive")
        assert result == ""


# =========================================================================
# 4. _is_valid_company — false positive filter
# =========================================================================

class TestIsValidCompany:
    def test_valid_company(self):
        assert _is_valid_company("Tra-C Industrie") is True

    def test_valid_short(self):
        assert _is_valid_company("Blue") is True

    def test_rejects_empty(self):
        assert _is_valid_company("") is False

    def test_rejects_single_char(self):
        assert _is_valid_company("A") is False

    def test_rejects_article_un(self):
        assert _is_valid_company("Un") is False

    def test_rejects_article_une(self):
        assert _is_valid_company("Une") is False

    def test_rejects_un_fonds(self):
        assert _is_valid_company("Un fonds biotech") is False

    def test_rejects_selon(self):
        assert _is_valid_company("Selon les analystes") is False

    def test_rejects_private_equity(self):
        assert _is_valid_company("Private Equity") is False

    def test_rejects_dette(self):
        assert _is_valid_company("Dette privée") is False

    def test_rejects_investir(self):
        assert _is_valid_company("Investir dans l'IA") is False

    def test_rejects_too_long(self):
        assert _is_valid_company("x" * 61) is False

    def test_rejects_date(self):
        assert _is_valid_company("14/04/2026 Truc") is False

    def test_accepts_ampersand(self):
        assert _is_valid_company("Bird & Bird") is True

    def test_accepts_plus(self):
        assert _is_valid_company("Oligo+") is True

    def test_rejects_closing(self):
        assert _is_valid_company("Closing") is False

    def test_rejects_correction(self):
        assert _is_valid_company("Correction de la valorisation") is False

    def test_rejects_reprises(self):
        assert _is_valid_company("Reprises à la barre") is False

    def test_rejects_mid(self):
        assert _is_valid_company("Mid") is False

    def test_rejects_de(self):
        assert _is_valid_company("De") is False
