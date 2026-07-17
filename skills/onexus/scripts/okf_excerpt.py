#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""okf_excerpt.py — copy a VERBATIM passage from a source file into an OKF gem.

Makes gems self-contained & portable: instead of citing a file on the machine,
embed the passage that IS the concept (a verse, a prayer, a formula) as a
first-class OKF concept (under references/). The copy is byte-exact — verbatim.

Select the passage by line range, by start/end markers, or by a regex per line.

Usage:
  uv run okf_excerpt.py <source> <gem> <dest_relpath>
     (--lines A-B | --from "<start>" --to "<end>" | --grep "<regex>")
     --title "<Title>" [--type Source] [--source-type digital] [--confidence high]
     [--citation "<origin>"] [--heading "<body heading>"] [--timestamp <ISO>]
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def pick(text: str, args) -> str:
    lines = text.splitlines()
    if args.lines:
        a, _, b = args.lines.partition("-")
        a = int(a); b = int(b) if b else len(lines)
        return "\n".join(lines[a - 1:b])
    if args.from_ is not None and args.to is not None:
        s = e = None
        for i, l in enumerate(lines):
            if s is None and args.from_ in l:
                s = i
                # both markers on the same line = that single line
                if args.to in l[l.index(args.from_) + len(args.from_):]:
                    e = i
                    break
            elif s is not None and args.to in l:
                e = i
                break
        if s is None:
            raise SystemExit(f"start marker not found: {args.from_!r}")
        if e is None:
            if not args.to_eof:
                raise SystemExit(
                    f"end marker not found: {args.to!r} — refusing to silently run to "
                    f"end-of-file ({len(lines) - s} lines). Pass --to-eof if that is intended.")
            e = len(lines) - 1
        return "\n".join(lines[s:e + 1])
    if args.grep:
        rx = re.compile(args.grep)
        keep = [l for l in lines if rx.search(l)]
        if not keep:
            raise SystemExit(f"no lines match: {args.grep!r}")
        return "\n".join(keep)
    raise SystemExit("choose a selector: --lines A-B | --from S --to E | --grep RE")


def main() -> int:
    ap = argparse.ArgumentParser(description="Embed a verbatim source passage into an OKF gem.")
    ap.add_argument("source", type=Path)
    ap.add_argument("gem", type=Path)
    ap.add_argument("dest", help="relpath inside the gem, e.g. references/primary-source.md")
    ap.add_argument("--lines")
    ap.add_argument("--from", dest="from_")
    ap.add_argument("--to")
    ap.add_argument("--to-eof", action="store_true",
                    help="allow --from/--to selection to run to end-of-file when the end marker is missing")
    ap.add_argument("--grep")
    ap.add_argument("--title", required=True)
    ap.add_argument("--type", default="Source")
    ap.add_argument("--source-type", dest="stype", default="digital")
    ap.add_argument("--confidence", default="high")
    ap.add_argument("--citation", default="")
    ap.add_argument("--heading", default="Text")
    ap.add_argument("--description", default="")
    ap.add_argument("--tags", default="", help="comma-separated, e.g. stoicism,virtue")
    ap.add_argument("--timestamp", default="")
    args = ap.parse_args()

    if not args.source.is_file():
        raise SystemExit(f"source not found: {args.source}")
    if not args.gem.is_dir():
        raise SystemExit(f"gem not found: {args.gem}")

    passage = pick(args.source.read_text(encoding="utf-8"), args).strip("\n")
    if not passage.strip():
        raise SystemExit("selected passage is empty — check your selector (--lines/--from/--to/--grep)")
    out = args.gem / args.dest
    out.parent.mkdir(parents=True, exist_ok=True)

    fm = [f"type: {args.type}", f"title: {args.title}"]
    desc = args.description or (f"Trecho verbatim — {args.citation}" if args.citation
                                else "Trecho verbatim embutido da fonte.")
    fm.append(f"description: {desc}")
    if args.citation:
        fm.append(f"resource: {args.citation}")
    fm.append(f"tags: [{args.tags or 'source, verbatim'}]")
    fm += [f"source_type: {args.stype}", f"confidence: {args.confidence}"]
    stamp = args.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm.append(f"timestamp: {stamp}")
    doc = "---\n" + "\n".join(fm) + "\n---\n\n" + f"# {args.heading}\n\n{passage}\n"
    if args.citation:
        doc += f"\n# Source\n{args.citation}\n"
    out.write_text(doc, encoding="utf-8")
    print(f"embedded {len(passage.splitlines())} lines -> {out.relative_to(args.gem)}  [{args.stype}/{args.confidence}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
