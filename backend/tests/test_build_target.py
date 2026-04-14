"""
EdRCF 6.0 — build_target Tests
Tests for the target construction pipeline in pappers_loader.py.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pappers_loader import (
    build_target,
    map_sector,
    map_region,
    map_structure,
    format_revenue,
    compute_ebitda_range,
    build_analysis,
    build_risks,
)


class TestMapSector:
    """Tests for NAF code → sector mapping."""

    def test_courtage(self):
        assert map_sector("66.22Z") == "Courtage d'assurance"

    def test_industrial_tech(self):
        assert map_sector("62.01Z") == "Industrial Tech / TIC"
        assert map_sector("25.62A") == "Industrial Tech / TIC"

    def test_logistique(self):
        assert map_sector("49.41A") == "Logistique / Transport"

    def test_btp(self):
        assert map_sector("41.20A") == "BTP / Construction"

    def test_medtech(self):
        assert map_sector("32.50A") == "MedTech / Sante"

    def test_agroalimentaire(self):
        assert map_sector("10.11Z") == "Agroalimentaire"

    def test_energie(self):
        assert map_sector("35.11Z") == "Energie / CleanTech"

    def test_fallback_services_b2b(self):
        assert map_sector("99.99Z") == "Services B2B"

    def test_none_returns_services_b2b(self):
        assert map_sector(None) == "Services B2B"
        assert map_sector("") == "Services B2B"

    def test_libelle_fallback(self):
        assert map_sector("99.99Z", "transport de marchandises") == "Logistique / Transport"
        assert map_sector("99.99Z", "conseil en management") == "Services B2B"


class TestMapRegion:
    """Tests for postal code → region mapping."""

    def test_paris(self):
        assert map_region("75001") == "Ile-de-France"

    def test_lyon(self):
        assert map_region("69001") == "Auvergne-Rhone-Alpes"

    def test_bordeaux(self):
        assert map_region("33000") == "Nouvelle-Aquitaine"

    def test_unknown(self):
        assert map_region("97100") == "France"

    def test_none(self):
        assert map_region(None) == "France"
        assert map_region("") == "France"


class TestMapStructure:
    """Tests for forme_juridique → structure mapping."""

    def test_sas(self):
        assert map_structure("SAS") == "Familiale"

    def test_sarl(self):
        assert map_structure("SARL") == "Familiale"

    def test_sa_directoire(self):
        assert map_structure("SA a directoire") == "Groupe cote"

    def test_none(self):
        assert map_structure(None) == "Familiale"
        assert map_structure("") == "Familiale"


class TestFormatRevenue:
    """Tests for revenue formatting."""

    def test_millions(self):
        assert format_revenue(25_000_000) == "25.0M EUR"

    def test_thousands(self):
        assert format_revenue(500_000) == "500K EUR"

    def test_small(self):
        assert format_revenue(500) == "500 EUR"

    def test_zero(self):
        assert format_revenue(0) == "N/A"

    def test_none(self):
        assert format_revenue(None) == "N/A"

    def test_negative(self):
        assert format_revenue(-100) == "N/A"


class TestComputeEbitdaRange:
    """Tests for EBITDA range categorization."""

    def test_under_3m(self):
        assert compute_ebitda_range(2_000_000) == "< 3M"

    def test_3_to_10m(self):
        assert compute_ebitda_range(5_000_000) == "3-10M"

    def test_10_to_30m(self):
        assert compute_ebitda_range(15_000_000) == "10-30M"

    def test_over_30m(self):
        assert compute_ebitda_range(50_000_000) == "> 30M"

    def test_zero(self):
        assert compute_ebitda_range(0) == "< 3M"

    def test_none(self):
        assert compute_ebitda_range(None) == "< 3M"


class TestBuildTarget:
    """Tests for the full build_target pipeline."""

    def test_complete_data(self, sample_company_info):
        target = build_target(idx=1, company_info=sample_company_info, search_info={})

        assert target["id"] == "edrcf-001"
        assert target["siren"] == "123456789"
        assert target["name"] == "ACME INDUSTRIES SAS"
        assert target["sector"] == "Industrial Tech / TIC"
        assert target["region"] == "Ile-de-France"
        assert target["city"] == "PARIS"
        assert target["structure"] == "Familiale"
        assert target["statut_activite"] == "En activite"

        # Dirigeants
        assert len(target["dirigeants"]) >= 1
        assert target["dirigeants"][0]["name"] == "Jean DUPONT"
        assert target["dirigeants"][0]["age"] == 63

        # Financials
        assert target["financials"]["revenue"] == "25.0M EUR"
        assert "%" in target["financials"]["revenue_growth"]

        # Signals
        assert len(target["active_signals"]) > 0

        # Required nested dicts
        assert "analysis" in target
        assert "type" in target["analysis"]
        assert "window" in target["analysis"]
        assert "narrative" in target["analysis"]

        assert "activation" in target
        assert "deciders" in target["activation"]
        assert "approach" in target["activation"]

        assert "risks" in target
        assert "falsePositive" in target["risks"]
        assert "uncertainties" in target["risks"]

        assert "group" in target
        assert "relationship" in target

    def test_minimal_data_no_crash(self, minimal_company_info):
        """build_target should not crash with minimal data."""
        target = build_target(idx=99, company_info=minimal_company_info, search_info={})

        assert target["id"] == "edrcf-099"
        assert target["siren"] == "987654321"
        assert target["name"] == "PETITE SARL"
        assert target["financials"]["revenue"] == "N/A"
        assert len(target["active_signals"]) > 0  # at least fallback signal

    def test_holding_detected(self, holding_company_info):
        target = build_target(idx=5, company_info=holding_company_info, search_info={})
        assert target["group"]["is_holding"] is True
        assert "holding_creation" in target["active_signals"]

    def test_procedure_collective(self, company_with_procedures):
        target = build_target(idx=10, company_info=company_with_procedures, search_info={})
        assert target["group"]["procedure_collective_en_cours"] is True
        assert "procedure_collective" in target["active_signals"]

    def test_subsidiaries_are_strings(self, sample_company_info):
        """Subsidiaries must be string[] for frontend compatibility."""
        target = build_target(idx=1, company_info=sample_company_info, search_info={})
        subs = target["group"]["subsidiaries"]
        for s in subs:
            assert isinstance(s, str), f"Subsidiary should be str, got {type(s)}: {s}"


class TestBuildAnalysis:
    """Tests for analysis field generation."""

    def test_transmission_type(self):
        signals = ["founder_60_no_successor", "holding_creation"]
        result = build_analysis(signals, "Services B2B", {}, [])
        assert result["type"] == "Transmission / LBO"

    def test_cession_type(self):
        signals = ["founder_60_no_successor"]
        result = build_analysis(signals, "Services B2B", {}, [])
        assert result["type"] == "Cession / Consolidation"

    def test_monitoring_type(self):
        signals = ["press_regional"]
        result = build_analysis(signals, "Services B2B", {}, [])
        assert result["type"] == "Monitoring"

    def test_window_short(self):
        signals = ["a", "b", "c", "d"]  # 4+ signals
        result = build_analysis(signals, "Services B2B", {}, [])
        assert result["window"] == "6-12 mois"

    def test_window_medium(self):
        signals = ["a", "b"]
        result = build_analysis(signals, "Services B2B", {}, [])
        assert result["window"] == "12-18 mois"

    def test_window_long(self):
        signals = ["a"]
        result = build_analysis(signals, "Services B2B", {}, [])
        assert result["window"] == "18+ mois"


class TestBuildRisks:
    """Tests for risk assessment generation."""

    def test_low_false_positive(self):
        risks = build_risks(["a", "b", "c", "d"])
        assert "Faible" in risks["falsePositive"]

    def test_medium_false_positive(self):
        risks = build_risks(["a", "b"])
        assert "Moyen" in risks["falsePositive"]

    def test_high_false_positive(self):
        risks = build_risks(["a"])
        assert "Eleve" in risks["falsePositive"]
