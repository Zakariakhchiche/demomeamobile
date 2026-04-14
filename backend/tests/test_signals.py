"""
EdRCF 6.0 — Signal Detection Tests
Tests for detect_signals function in pappers_loader.py.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pappers_loader import detect_signals
from demo_data import SIGNAL_CATALOG


class TestDirectorAgeSignals:
    """Tests for director age-based signal detection."""

    def test_director_over_60_triggers_founder_signal(self, sample_company_info):
        signals = detect_signals(sample_company_info)
        assert "founder_60_no_successor" in signals

    def test_director_under_60_no_founder_signal(self, minimal_company_info):
        minimal_company_info["representants"] = [
            {"prenom": "Young", "nom": "CEO", "qualite": "President", "age": 45}
        ]
        signals = detect_signals(minimal_company_info)
        assert "founder_60_no_successor" not in signals

    def test_director_over_65_triggers_withdrawal(self, sample_company_info):
        sample_company_info["representants"] = [
            {"prenom": "Old", "nom": "BOSS", "qualite": "President", "age": 67}
        ]
        signals = detect_signals(sample_company_info)
        assert "director_withdrawal" in signals

    def test_age_from_date_de_naissance(self):
        """When age field is 0, compute from date_de_naissance."""
        info = {
            "siren": "111111111",
            "representants": [
                {
                    "prenom": "Test",
                    "nom": "DIR",
                    "qualite": "President",
                    "age": 0,
                    "date_de_naissance": "1958-01-15",
                }
            ],
        }
        signals = detect_signals(info)
        # Born 1958, current year ~2026 → age ~68 → should trigger both signals
        assert "founder_60_no_successor" in signals
        assert "director_withdrawal" in signals

    def test_non_leader_role_does_not_trigger(self):
        """Only leadership roles should trigger age signals."""
        info = {
            "siren": "222222222",
            "representants": [
                {"prenom": "Old", "nom": "WORKER", "qualite": "Commissaire aux comptes", "age": 70}
            ],
        }
        signals = detect_signals(info)
        assert "founder_60_no_successor" not in signals

    def test_search_age_filter_forces_founder_signal(self):
        """search_had_age_filter=True should force founder signal even without old directors."""
        info = {"siren": "333333333", "representants": []}
        signals = detect_signals(info, search_had_age_filter=True)
        assert "founder_60_no_successor" in signals


class TestMultiMandatsSignal:
    """Tests for dirigeant_multi_mandats signal."""

    def test_multi_mandats_detected(self, sample_company_info):
        # sample_company_info has a director with 2 autres_mandats
        signals = detect_signals(sample_company_info)
        assert "dirigeant_multi_mandats" in signals

    def test_single_mandat_not_detected(self):
        info = {
            "siren": "444444444",
            "representants": [
                {"prenom": "X", "nom": "Y", "qualite": "President", "age": 50, "autres_mandats": [{"siren": "1"}]}
            ],
        }
        signals = detect_signals(info)
        assert "dirigeant_multi_mandats" not in signals


class TestFinancialSignals:
    """Tests for financial growth signal detection."""

    def test_ca_growth_over_10pct(self, sample_company_info):
        # 25M vs 20M = 25% growth → should trigger
        signals = detect_signals(sample_company_info)
        assert "ca_growth_2years" in signals

    def test_no_growth_signal_when_declining(self):
        info = {
            "siren": "555555555",
            "finances": [
                {"chiffre_affaires": 5000000, "annee": 2024},
                {"chiffre_affaires": 8000000, "annee": 2023},
            ],
        }
        signals = detect_signals(info)
        assert "ca_growth_2years" not in signals

    def test_no_financial_data(self):
        info = {"siren": "666666666"}
        signals = detect_signals(info)
        assert "ca_growth_2years" not in signals


class TestEstablishmentSignals:
    """Tests for multiple establishments signal."""

    def test_multiple_etablissements(self, sample_company_info):
        signals = detect_signals(sample_company_info)
        assert "new_establishment" in signals

    def test_single_etablissement(self):
        info = {
            "siren": "777777777",
            "etablissements": [{"siret": "77777777700010"}],
        }
        signals = detect_signals(info)
        assert "new_establishment" not in signals


class TestSectorConsolidation:
    """Tests for sector consolidation signal."""

    def test_hot_sector_triggers_consolidation(self, sample_company_info):
        # Industrial Tech / TIC has heat=82 (>=70)
        signals = detect_signals(sample_company_info)
        assert "sector_consolidation" in signals

    def test_cold_sector_no_consolidation(self):
        info = {
            "siren": "888888888",
            "code_naf": "41.20A",  # BTP → heat=45 (<70)
            "libelle_code_naf": "Construction",
        }
        signals = detect_signals(info)
        assert "sector_consolidation" not in signals


class TestHoldingSignal:
    """Tests for holding detection signal."""

    def test_holding_by_name(self, holding_company_info):
        signals = detect_signals(holding_company_info)
        assert "holding_creation" in signals

    def test_holding_by_naf_code(self):
        info = {
            "siren": "999999999",
            "code_naf": "64.20Z",
            "libelle_code_naf": "Activites des societes holding",
        }
        signals = detect_signals(info)
        assert "holding_creation" in signals


class TestProcedureCollective:
    """Tests for collective procedure signal."""

    def test_procedure_collective_detected(self, company_with_procedures):
        signals = detect_signals(company_with_procedures)
        assert "procedure_collective" in signals

    def test_no_procedure_no_signal(self, sample_company_info):
        signals = detect_signals(sample_company_info)
        assert "procedure_collective" not in signals


class TestBodaccSignals:
    """Tests for BODACC publication signal detection."""

    def test_bodacc_cession(self):
        info = {
            "siren": "111111111",
            "publications_bodacc": [
                {"type": "Vente", "description": "Cession de parts", "administration": ""}
            ],
        }
        signals = detect_signals(info)
        assert "bodacc_cession" in signals

    def test_bodacc_capital_change(self):
        info = {
            "siren": "222222222",
            "publications_bodacc": [
                {"type": "Modification", "description": "Augmentation de capital", "administration": ""}
            ],
        }
        signals = detect_signals(info)
        assert "bodacc_capital_change" in signals

    def test_bodacc_dissolution(self):
        info = {
            "siren": "333333333",
            "publications_bodacc": [
                {"type": "Radiation", "description": "Dissolution de la societe", "administration": ""}
            ],
        }
        signals = detect_signals(info)
        assert "bodacc_dissolution" in signals


class TestFallbackSignal:
    """Tests for fallback when no signals detected."""

    def test_empty_company_gets_press_regional(self):
        info = {"siren": "000000000"}
        signals = detect_signals(info)
        assert "press_regional" in signals
        assert len(signals) >= 1

    def test_all_signals_are_valid(self, sample_company_info):
        """Every detected signal must exist in SIGNAL_CATALOG."""
        signals = detect_signals(sample_company_info)
        for s in signals:
            assert s in SIGNAL_CATALOG, f"Signal '{s}' not in catalog"


class TestInfogreffeSignals:
    """Tests for Infogreffe actes signal detection."""

    def test_infogreffe_dirigeant_nomination(self):
        info = {
            "siren": "444444444",
            "infogreffe_actes": [
                {"type": "Nomination du president", "date": "2024-01-15"}
            ],
        }
        signals = detect_signals(info)
        assert "infogreffe_nouveau_dirigeant" in signals

    def test_infogreffe_fusion(self):
        info = {
            "siren": "555555555",
            "infogreffe_actes": [
                {"type": "Fusion absorption", "date": "2024-03-01"}
            ],
        }
        signals = detect_signals(info)
        assert "infogreffe_fusion_absorption" in signals


class TestNewsSignals:
    """Tests for Google News article signal detection."""

    def test_presse_cession(self):
        info = {
            "siren": "666666666",
            "news_articles": [
                {"title": "Entreprise X cède ses parts à un investisseur"}
            ],
        }
        signals = detect_signals(info)
        assert "presse_cession" in signals

    def test_presse_difficultes(self):
        info = {
            "siren": "777777777",
            "news_articles": [
                {"title": "Redressement judiciaire pour la societe Y"}
            ],
        }
        signals = detect_signals(info)
        assert "presse_difficultes" in signals
