#!/usr/bin/env python3
"""Inline data/*.json into template.html and write index.html."""

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
(ROOT / "index.html").write_text(html)
print(f"Wrote index.html ({len(data)} users)")
