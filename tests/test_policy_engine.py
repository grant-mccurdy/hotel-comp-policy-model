from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from policy_config import comp_catalog, load_policy_config  # noqa: E402
from policy_engine import recommend_comp, recovery_need_score, service_recovery_floor_score  # noqa: E402


class PolicyEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy_config()
        self.catalog = comp_catalog(self.policy)
        self.stay = {
            "guest_tier": "loyalty_guest",
            "traveler_segment": "coastal_weekend",
            "stay_value": 2800,
            "estimated_lifetime_value": 14000,
            "guest_value_score": 0.74,
            "repeat_comp_review_risk": 0.04,
            "nightly_rate": 700,
        }
        self.failure = {
            "failure_category": "room_readiness_delay",
            "failure_type": "outcome",
            "severity": 4,
            "hotel_responsibility_score": 0.9,
            "reported_in_stay": True,
            "resolution_delay_minutes": 95,
            "complaint_sentiment_intensity": 0.76,
            "review_risk_score": 0.8,
            "occupancy_pressure": 0.72,
            "public_rate_pressure_index": 0.5,
            "rate_context_confidence": 0,
            "property_context_confidence": 0.88,
            "rooftop_f_and_b_fit_modifier": 1.22,
            "spa_wellness_fit_modifier": 1.18,
            "lobby_lounge_fit_modifier": 1.12,
            "parking_fee_fit_modifier": 1.04,
            "late_checkout_fit_modifier": 1.04,
            "room_upgrade_fit_modifier": 1.08,
        }

    def test_recommendation_is_deterministic_and_bounded(self) -> None:
        first = recommend_comp(self.stay, self.failure, self.catalog, self.policy)
        second = recommend_comp(self.stay, self.failure, self.catalog, self.policy)
        self.assertEqual(first, second)
        self.assertLessEqual(first.internal_cost_low, first.estimated_internal_cost)
        self.assertLessEqual(first.estimated_internal_cost, first.internal_cost_high)
        self.assertGreaterEqual(first.recommendation_stability, 0)
        self.assertLessEqual(first.recommendation_stability, 1)
        self.assertIn(first.decision_confidence, {"low", "moderate", "high"})
        self.assertEqual(first.policy_id, self.policy["policy_id"])
        self.assertEqual(first.policy_version, self.policy["policy_version"])
        self.assertEqual(len(first.alternatives), 2)

    def test_severity_and_responsibility_raise_recovery_need(self) -> None:
        low = dict(self.failure, severity=2, hotel_responsibility_score=0.35, review_risk_score=0.3)
        high = dict(self.failure, severity=5, hotel_responsibility_score=0.95, review_risk_score=0.9)
        self.assertGreater(
            recovery_need_score(self.stay, high, self.policy),
            recovery_need_score(self.stay, low, self.policy),
        )
        self.assertGreaterEqual(
            recommend_comp(self.stay, high, self.catalog, self.policy).recommended_tier,
            recommend_comp(self.stay, low, self.catalog, self.policy).recommended_tier,
        )

    def test_high_rate_pressure_can_change_room_recovery(self) -> None:
        base = dict(
            self.failure,
            failure_category="room_assignment_expectation_gap",
            occupancy_pressure=0.64,
            public_rate_pressure_index=0.25,
            high_demand_rate_flag=False,
            upgrade_opportunity_cost_proxy=70,
            refund_cost_pressure=0.95,
            rate_context_confidence=0.82,
        )
        high = dict(
            base,
            occupancy_pressure=0.84,
            public_rate_pressure_index=0.92,
            high_demand_rate_flag=True,
            upgrade_opportunity_cost_proxy=290,
            refund_cost_pressure=1.28,
        )
        low_result = recommend_comp(self.stay, base, self.catalog, self.policy)
        high_result = recommend_comp(self.stay, high, self.catalog, self.policy)
        self.assertEqual(low_result.comp_code, "room_upgrade")
        self.assertNotEqual(high_result.comp_code, "room_upgrade")
        self.assertIn("public_rate_pressure_changed_recovery", high_result.reason_codes)
        self.assertTrue(any("Public rate pressure" in item for item in high_result.counterfactuals))

    def test_repeat_comp_pattern_routes_to_review(self) -> None:
        stay = dict(self.stay, repeat_comp_review_risk=0.8)
        result = recommend_comp(stay, self.failure, self.catalog, self.policy)
        self.assertTrue(result.manager_review_flag)
        self.assertIn("repeat_comp_pattern_review_needed", result.reason_codes)

    def test_service_recovery_floor_is_independent_of_guest_value(self) -> None:
        low_value = dict(self.stay, guest_value_score=0.0)
        high_value = dict(self.stay, guest_value_score=1.0)
        self.assertEqual(
            service_recovery_floor_score(low_value, self.failure, self.policy),
            service_recovery_floor_score(high_value, self.failure, self.policy),
        )
        self.assertGreaterEqual(
            recovery_need_score(high_value, self.failure, self.policy),
            service_recovery_floor_score(low_value, self.failure, self.policy),
        )

    def test_lost_recovery_window_does_not_reduce_need_or_offer_room_gestures(self) -> None:
        in_stay = dict(self.failure, reported_in_stay=True)
        after_checkout = dict(self.failure, reported_in_stay=False)
        self.assertGreaterEqual(
            recovery_need_score(self.stay, after_checkout, self.policy),
            recovery_need_score(self.stay, in_stay, self.policy),
        )
        result = recommend_comp(self.stay, after_checkout, self.catalog, self.policy)
        self.assertNotIn(result.comp_code, {"room_upgrade", "late_checkout"})

    def test_low_source_match_forces_low_confidence_and_review(self) -> None:
        stay = dict(self.stay, data_quality_flags="low_reservation_match_confidence;severity_inferred")
        result = recommend_comp(stay, self.failure, self.catalog, self.policy)
        self.assertEqual(result.decision_confidence, "low")
        self.assertTrue(result.manager_review_flag)

    def test_sample_seed_rate_context_cannot_receive_high_confidence_when_causal(self) -> None:
        failure = dict(
            self.failure,
            failure_category="room_assignment_expectation_gap",
            occupancy_pressure=0.84,
            public_rate_pressure_index=0.92,
            high_demand_rate_flag=True,
            upgrade_opportunity_cost_proxy=290,
            refund_cost_pressure=1.28,
            rate_context_confidence=0.82,
            pricing_provenance="sample_seed_public_rate_shape",
        )
        result = recommend_comp(self.stay, failure, self.catalog, self.policy)
        self.assertIn("public_rate_pressure_changed_recovery", result.reason_codes)
        self.assertNotEqual(result.decision_confidence, "high")

    def test_randomized_valid_scenarios_remain_in_domain(self) -> None:
        rng = random.Random(20260710)
        categories = list(self.policy["failure_base_risk"])
        tiers = ["new_guest", "returning_guest", "loyalty_guest", "vip_guest", "event_or_suite_guest"]
        codes = {row["comp_code"] for row in self.catalog}
        for _ in range(250):
            stay = dict(
                self.stay,
                guest_tier=rng.choice(tiers),
                stay_value=rng.uniform(300, 10000),
                estimated_lifetime_value=rng.uniform(500, 80000),
                guest_value_score=rng.random(),
                repeat_comp_review_risk=rng.random(),
                nightly_rate=rng.uniform(300, 2500),
            )
            failure = dict(
                self.failure,
                failure_category=rng.choice(categories),
                severity=rng.randint(1, 5),
                hotel_responsibility_score=rng.random(),
                reported_in_stay=rng.choice([True, False]),
                resolution_delay_minutes=rng.randint(0, 720),
                complaint_sentiment_intensity=rng.random(),
                review_risk_score=rng.random(),
                occupancy_pressure=rng.random(),
                public_rate_pressure_index=rng.random(),
            )
            result = recommend_comp(stay, failure, self.catalog, self.policy)
            self.assertIn(result.comp_code, codes)
            self.assertGreaterEqual(result.recommended_value, 0)
            self.assertLessEqual(result.recovery_need_score, 100)
            self.assertGreaterEqual(result.brand_impact_risk, 0)
            self.assertLessEqual(result.brand_impact_risk, 1)


if __name__ == "__main__":
    unittest.main()
