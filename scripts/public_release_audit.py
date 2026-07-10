from __future__ import annotations

import re
from pathlib import Path

from common import PROJECT_ROOT, REPORT_DIR, ensure_dirs, utc_now_iso


AUDIT_REPORT_PATH = REPORT_DIR / "public-release-audit.md"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "data/raw",
    "data/warehouse",
    "tmp",
    "local_duckdb",
}

TEXT_SUFFIXES = {
    ".csv",
    ".html",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yml",
    ".yaml",
    ".gitignore",
    "",
}

SECRET_PATTERNS = {
    "GitHub token": re.compile(r"gh[opsu]_[A-Za-z0-9_]{20,}"),
    "OpenAI-style key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    "Slack token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{20,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
}

PRIVATE_PATH_PATTERNS = {
    "private repo path": re.compile(re.escape("/home/grant/repos/" + "private")),
    "home secrets path": re.compile(
        re.escape("~/" + ".secrets") + "|" + re.escape("/home/grant/" + ".secrets")
    ),
}

INFRASTRUCTURE_IDENTIFIER_PATTERNS = {
    "AWS account identifier": re.compile(r"(?<!\d)\d{12}(?!\d)"),
    "Snowflake account identifier": re.compile(r"\b[A-Z]{5,12}-[A-Z0-9]{5,12}\b"),
}

LOCAL_ONLY_FILES = {
    "data/manifests/s3_datalake_manifest.json",
    "data/manifests/s3_snowflake_integration_manifest.json",
    "data/manifests/snowflake_s3_copy_manifest.json",
}


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    if relative.as_posix() in LOCAL_ONLY_FILES:
        return True
    parts = set(relative.parts)
    if parts & {".git", ".venv", "__pycache__", "tmp", "local_duckdb"}:
        return True
    relative_text = relative.as_posix()
    return any(relative_text == excluded or relative_text.startswith(f"{excluded}/") for excluded in EXCLUDED_PARTS)


def iter_release_files() -> list[Path]:
    files: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or is_excluded(path):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name == ".gitignore":
            files.append(path)
    return sorted(files)


def read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def find_pattern_hits(patterns: dict[str, re.Pattern[str]], files: list[Path]) -> list[tuple[str, str]]:
    hits = []
    for path in files:
        text = read_text_safely(path)
        for label, pattern in patterns.items():
            if pattern.search(text):
                hits.append((label, path.relative_to(PROJECT_ROOT).as_posix()))
    return hits


def check_gitignore() -> dict[str, bool]:
    gitignore_path = PROJECT_ROOT / ".gitignore"
    text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    return {
        "data/raw/ ignored": "data/raw/" in text,
        "data/warehouse/ ignored": "data/warehouse/" in text,
        ".env ignored": ".env" in text,
        "python cache ignored": "__pycache__/" in text and "*.pyc" in text,
        "Snowflake local config ignored": "connections.toml" in text and "*.p8" in text and "*.pem" in text,
    }


def credential_files_present() -> list[str]:
    risky_names = {
        ".env",
        ".env.local",
        ".env.production",
        "connections.toml",
        "config.toml",
        "credentials.json",
        "token.json",
    }
    risky_suffixes = {".pem", ".p8"}
    found = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or is_excluded(path):
            continue
        if path.name in risky_names or path.suffix in risky_suffixes:
            found.append(path.relative_to(PROJECT_ROOT).as_posix())
    return sorted(found)


def render_report(
    files: list[Path],
    secret_hits: list[tuple[str, str]],
    private_path_hits: list[tuple[str, str]],
    infrastructure_identifier_hits: list[tuple[str, str]],
    ignored: dict[str, bool],
    credential_files: list[str],
) -> str:
    blockers = []
    if secret_hits:
        blockers.append("secret-like token pattern found")
    if private_path_hits:
        blockers.append("private path found")
    if infrastructure_identifier_hits:
        blockers.append("account-scoped infrastructure identifier found")
    if credential_files:
        blockers.append("credential-like local file present")
    missing_ignores = [name for name, passed in ignored.items() if not passed]
    if missing_ignores:
        blockers.append("required ignore rule missing")

    lines = [
        "# Public Release Audit",
        "",
        f"Generated at: `{utc_now_iso()}`",
        "",
        "## Summary",
        "",
        f"- Files scanned: `{len(files)}`",
        f"- Release status: `{'NEEDS REVIEW' if blockers else 'NO BLOCKERS FOUND'}`",
        f"- Blockers: `{len(blockers)}`",
        "",
        "## Automated Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
        f"| Secret-like token patterns | {'FAIL' if secret_hits else 'PASS'} | {len(secret_hits)} hits |",
        f"| Private workspace paths | {'FAIL' if private_path_hits else 'PASS'} | {len(private_path_hits)} hits |",
        f"| Account-scoped infrastructure identifiers | {'FAIL' if infrastructure_identifier_hits else 'PASS'} | {len(infrastructure_identifier_hits)} hits |",
        f"| Credential-like files | {'FAIL' if credential_files else 'PASS'} | {', '.join(credential_files) if credential_files else 'none found'} |",
    ]
    for name, passed in ignored.items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | .gitignore rule {'present' if passed else 'missing'} |")

    lines.extend(
        [
            "",
            "## Public-Safety Boundary",
            "",
            "- Internal hotel records, guest PII, real comp history, internal rates, occupancy, revenue, margin, inventory, and proprietary policy are not included.",
            "- Full public-source downloads remain outside Git under `data/raw/`.",
            "- The local DuckDB database remains outside Git under `data/warehouse/`.",
            "- Snowflake connection files, private keys, and key-pair auth material must remain outside Git.",
            "- Live API credentials are not required for the default workflow and should remain outside the repository.",
            "",
            "## Manual Review Items",
            "",
            "- Confirm generated reports continue to frame the project as a synthetic prototype.",
            "- Confirm references to Santa Monica Proper or Proper Hotels are public-context framing, not claims of internal access.",
            "- Confirm any future live API extraction writes only public-safe, non-secret outputs.",
            "",
        ]
    )

    if secret_hits or private_path_hits or infrastructure_identifier_hits:
        lines.extend(["## Hits Requiring Review", "", "| Type | File |", "| --- | --- |"])
        for label, path in [*secret_hits, *private_path_hits, *infrastructure_identifier_hits]:
            lines.append(f"| {label} | `{path}` |")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    ensure_dirs()
    files = iter_release_files()
    secret_hits = find_pattern_hits(SECRET_PATTERNS, files)
    private_path_hits = find_pattern_hits(PRIVATE_PATH_PATTERNS, files)
    infrastructure_identifier_hits = find_pattern_hits(INFRASTRUCTURE_IDENTIFIER_PATTERNS, files)
    ignored = check_gitignore()
    credential_files = credential_files_present()
    AUDIT_REPORT_PATH.write_text(
        render_report(
            files,
            secret_hits,
            private_path_hits,
            infrastructure_identifier_hits,
            ignored,
            credential_files,
        ),
        encoding="utf-8",
    )
    blockers = bool(
        secret_hits
        or private_path_hits
        or infrastructure_identifier_hits
        or credential_files
        or any(not passed for passed in ignored.values())
    )
    print(f"Wrote public release audit: {AUDIT_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    if blockers:
        print("Public release audit needs review.")
        return 1
    print("Public release audit passed: no blockers found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
