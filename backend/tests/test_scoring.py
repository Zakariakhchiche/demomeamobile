"""
EdRCF 6.0 — Scoring Engine Tests
Tests for calculate_score, enrich_target, and priority levels.
"""

import sys
import os
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import calculate_score, enrich_target
from demo_data import SIGNAL_CATALOG, DEFAULT_SCORING_WEIGHTS


class TestCalculateScore:
    """Tests for the scoring engine."""

    def _make_company(self, signal_ids):
        return {"active_signals": signal_ids}

    def test_empty_signals_gives_zero(self):
        score, priority, dims, signals = calculate_score(self._make_company([]))
        assert score == 0
        assert priority == "Veille Passive"
        assert len(signals) == 0

    def test_unknown_signal_is_ignored(self):
        score, priority, dims, signals = calculate_score(
            self._make_company(["nonexistent_signal_xyz"])
        )
        assert score == 0
        assert len(signals) == 0

    def test_single_high_signal(self):
        score, priority, dims, signals = calculate_score(
            self._make_company(["holding_creation"])
        )
        # holding_creation = 20 pts in signaux_patrimoniaux
        assert score == 20
        assert len(signals) == 1
        assert signals[0]["id"] == "holding_creation"

    def test_dimension_capping(self):
        """Scores within a dimension should not exceed the max."""
        # signaux_patrimoniaux max = 30
        # holding_creation(20) + share_sale_by_director(18) + big4_audit(12) = 50, capped at 30
        score, priority, dims, signals = calculate_score(
            self._make_company(["holding_creation", "share_sale_by_director", "big4_audit"])
        )
        assert dims["signaux_patrimoniaux"]["score"] == 30  # capped
        assert dims["signaux_patrimoniaux"]["raw"] == 50  # uncapped

    def test_multiple_dimensions_add_up(self):
        signals_ids = [
            "founder_60_no_successor",  # maturite_dirigeant: 15
            "holding_creation",          # signaux_patrimoniaux: 20
            "ca_growth_2years",          # dynamique_financiere: 8
        ]
        score, priority, dims, signals = calculate_score(self._make_company(signals_ids))
        expected = 15 + 20 + 8
        assert score == expected

    def test_priority_action_prioritaire(self):
        """Score >= 65 should be Action Prioritaire."""
        # Stack enough signals to reach 65+
        high_signals = [
            "holding_creation",        # patrimoine: 20
            "share_sale_by_director",  # patrimoine: 18 (capped at 30 total)
            "director_withdrawal",     # maturite: 20
            "founder_60_no_successor", # maturite: 15 (capped at 30 total)
            "lbo_4_years",             # financiere: 12
            "daf_pe_recruitment",      # rh: 18
        ]
        score, priority, _, _ = calculate_score(self._make_company(high_signals))
        # patrimoine: 30 (capped) + maturite: 30 (capped) + financiere: 12 + rh: 18 = 90
        assert score >= 65
        assert priority == "Action Prioritaire"

    def test_priority_qualification(self):
        """Score >= 45 and < 65 should be Qualification."""
        signals_ids = [
            "founder_60_no_successor",  # maturite: 15
            "holding_creation",          # patrimoine: 20
            "ca_growth_2years",          # financiere: 8
            "cofounder_departure",       # rh: 10
        ]
        score, priority, _, _ = calculate_score(self._make_company(signals_ids))
        # 15 + 20 + 8 + 10 = 53
        assert 45 <= score < 65
        assert priority == "Qualification"

    def test_priority_monitoring(self):
        """Score >= 25 and < 45 should be Monitoring."""
        signals_ids = [
            "ca_growth_2years",      # financiere: 8
            "new_establishment",     # financiere: 6
            "sector_consolidation",  # consolidation: 8
            "press_regional",        # consolidation: 5
        ]
        score, priority, _, _ = calculate_score(self._make_company(signals_ids))
        # 8 + 6 + 8 + 5 = 27
        assert 25 <= score < 45
        assert priority == "Monitoring"

    def test_priority_veille_passive(self):
        """Score < 25 should be Veille Passive."""
        signals_ids = ["press_regional"]  # 5 pts
        score, priority, _, _ = calculate_score(self._make_company(signals_ids))
        assert score < 25
        assert priority == "Veille Passive"

    def test_score_is_rounded(self):
        score, _, _, _ = calculate_score(self._make_company(["press_regional"]))
        assert score == round(score, 1)

    def test_custom_weights(self):
        """Custom weights override default dimensions."""
        custom = copy.deepcopy(DEFAULT_SCORING_WEIGHTS)
        custom["signaux_patrimoniaux"]["max"] = 10  # Lower cap
        score, _, dims, _ = calculate_score(
            self._make_company(["holding_creation"]),  # 20 pts
            weights=custom,
        )
        assert dims["signaux_patrimoniaux"]["score"] == 10  # capped to custom max
        assert score == 10


class TestEnrichTarget:
    """Tests for enrich_target function."""

    def test_enriches_with_scoring_fields(self):
        raw = {
            "name": "Test Co",
            "active_signals": ["ca_growth_2years"],
            "sector": "Services B2B",
        }
        enriched = enrich_target(raw)
        assert "globalScore" in enriched
        assert "priorityLevel" in enriched
        assert "scoring_details" in enriched
        assert "topSignals" in enriched

    def test_preserves_original_fields(self):
        raw = {
            "name": "Test Co",
            "siren": "123456789",
            "active_signals": [],
        }
        enriched = enrich_target(raw)
        assert enriched["name"] == "Test Co"
        assert enriched["siren"] == "123456789"
