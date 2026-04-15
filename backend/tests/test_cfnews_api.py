"""
EdRCF 6.0 — CFNEWS API Integration Tests
REST endpoint tests for /api/cfnews, /api/cfnews/entreprises,
/api/cfnews/veille, /api/cfnews/recherche, and Copilot CFNEWS intent.
"""

import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Shared mock HTML that simulates cfnews.net homepage
# ---------------------------------------------------------------------------

MOCK_CFNEWS_HTML = """
<html><body>
<a href="/L-actualite/Capital-developpement/Operations/Augmentation-de-capital/Tra-C-Industrie-soude-son-capital-645731">
  Tra-C Industrie soude son capital
</a>
<a href="/L-actualite/International/Operations/LBO/Blue-communique-de-l-autre-cote-de-la-Manche-645118">
  Blue communique de l'autre côté de la Manche
</a>
<a href="/L-actualite/Capital-innovation/Operations/Amorcage/Mirabelle-recolte-les-fruits-645038">
  Mirabelle récolte les fruits de son amorçage
</a>
<a href="/L-actualite/M-A-Corporate/Operations/Majoritaire/Maison-Cadiou-ouvre-ses-portes-645748">
  Maison Cadiou ouvre ses portes à un tourangeau
</a>
<a href="/L-actualite/Nominations/Avocat/Fidal-se-structure-en-region-645646">
  Fidal se structure en région
</a>
</body></html>
"""


def _mock_fetch_page(url):
    """Return a BeautifulSoup from our mock HTML."""
    return BeautifulSoup(MOCK_CFNEWS_HTML, "html.parser")


def _mock_fetch_page_fail(url):
    """Simulate cfnews.net being down."""
    return None


# ---------------------------------------------------------------------------
# Test client fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def cfnews_client(sample_enriched_target):
    """FastAPI test client with CFNEWS mock."""
    from main import app, enriched_targets
    from httpx import AsyncClient, ASGITransport

    enriched_targets.clear()
    enriched_targets.append(sample_enriched_target)

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


# =========================================================================
# 1. GET /api/cfnews — articles bruts
# =========================================================================

class TestCfnewsArticlesEndpoint:
    @pytest.mark.asyncio
    async def test_returns_articles(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page):
            resp = await cfnews_client.get("/api/cfnews")

        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_cfnews_down_returns_502(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", return_value=None):
            resp = await cfnews_client.get("/api/cfnews")
        assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_limite_parameter(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page):
            resp = await cfnews_client.get("/api/cfnews", params={"limite": 2})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) <= 2


# =========================================================================
# 2. GET /api/cfnews/entreprises — company list
# =========================================================================

class TestCfnewsEntreprisesEndpoint:
    @pytest.mark.asyncio
    async def test_returns_unique_companies(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page):
            resp = await cfnews_client.get("/api/cfnews/entreprises")

        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        names = [e["entreprise"] for e in data["data"]]
        # No duplicates
        assert len(names) == len(set(names))

    @pytest.mark.asyncio
    async def test_company_has_required_fields(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page):
            resp = await cfnews_client.get("/api/cfnews/entreprises")

        for e in resp.json()["data"]:
            assert "entreprise" in e
            assert "categorie" in e
            assert "titre" in e
            assert "url" in e


# =========================================================================
# 3. GET /api/cfnews/recherche/{nom} — search
# =========================================================================

class TestCfnewsRechercheEndpoint:
    @pytest.mark.asyncio
    async def test_search_finds_match(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page):
            resp = await cfnews_client.get("/api/cfnews/recherche/Tra-C")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("Tra-C" in a["titre"] for a in data["data"])

    @pytest.mark.asyncio
    async def test_search_no_match(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page):
            resp = await cfnews_client.get("/api/cfnews/recherche/ZZZZNOEXIST")

        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page):
            resp = await cfnews_client.get("/api/cfnews/recherche/blue")

        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# =========================================================================
# 4. GET /api/cfnews/veille — enriched targets with scoring
# =========================================================================

class TestCfnewsVeilleEndpoint:
    @pytest.mark.asyncio
    async def test_veille_returns_targets(self, cfnews_client):
        """Veille endpoint with mocked Pappers returning empty (cfnews-only targets)."""
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page), \
             patch("main.search_pappers", new_callable=AsyncMock, return_value={"resultats": []}):
            resp = await cfnews_client.get("/api/cfnews/veille", params={"limite": 3})

        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        assert "source" in data
        assert data["source"] == "cfnews-veille"

    @pytest.mark.asyncio
    async def test_veille_target_has_cfnews_meta(self, cfnews_client):
        """Each target should carry cfnews metadata."""
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page), \
             patch("main.search_pappers", new_callable=AsyncMock, return_value={"resultats": []}):
            resp = await cfnews_client.get("/api/cfnews/veille", params={"limite": 2})

        for target in resp.json()["data"]:
            assert "cfnews" in target
            assert "titre" in target["cfnews"]
            assert "categorie" in target["cfnews"]
            assert "url" in target["cfnews"]

    @pytest.mark.asyncio
    async def test_veille_target_has_scoring_fields(self, cfnews_client):
        """Each target must have globalScore, priorityLevel, financials."""
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page), \
             patch("main.search_pappers", new_callable=AsyncMock, return_value={"resultats": []}):
            resp = await cfnews_client.get("/api/cfnews/veille", params={"limite": 2})

        for target in resp.json()["data"]:
            assert "globalScore" in target
            assert "priorityLevel" in target
            assert "financials" in target
            assert "name" in target

    @pytest.mark.asyncio
    async def test_veille_sorted_by_score_desc(self, cfnews_client):
        """Results should be sorted by globalScore descending."""
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page), \
             patch("main.search_pappers", new_callable=AsyncMock, return_value={"resultats": []}):
            resp = await cfnews_client.get("/api/cfnews/veille", params={"limite": 5})

        targets = resp.json()["data"]
        scores = [t["globalScore"] for t in targets]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_veille_with_pappers_match(self, cfnews_client):
        """When Pappers finds a company, target should be enriched."""
        pappers_result = {
            "resultats": [{
                "siren": "999888777",
                "nom_entreprise": "TRA-C INDUSTRIE",
                "siege": {"code_postal": "44000", "ville": "NANTES"},
                "code_naf": "25.62A",
                "libelle_code_naf": "Mécanique industrielle",
                "effectif": "200",
                "chiffre_affaires": 56000000,
                "forme_juridique": "SAS",
                "date_creation": "2001-01-01",
            }]
        }
        pappers_company = {
            "siren": "999888777",
            "nom_entreprise": "TRA-C INDUSTRIE",
            "siege": {"code_postal": "44000", "ville": "NANTES", "departement": "44"},
            "code_naf": "25.62A",
            "libelle_code_naf": "Mécanique industrielle",
            "effectif": "200",
            "date_creation": "2001-01-01",
            "forme_juridique": "SAS",
            "representants": [
                {"prenom": "Jean", "nom": "MARTIN", "qualite": "President", "age": 62}
            ],
            "finances": [
                {"chiffre_affaires": 56000000, "resultat": 4000000, "annee": 2024},
            ],
            "entreprise_cessee": False,
            "etablissements": [],
            "beneficiaires_effectifs": [],
            "publications_bodacc": [],
        }

        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page), \
             patch("main.search_pappers", new_callable=AsyncMock, return_value=pappers_result), \
             patch("main.get_pappers_company", new_callable=AsyncMock, return_value=pappers_company):
            resp = await cfnews_client.get("/api/cfnews/veille", params={"limite": 3})

        assert resp.status_code == 200
        targets = resp.json()["data"]
        # At least one should have been enriched via Pappers
        enriched = [t for t in targets if t.get("source") == "cfnews+pappers"]
        assert len(enriched) >= 1
        t = enriched[0]
        assert t["siren"] == "999888777"
        assert t["globalScore"] > 0
        assert t["cfnews"]["titre"] != ""

    @pytest.mark.asyncio
    async def test_veille_cfnews_down_returns_502(self, cfnews_client):
        with patch("mcp_cfnews._fetch_page", return_value=None):
            resp = await cfnews_client.get("/api/cfnews/veille")
        assert resp.status_code == 502


# =========================================================================
# 5. Copilot — CFNEWS intent detection & response
# =========================================================================

class TestCopilotCfnewsIntent:
    CFNEWS_KEYWORDS = [
        "cfnews", "veille", "actualité", "actualite", "actus", "news",
        "presse", "article", "dernières nouvelles", "dernieres nouvelles",
        "qui fait l'actu", "actu m&a", "actu ma",
    ]

    def _wants_cfnews(self, query: str) -> bool:
        ql = query.lower()
        return any(w in ql for w in self.CFNEWS_KEYWORDS)

    def test_cfnews_keyword_triggers(self):
        assert self._wants_cfnews("montre moi les actus cfnews") is True

    def test_veille_triggers(self):
        assert self._wants_cfnews("lance la veille") is True

    def test_actualite_triggers(self):
        assert self._wants_cfnews("quelles sont les actualités M&A") is True

    def test_news_triggers(self):
        assert self._wants_cfnews("news du jour") is True

    def test_presse_triggers(self):
        assert self._wants_cfnews("que dit la presse") is True

    def test_actu_ma_triggers(self):
        assert self._wants_cfnews("actu M&A de la semaine") is True

    def test_casual_does_not_trigger(self):
        assert self._wants_cfnews("top 5 cibles") is False
        assert self._wants_cfnews("bonjour") is False
        assert self._wants_cfnews("secteur courtage") is False

    def test_scoring_does_not_trigger(self):
        assert self._wants_cfnews("explique le scoring") is False

    def test_pappers_does_not_trigger(self):
        assert self._wants_cfnews("recherche pappers BTP") is False

    @pytest.mark.asyncio
    async def test_copilot_cfnews_query(self, cfnews_client):
        """Full integration: Copilot with 'veille cfnews' query returns CFNEWS data."""
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page), \
             patch("main.DEEPSEEK_API_KEY", ""):
            resp = await cfnews_client.get("/api/copilot/query", params={"q": "veille cfnews"})

        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "source" in data
        # Should mention CFNEWS in response
        assert "CFNEWS" in data["response"] or "cfnews" in data["source"]

    @pytest.mark.asyncio
    async def test_copilot_cfnews_lists_companies(self, cfnews_client):
        """Copilot CFNEWS response should list company names."""
        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page), \
             patch("main.DEEPSEEK_API_KEY", ""):
            resp = await cfnews_client.get("/api/copilot/query", params={"q": "actualités"})

        response_text = resp.json()["response"]
        # At least some companies from our mock should appear
        assert any(name in response_text for name in ["Tra-C", "Blue", "Mirabelle", "Maison Cadiou", "Fidal"])

    @pytest.mark.asyncio
    async def test_copilot_non_cfnews_still_works(self, cfnews_client):
        """Non-CFNEWS queries must continue to work (no regression)."""
        resp = await cfnews_client.get("/api/copilot/query", params={"q": "top cibles"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "Top" in data["response"] or "top" in data["response"].lower()

    @pytest.mark.asyncio
    async def test_copilot_help_mentions_cfnews(self, cfnews_client):
        """Help response should mention CFNEWS as available option."""
        resp = await cfnews_client.get("/api/copilot/query", params={"q": "aide"})
        assert resp.status_code == 200
        assert "CFNEWS" in resp.json()["response"]


# =========================================================================
# 6. Use Case End-to-End: CFNEWS → Score → Priority
# =========================================================================

class TestUseCaseEndToEnd:
    """
    Use Case: 'Tra-C Industrie' appears on CFNEWS homepage.
    The veille endpoint should detect it, look it up on Pappers,
    score it, and return it as a Target with correct priority level.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_company_scoring(self, cfnews_client):
        pappers_search = {
            "resultats": [{
                "siren": "444555666",
                "nom_entreprise": "TRA-C INDUSTRIE",
                "siege": {"code_postal": "44000", "ville": "NANTES"},
                "code_naf": "25.62A",
                "libelle_code_naf": "Mécanique industrielle",
                "effectif": "200",
                "forme_juridique": "SAS",
                "date_creation": "2001-01-01",
            }]
        }
        pappers_detail = {
            "siren": "444555666",
            "nom_entreprise": "TRA-C INDUSTRIE",
            "siege": {"code_postal": "44000", "ville": "NANTES", "departement": "44"},
            "code_naf": "25.62A",
            "libelle_code_naf": "Mécanique industrielle",
            "effectif": "200",
            "date_creation": "2001-01-01",
            "forme_juridique": "SAS",
            "representants": [
                {
                    "prenom": "Philippe",
                    "nom": "MARTIN",
                    "qualite": "President",
                    "age": 64,
                    "date_de_naissance": "1962-03-15",
                    "date_prise_de_poste": "2001-01-01",
                    "autres_mandats": [{"siren": "111"}, {"siren": "222"}],
                }
            ],
            "finances": [
                {"chiffre_affaires": 56000000, "resultat": 5000000, "annee": 2024},
                {"chiffre_affaires": 48000000, "resultat": 4000000, "annee": 2023},
            ],
            "entreprise_cessee": False,
            "etablissements": [
                {"siret": "44455566600010", "ville": "NANTES"},
                {"siret": "44455566600020", "ville": "PARIS"},
            ],
            "beneficiaires_effectifs": [],
            "publications_bodacc": [],
            "procedure_collective_existe": False,
            "procedure_collective_en_cours": False,
            "procedures_collectives": [],
        }

        with patch("mcp_cfnews._fetch_page", side_effect=_mock_fetch_page), \
             patch("main.search_pappers", new_callable=AsyncMock, return_value=pappers_search), \
             patch("main.get_pappers_company", new_callable=AsyncMock, return_value=pappers_detail):
            resp = await cfnews_client.get("/api/cfnews/veille", params={"limite": 5})

        assert resp.status_code == 200
        targets = resp.json()["data"]

        # Find Tra-C in results
        trac = next((t for t in targets if "444555666" in t.get("siren", "")), None)
        assert trac is not None, f"Tra-C not found in results: {[t['name'] for t in targets]}"

        # Verify scoring
        assert trac["globalScore"] > 0
        assert trac["priorityLevel"] in [
            "Action Prioritaire", "Qualification", "Monitoring", "Veille Passive"
        ]

        # Verify company data
        assert trac["siren"] == "444555666"
        assert trac["sector"] != ""
        assert trac["region"] != ""

        # Verify signals detected (founder 64yo + multi-mandats + CA growth + multi-etablissements)
        signal_ids = [s["id"] for s in trac.get("topSignals", [])]
        assert len(signal_ids) >= 2, f"Expected signals, got: {signal_ids}"

        # Verify financials
        assert trac["financials"]["revenue"] != "N/A"
        assert trac["financials"]["ebitda"] != "N/A"

        # Verify CFNEWS metadata preserved
        assert trac["cfnews"]["titre"] != ""
        assert "cfnews.net" in trac["cfnews"]["url"]
        assert trac["source"] == "cfnews+pappers"

        # Verify dirigeants
        assert len(trac["dirigeants"]) >= 1
        assert trac["dirigeants"][0]["age"] == 64
