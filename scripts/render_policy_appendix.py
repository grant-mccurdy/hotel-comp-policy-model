#!/usr/bin/env python3
"""Render the policy-selection technical appendix from a stable directory."""

from __future__ import annotations

import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_SOURCE = PROJECT_ROOT / "reports" / "policy-selection-technical-appendix.qmd"
HTML_OUTPUT = PROJECT_ROOT / "reports" / "policy-selection-technical-appendix.html"


def normalize_generated_html(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def main() -> int:
    subprocess.run(
        [
            "quarto",
            "render",
            str(REPORT_SOURCE.relative_to(PROJECT_ROOT)),
            "--to",
            "html",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    normalize_generated_html(HTML_OUTPUT)
    print(f"Rendered technical appendix: {HTML_OUTPUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

