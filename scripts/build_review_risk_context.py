from __future__ import annotations

import re

from common import (
    RATE_SHOP_SNAPSHOT_PATH,
    REPORT_DIR,
    REVIEW_RISK_CONTEXT_MANIFEST_PATH,
    REVIEW_RISK_CONTEXT_PATH,
    ensure_dirs,
    read_csv_rows,
    utc_now_iso,
    write_csv,
    write_json,
)
from policy_engine import clamp


REVIEW_RISK_REPORT = REPORT_DIR / "review-risk-context.md"

FIELDNAMES = [
    "captured_at",
    "failure_category",
    "public_review_theme",
    "baseline_review_risk_prior",
    "observed_negative_mentions",
    "observed_positive_mentions",
    "source_signal_count",
    "observed_context_count",
    "sample_seed_context_count",
    "review_context_confidence",
    "provenance",
    "public_context_use",
    "review_context_note",
]

THEME_PRIORS = {
    "room_readiness_delay": ("rooms;service;arrival", 0.74),
    "room_assignment_expectation_gap": ("rooms;expectations;service", 0.68),
    "housekeeping_miss": ("rooms;cleanliness;service", 0.72),
    "maintenance_issue": ("rooms;maintenance;amenities", 0.69),
    "noise_disruption": ("rooms;sleep;comfort", 0.62),
    "billing_or_fee_dispute": ("fees;billing;service", 0.58),
    "f_and_b_service_lapse": ("food;restaurant;service", 0.6),
    "rooftop_pool_access_issue": ("pool;rooftop;amenities", 0.6),
    "spa_wellness_service_issue": ("spa;wellness;amenities", 0.64),
    "valet_or_parking_delay": ("parking;valet;arrival", 0.56),
}


def parse_review_breakdown(summary: str) -> list[dict[str, int | str]]:
    output = []
    for item in summary.split(";"):
        if not item.strip():
            continue
        name = item.split(":", 1)[0].strip().lower()
        negative = 0
        positive = 0
        negative_match = re.search(r"negative=(\d+)", item)
        positive_match = re.search(r"positive=(\d+)", item)
        if negative_match:
            negative = int(negative_match.group(1))
        if positive_match:
            positive = int(positive_match.group(1))
        output.append({"theme": name, "negative": negative, "positive": positive})
    return output


def build_rows() -> list[dict[str, object]]:
    ensure_dirs()
    snapshot_rows = []
    if RATE_SHOP_SNAPSHOT_PATH.exists():
        _, snapshot_rows = read_csv_rows(RATE_SHOP_SNAPSHOT_PATH)

    captured_at = utc_now_iso()
    rows: list[dict[str, object]] = []
    parsed = []
    observed_context_count = 0
    sample_seed_context_count = 0
    for row in snapshot_rows:
        provenance = row.get("provenance", "")
        if provenance == "observed_public_market_context":
            observed_context_count += 1
        if provenance == "sample_seed_public_rate_shape":
            sample_seed_context_count += 1
        parsed.extend(parse_review_breakdown(row.get("reviews_breakdown_summary", "")))

    for failure_category, (themes, baseline_prior) in THEME_PRIORS.items():
        theme_tokens = {theme.strip() for theme in themes.split(";")}
        matches = [item for item in parsed if str(item["theme"]) in theme_tokens]
        negative = sum(int(item["negative"]) for item in matches)
        positive = sum(int(item["positive"]) for item in matches)
        signal_count = len(matches)
        observed_strength = negative / max(negative + positive, 1)
        adjusted_prior = baseline_prior
        if negative + positive > 0:
            adjusted_prior = clamp(baseline_prior * 0.72 + observed_strength * 0.28, 0.35, 0.92)
        confidence = 0.18
        if observed_context_count:
            confidence += min(observed_context_count, 12) * 0.02
        if signal_count:
            confidence += min(signal_count, 12) * 0.01
        if sample_seed_context_count and not observed_context_count:
            confidence = min(confidence, 0.28)
        rows.append(
            {
                "captured_at": captured_at,
                "failure_category": failure_category,
                "public_review_theme": themes,
                "baseline_review_risk_prior": round(adjusted_prior, 3),
                "observed_negative_mentions": negative,
                "observed_positive_mentions": positive,
                "source_signal_count": signal_count,
                "observed_context_count": observed_context_count,
                "sample_seed_context_count": sample_seed_context_count,
                "review_context_confidence": round(clamp(confidence, 0, 0.85), 3),
                "provenance": "observed_public_review_context" if observed_context_count else "sample_seed_review_taxonomy_prior",
                "public_context_use": "issue-level review-risk prior for service recovery recommendations",
                "review_context_note": "Public review context or taxonomy prior only; not post-recovery satisfaction or actual Proper Hotels review outcomes.",
            }
        )
    return rows


def render_report(rows: list[dict[str, object]]) -> str:
    highest = sorted(rows, key=lambda row: float(row["baseline_review_risk_prior"]), reverse=True)[:5]
    observed = int(rows[0]["observed_context_count"]) if rows else 0
    sample = int(rows[0]["sample_seed_context_count"]) if rows else 0
    lines = [
        "# Review Risk Context",
        "",
        "This layer maps public review themes or review-taxonomy priors to service-failure risk.",
        "",
        "It is not actual post-recovery satisfaction, guest lifetime value, or Proper Hotels internal reputation monitoring.",
        "",
        "## Source Summary",
        "",
        f"- Observed public context count across categories: `{observed}`",
        f"- Sample-seed context count across categories: `{sample}`",
        "",
        "## Highest Review-Risk Priors",
        "",
        "| Failure category | Prior | Themes |",
        "| --- | ---: | --- |",
    ]
    for row in highest:
        lines.append(f"| `{row['failure_category']}` | {row['baseline_review_risk_prior']} | {row['public_review_theme']} |")
    lines.extend(
        [
            "",
            "## Decision Use",
            "",
            "- Calibrate issue-level review risk rather than treating every issue type the same.",
            "- Increase recovery need when a failure category has high reputation sensitivity.",
            "- Reduce confidence when only sample-seed context is available.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    rows = build_rows()
    write_csv(REVIEW_RISK_CONTEXT_PATH, FIELDNAMES, rows)
    write_json(
        REVIEW_RISK_CONTEXT_MANIFEST_PATH,
        {
            "generated_at": utc_now_iso(),
            "source_family": "public_review_risk_context",
            "review_risk_context_path": "data/sample/external_context/review_risk_context.csv",
            "row_count": len(rows),
            "fields": FIELDNAMES,
            "public_safety_note": "Review-risk context is public or sample-seed taxonomy context, not internal guest outcomes.",
        },
    )
    REVIEW_RISK_REPORT.write_text(render_report(rows), encoding="utf-8")
    print(f"Wrote review-risk context: {REVIEW_RISK_CONTEXT_PATH.relative_to(REVIEW_RISK_CONTEXT_PATH.parents[2])}")
    print(f"Wrote review-risk report: {REVIEW_RISK_REPORT.relative_to(REVIEW_RISK_REPORT.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
