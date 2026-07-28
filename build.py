#!/usr/bin/env python3
"""Inline data/*.json into template.html and write index.html."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

data = []
for path in sorted((ROOT / "data").glob("*.json")):
    try:
        data.append(json.loads(path.read_text()))
    except json.JSONDecodeError as e:
        # Don't skip: quietly dropping a gladiator publishes a wrong board that
        # looks right. Fail the build instead, so the last good deploy stays up
        # and the red run says why. (Jul 28: a failed autostash committed conflict
        # markers into a data file and Brendan silently vanished from the site.)
        raise SystemExit(f"{path.name} is not valid JSON: {e}")

template = (ROOT / "template.html").read_text()
marker = "/*__DATA__*/[]"
if marker not in template:
    raise SystemExit("template.html is missing the /*__DATA__*/[] marker")
html = template.replace(marker, json.dumps(data, separators=(",", ":")))
(ROOT / "index.html").write_text(html)
print(f"Wrote index.html ({len(data)} users)")
