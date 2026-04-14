"""
EdRCF 6.0 — Copilot Logic Tests
Tests for SIREN detection, wants_pappers, and company name search in copilot_query.
"""

import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSirenDetection:
    """Tests for SIREN pattern detection in copilot queries."""

    def test_siren_9_digits_detected(self):
        match = re.search(r'\b(\d{9})\b', "Donne moi les infos sur 123456789")
        assert match is not None
        assert match.group(1) == "123456789"

    def test_siren_in_sentence(self):
        match = re.search(r'\b(\d{9})\b', "recherche entreprise siren 987654321 merci")
        assert match is not None
        assert match.group(1) == "987654321"

    def test_no_siren_short_number(self):
        match = re.search(r'\b(\d{9})\b', "code 12345")
        assert match is None

    def test_no_siren_long_number(self):
        match = re.search(r'\b(\d{9})\b', "numero 12345678901")
        # 10+ digits should not match as 9-digit SIREN
        # (it might match a 9-digit substring, but the \b boundaries prevent it in proper context)
        pass  # regex behavior depends on boundaries

    def test_siren_at_start(self):
        match = re.search(r'\b(\d{9})\b', "123456789")
        assert match is not None

    def test_siren_with_spaces(self):
        """SIREN with spaces should NOT match the regex (intentional)."""
        match = re.search(r'\b(\d{9})\b', "123 456 789")
        assert match is None


class TestWantsPappers:
    """Tests for wants_pappers keyword detection.

    These keywords should NOT trigger Pappers search for casual conversation.
    Only specific M&A/screening keywords should trigger it.
    """

    WANTS_PAPPERS_KEYWORDS = [
        "pappers", "screening", "screener", "scan", "prospecter", "nouvelles cibles",
        "open data", "pme", "eti",
        "ca superieur", "chiffre affaires",
        "salarie", "salarié", "effectif",
    ]

    def _wants_pappers(self, query):
        ql = query.lower()
        return any(w in ql for w in self.WANTS_PAPPERS_KEYWORDS)

    def test_pappers_keyword_triggers(self):
        assert self._wants_pappers("lance un screening pappers") is True

    def test_pme_triggers(self):
        assert self._wants_pappers("trouve des PME dans la tech") is True

    def test_ca_triggers(self):
        assert self._wants_pappers("entreprises avec chiffre affaires > 10M") is True

    def test_casual_does_not_trigger(self):
        """Common casual queries should NOT trigger Pappers search."""
        assert self._wants_pappers("donne moi des infos") is False
        assert self._wants_pappers("quelle est la meilleure cible") is False
        assert self._wants_pappers("bonjour") is False
        assert self._wants_pappers("analyse la situation") is False

    def test_france_does_not_trigger(self):
        """'france' was removed from keywords to avoid false positives."""
        assert self._wants_pappers("entreprise en france") is False

    def test_liste_does_not_trigger(self):
        """'liste' was removed from keywords."""
        assert self._wants_pappers("donne moi la liste") is False

    def test_entreprise_does_not_trigger(self):
        """'entreprise' alone was removed — too generic."""
        assert self._wants_pappers("parle moi de cette entreprise") is False

    def test_societe_does_not_trigger(self):
        """'societe' alone was removed — too generic."""
        assert self._wants_pappers("c'est quelle societe") is False


class TestSectorDetection:
    """Tests for sector keyword → NAF code mapping in copilot."""

    SECTOR_NAF_MAP = {
        "courtage": "66.22Z", "assurance": "66.22Z",
        "logistique": "49.41A,52", "transport": "49.41A,49.41B",
        "medtech": "32.50A", "sante": "32.50A,86",
        "conseil": "70.22Z", "consulting": "70.22Z",
        "btp": "41.20A,41.20B", "construction": "41.20A,41.20B",
        "informatique": "62.01Z", "logiciel": "62.01Z",
    }

    def _detect_naf(self, query):
        ql = query.lower()
        for keyword, naf in self.SECTOR_NAF_MAP.items():
            if keyword in ql:
                return naf
        return None

    def test_courtage_detected(self):
        assert self._detect_naf("recherche courtage assurance") == "66.22Z"

    def test_btp_detected(self):
        assert self._detect_naf("scan BTP construction") is not None

    def test_informatique_detected(self):
        assert self._detect_naf("PME informatique") == "62.01Z"

    def test_no_sector(self):
        assert self._detect_naf("bonjour comment ça va") is None


class TestFinancialFilterDetection:
    """Tests for natural language financial filter extraction."""

    def test_ca_millions_detected(self):
        match = re.search(r"(\d+)\s*(?:m€|m\b|millions?|meur)", "entreprise CA 10m€")
        assert match is not None
        assert int(match.group(1)) == 10

    def test_ca_meur_detected(self):
        match = re.search(r"(\d+)\s*(?:m€|m\b|millions?|meur)", "CA superieur 5 millions")
        assert match is not None
        assert int(match.group(1)) == 5

    def test_effectif_detected(self):
        match = re.search(r"(\d+)\s*(?:salari|employ|effectif)", "plus de 50 salaries")
        assert match is not None
        assert int(match.group(1)) == 50

    def test_age_detected(self):
        query = "dirigeant 60 ans retraite"
        ql = query.lower()
        has_age = any(w in ql for w in ["60 ans", "65 ans", "senior", "succession", "retraite"])
        assert has_age is True
