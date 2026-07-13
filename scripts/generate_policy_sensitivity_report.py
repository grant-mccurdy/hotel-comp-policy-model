from __future__ import annotations

from common import (
    POLICY_DECISION_SUMMARY_PATH,
    POLICY_UNCERTAINTY_SUMMARY_PATH,
    REPORT_DIR,
    ensure_dirs,
    read_csv_rows,
)
from policy_engine import as_float


REPORT_PATH = REPORT_DIR / "policy-sensitivity.md"


def money(value: object) -> str:
    return f"${as_float(value):,.0f}"


def render_report(
    summary_rows: list[dict[str, str]], uncertainty_rows: list[dict[str, str]]
) -> str:
    selected = next((row for row in summary_rows if row.get("selected_for_pilot") == "true"), None)
    uncertainty_by_policy = {row["policy_id"]: row for row in uncertainty_rows}
    lines = [
        "# Policy Comparison Assumption Stress Test",
        "",
        "This report tests whether the simulated policy decision remains credible when the case mix is resampled and uncertain cost/fit assumptions are varied. It does not validate guest outcomes, estimate causal effects, or project Proper Hotels savings.",
        "",
        "## Generated Shadow-Validation Decision",
        "",
        (
            selected["executive_recommendation"]
            if selected
            else "No candidate cleared the declared shadow-validation guardrails."
        ),
        "",
        "## Shared-World Assumption Stress",
        "",
        "| Policy | Assumption-stress pass rate | Selection frequency | Modeled cost P05 | P50 | P95 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        uncertainty = uncertainty_by_policy[row["policy_id"]]
        lines.append(
            f"| {row['policy_label']} | "
            f"{as_float(uncertainty['joint_guardrail_pass_probability']):.1%} | "
            f"{as_float(uncertainty['policy_selection_probability']):.1%} | "
            f"{money(uncertainty['internal_cost_p05'])} | {money(uncertainty['internal_cost_p50'])} | "
            f"{money(uncertainty['internal_cost_p95'])} |"
        )
    lines.extend(
        [
            "",
            "The assumption stress test applies one coherent set of recovery-weight, fit, occupancy, and gesture-cost assumptions to every policy in each draw. It then recalculates policy metrics, reapplies all shadow-validation guardrails, and reruns the selection rule.",
            "",
            "## Paired Case-Bootstrap Intervals",
            "",
            "| Policy | Safe recovery path | 95% interval | High-risk under-recovery | 95% interval | Manager review | 95% interval |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary_rows:
        manager_review = (
            "Unknown"
            if int(row.get("manager_review_evaluable_cases", 0)) == 0
            else f"{as_float(row['manager_review_rate']):.1%}"
        )
        manager_interval = (
            "Unknown"
            if int(row.get("manager_review_evaluable_cases", 0)) == 0
            else f"{as_float(row['manager_review_rate_ci_low']):.1%}-{as_float(row['manager_review_rate_ci_high']):.1%}"
        )
        lines.append(
            f"| {row['policy_label']} | {as_float(row['adequacy_rate']):.1%} | "
            f"{as_float(row['adequacy_rate_ci_low']):.1%}-{as_float(row['adequacy_rate_ci_high']):.1%} | "
            f"{as_float(row['high_risk_under_recovery_rate']):.1%} | "
            f"{as_float(row['high_risk_under_recovery_ci_low']):.1%}-{as_float(row['high_risk_under_recovery_ci_high']):.1%} | "
            f"{manager_review} | {manager_interval} |"
        )
    lines.extend(
        [
            "",
            "Case IDs are resampled once per bootstrap draw and applied to every policy. This paired design preserves case-level comparability and quantifies sampling uncertainty without inventing additional hotel outcomes.",
            "",
            "## Interpretation",
            "",
            "- A high pass rate means a policy repeatedly clears the declared simulation rules under the tested assumptions; it does not establish real-world effectiveness.",
            "- Selection frequency measures how often the same policy wins after all guardrails and tie-breakers are reapplied; it is not an empirically calibrated probability of business success.",
            "- Cost percentiles reflect synthetic case mix and assumed marginal-cost ranges, not property accounting estimates.",
            "- Shadow-mode data should replace cost assumptions and test manager overrides, operational feasibility, and guest-recovery outcomes before controlled use.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    required = [POLICY_DECISION_SUMMARY_PATH, POLICY_UNCERTAINTY_SUMMARY_PATH]
    if any(not path.exists() for path in required):
        print("Missing policy comparison artifacts. Run `make compare-policies` first.")
        return 1
    _, summary_rows = read_csv_rows(POLICY_DECISION_SUMMARY_PATH)
    _, uncertainty_rows = read_csv_rows(POLICY_UNCERTAINTY_SUMMARY_PATH)
    REPORT_PATH.write_text(render_report(summary_rows, uncertainty_rows), encoding="utf-8")
    print(f"Wrote policy sensitivity report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
