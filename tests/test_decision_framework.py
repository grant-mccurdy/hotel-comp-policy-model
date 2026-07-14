from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_SOURCE = PROJECT_ROOT / "reports" / "hotel-comp-decision-framework.qmd"


class DecisionFrameworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = REPORT_SOURCE.read_text(encoding="utf-8")

    def test_report_leads_with_a_bounded_operating_recommendation(self) -> None:
        for text in (
            "The decision is not whether to comp less",
            "do not change comp policy from synthetic results",
            "Guest recovery first",
            "Cost second",
            "Real outcomes decide",
            "four weeks or 50 eligible recovery cases",
            "operational discovery target",
            "90-minute working session",
        ):
            self.assertIn(text, self.source)

    def test_report_computes_evidence_from_versioned_marts(self) -> None:
        self.assertIn("../data/marts/policy_uncertainty_summary.csv", self.source)
        self.assertIn("../data/marts/policy_decision_summary.csv", self.source)
        self.assertIn("../data/marts/comp_recommendations.csv", self.source)
        self.assertIn("joint_guardrail_pass_probability >= 0.80", self.source)
        self.assertNotIn("case_00019", self.source)

    def test_primary_report_is_a_document_not_an_application(self) -> None:
        self.assertEqual(self.source.count("```{r}"), 3)
        self.assertEqual(self.source.count("fig-policy-cost"), 1)
        self.assertEqual(self.source.count("kable(decision_path"), 1)
        self.assertNotIn("tabset", self.source.lower())
        self.assertNotIn("dashboard", self.source.lower())


if __name__ == "__main__":
    unittest.main()
