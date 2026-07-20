from __future__ import annotations

import argparse
import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = PROJECT_ROOT / "cloudflare" / "ui"
TEMPLATE_PATH = UI_ROOT / "index.html"
STYLES_PATH = UI_ROOT / "styles.css"
SCRIPT_PATH = UI_ROOT / "app.js"
OUTPUT_PATH = PROJECT_ROOT / "cloudflare" / "src" / "ui.py"


def render_html() -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    styles = STYLES_PATH.read_text(encoding="utf-8").strip()
    script = SCRIPT_PATH.read_text(encoding="utf-8").strip()
    html = template.replace("/*__STYLES__*/", styles).replace("/*__SCRIPT__*/", script)
    if "/*__STYLES__*/" in html or "/*__SCRIPT__*/" in html:
        raise ValueError("Worker UI template still contains an unresolved asset placeholder.")
    return html


def render_worker_module() -> str:
    html = render_html()
    if "'''" in html:
        raise ValueError("Worker UI cannot contain three consecutive single quotes.")
    source = f"DECISION_DESK_HTML = r'''{html}'''\n"
    ast.parse(source)
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the embedded Cloudflare Worker decision-desk UI.")
    parser.add_argument("--check", action="store_true", help="Fail if the generated Python module is stale.")
    args = parser.parse_args()
    rendered = render_worker_module()

    if args.check:
        current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        if current != rendered:
            print("Worker UI is stale. Run: python3 scripts/build_worker_ui.py")
            return 1
        print("Worker UI matches the canonical HTML, CSS, and JavaScript sources.")
        return 0

    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Built {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
