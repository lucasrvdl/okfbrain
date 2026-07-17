#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""okf_log.py — append an enriched, dated entry to a gem's log.md.

Records provenance of EDITS: date (system) · harness · model · action — so you can
later see WHO changed WHAT (especially when a loop runs with multiple models).

Usage:
  uv run okf_log.py <gem> --note "added intro/overview" \
     [--kind Expansion] [--agent "Claude Code"] [--model "opus-4.8"] [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Append a dated provenance entry to a gem's log.md.")
    ap.add_argument("gem", type=Path)
    ap.add_argument("--note", required=True)
    ap.add_argument("--kind", default="Update", help="Creation/Update/Expansion/Ingest/Embed/Edit/Learn/Merge/Deprecation/Loop")
    ap.add_argument("--agent", default="", help="harness, e.g. 'Claude Code', 'Codex'")
    ap.add_argument("--model", default="", help="model, e.g. 'opus-4.8'")
    ap.add_argument("--date", default="", help="YYYY-MM-DD (default: system today)")
    args = ap.parse_args()
    if not args.gem.is_dir():
        raise SystemExit(f"gem not found: {args.gem}")

    d = args.date or datetime.now().strftime("%Y-%m-%d")
    meta = " · ".join(x for x in (args.agent, args.model) if x)
    entry = f"* **{args.kind}**" + (f" · {meta}" if meta else "") + f" — {args.note}"

    log = args.gem / "log.md"
    text = log.read_text(encoding="utf-8") if log.exists() else "# Update Log\n"
    lines = text.splitlines()
    heading = f"## {d}"
    if heading in lines:
        lines.insert(lines.index(heading) + 1, entry)  # add under today's date
    else:
        ins = 0
        for j, l in enumerate(lines):
            if l.startswith("# "):
                ins = j + 1
                break
        lines[ins:ins] = ["", heading, entry]  # new date section, newest first
    log.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"logged -> {log.name}: {entry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
