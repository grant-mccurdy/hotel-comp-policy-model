from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_SOURCE = PROJECT_ROOT / "reports" / "hotel-comp-decision-framework.qmd"
README_PATH = PROJECT_ROOT / "README.md"
STATUS_PATH = PROJECT_ROOT / "PROJECT_STATUS.md"


class DecisionFrameworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = REPORT_SOURCE.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")
        cls.status = STATUS_PATH.read_text(encoding="utf-8")

    def test_report_has_a_focused_stakeholder_flow(self) -> None:
        required_text = (
            "The business task",
            "The proposed decision product",
            "minimum recovery obligation",
            "An illustrative recommendation",
            "How the real model would be chosen",
            "A focused first step",
            "90-minute data and policy workshop",
            "four weeks or 50 eligible cases",
            "workflow discovery, not proof of impact",
        )
        for text in required_text:
            self.assertIn(text, self.source)

    def test_report_computes_only_the_worked_example(self) -> None:
        self.assertIn("../data/marts/policy_decision_summary.csv", self.source)
        self.assertIn("../data/marts/policy_case_comparison.csv", self.source)
        self.assertNotIn("policy_uncertainty_summary.csv", self.source)
        self.assertNotIn("joint_guardrail_pass_probability", self.source)
        self.assertNotIn("case_00019", self.source)

    def test_primary_report_is_a_brief_not_an_application_or_model_report(self) -> None:
        self.assertEqual(self.source.count("```{r}"), 1)
        self.assertNotIn("fig-shadow-screen", self.source)
        self.assertNotIn("ggplot", self.source)
        self.assertNotIn("kable(", self.source)
        self.assertNotIn("tabset", self.source.lower())
        self.assertNotIn("dashboard", self.source.lower())

    def test_primary_report_excludes_supporting_implementation_topics(self) -> None:
        for text in (
            "Guardrailed recovery",
            "5,000",
            "Snowflake",
            "Cloudflare",
            "Workers AI",
            "D1",
            "RAG",
        ):
            self.assertNotIn(text, self.source)

    def test_report_links_to_the_public_synthetic_decision_desk(self) -> None:
        self.assertIn("Test the prototype", self.source)
        self.assertIn(
            "https://hotel-comp-decision-desk.grant-mccurdy.workers.dev/",
            self.source,
        )
        self.assertIn("Synthetic scenarios only", self.source)
        self.assertIn("Do not enter actual guest or reservation information", self.source)

    def test_report_exposes_the_three_primary_artifacts(self) -> None:
        self.assertIn("Executive brief PDF", self.source)
        self.assertIn("reports/hotel-comp-decision-framework.pdf", self.source)
        self.assertIn("Policy selection appendix", self.source)
        self.assertIn("reports/policy-selection-technical-appendix.html", self.source)
        self.assertIn("Open the Decision Desk", self.source)

    def test_repository_docs_preserve_the_deliverable_hierarchy(self) -> None:
        self.assertIn("The report is the primary deliverable", self.readme)
        self.assertIn("## Scope Control", self.readme)
        self.assertIn("Infrastructure expansion is out of scope", self.readme)
        self.assertIn("Everything else is supporting evidence", self.status)
        self.assertIn("## Scope Freeze", self.status)


if __name__ == "__main__":
    unittest.main()
