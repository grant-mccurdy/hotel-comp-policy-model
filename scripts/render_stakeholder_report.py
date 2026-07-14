#!/usr/bin/env python3
"""Render the Quarto stakeholder report from a stable working directory."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_SOURCE = REPORT_DIR / "hotel-comp-decision-framework.qmd"
HTML_OUTPUT = REPORT_DIR / "hotel-comp-decision-framework.html"
PDF_OUTPUT = REPORT_DIR / "hotel-comp-decision-framework.pdf"


def normalize_generated_html(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("html", "pdf", "all"),
        default="all",
        help="Output format to render.",
    )
    return parser.parse_args()


def render(output_format: str) -> None:
    output_name = HTML_OUTPUT.name if output_format == "html" else PDF_OUTPUT.name
    subprocess.run(
        [
            "quarto",
            "render",
            REPORT_SOURCE.name,
            "--to",
            output_format,
            "--output",
            output_name,
        ],
        cwd=REPORT_DIR,
        check=True,
    )
    if output_format == "html":
        normalize_generated_html(HTML_OUTPUT)
        shutil.copy2(HTML_OUTPUT, PROJECT_ROOT / "index.html")


def main() -> int:
    args = parse_args()
    formats = ("html", "pdf") if args.format == "all" else (args.format,)
    for output_format in formats:
        render(output_format)
    print(f"Rendered stakeholder report formats: {', '.join(formats)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
