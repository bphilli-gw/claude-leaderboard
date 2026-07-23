#!/usr/bin/env python3
"""Inline data/*.json into template.html and write dashboard.html."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

data = []
for path in sorted((ROOT / "data").glob("*.json")):
    try:
        data.append(json.loads(path.read_text()))
    except json.JSONDecodeError:
        print(f"Skipping unreadable {path.name}")

template = (ROOT / "template.html").read_text()
marker = "/*__DATA__*/[]"
if marker not in template:
    raise SystemExit("template.html is missing the /*__DATA__*/[] marker")
html = template.replace(marker, json.dumps(data, separators=(",", ":")))
(ROOT / "dashboard.html").write_text(html)
print(f"Wrote dashboard.html ({len(data)} users)")
