from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
