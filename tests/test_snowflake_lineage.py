from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from common import POLICY_DECISION_SUMMARY_PATH, RATE_SHOP_SNAPSHOT_PATH  # noqa: E402
from load_snowflake_warehouse import coerce_value, mart_type_lookup, table_ddl  # noqa: E402


class SnowflakeLineageTests(unittest.TestCase):
    def test_offline_lineage_does_not_require_cloud_packages(self) -> None:
        result = subprocess.run(
            [sys.executable, "-S", "scripts/load_snowflake_warehouse.py", "lineage"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Wrote Snowflake lineage report", result.stdout)

    def test_raw_tables_preserve_text_while_marts_use_contract_types(self) -> None:
        raw_ddl = table_ddl("RAW", "STG_RATE_SHOP_SNAPSHOTS", RATE_SHOP_SNAPSHOT_PATH)
        mart_ddl = table_ddl("MARTS", "MART_POLICY_DECISION_SUMMARY", POLICY_DECISION_SUMMARY_PATH)
        self.assertIn("CHECK_IN_DATE VARCHAR", raw_ddl)
        self.assertIn("SELECTED_FOR_PILOT BOOLEAN", mart_ddl)
        self.assertIn("INTERNAL_COST_MID NUMBER(18,6)", mart_ddl)

    def test_mart_type_contract_has_expected_decision_types(self) -> None:
        lookup = mart_type_lookup()
        self.assertEqual(lookup["SELECTED_FOR_PILOT"], "BOOLEAN")
        self.assertEqual(lookup["JOINT_GUARDRAIL_PASS_PROBABILITY"], "NUMBER(18,6)")
        self.assertEqual(coerce_value("true", "BOOLEAN"), True)
        self.assertIsNone(coerce_value("", "NUMBER(18,6)"))


if __name__ == "__main__":
    unittest.main()
