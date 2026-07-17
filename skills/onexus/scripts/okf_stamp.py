#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Stamp provenance (source_type + confidence) into OKF concept frontmatter, in bulk.

Provenance is the onexus differentiator: every concept carries WHERE it came from
and HOW trustworthy it is, so fidelity becomes queryable/visible instead of prose.

  source_type: digital | ocr | web | mixed | none
  confidence:  high | medium | low

Insertion is TEXTUAL — it only adds/updates those two keys and preserves the rest
of the frontmatter exactly (no YAML re-dump, no reordering).

Usage:
  uv run okf_stamp.py <bundle> <relpath>=<source_type>:<confidence> [...] [--default st:conf]

Example:
  uv run okf_stamp.py ./my-gem \\
     sources/primary-text.md=digital:high \\
     sources/scanned-edition.md=ocr:low \\
     --default web:medium
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RESERVED = {"index.md", "log.md"}
VALID_ST = {"digital", "ocr", "web", "mixed", "none"}
VALID_CONF = {"high", "medium", "low"}


def parse_spec(spec: str) -> tuple[str, str]:
    st, _, conf = spec.partition(":")
    if st not in VALID_ST or conf not in VALID_CONF:
        raise ValueError(f"invalid spec '{spec}' (source_type:{sorted(VALID_ST)} confidence:{sorted(VALID_CONF)})")
    return st, conf


def stamp_file(path: Path, st: str, conf: str, only_if_missing: bool = False) -> tuple[bool, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return False, f"unreadable: {exc}"
    if not text.startswith("---"):
        return False, "no frontmatter"
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return False, "unterminated frontmatter"
    has_both = all(any(l.strip().startswith(k) for l in lines[1:end])
                   for k in ("source_type:", "confidence:"))
    if only_if_missing and has_both:
        return False, "already stamped — provenance is deliberate; overwrite only with an explicit pair or --force-default"
    fm = [l for l in lines[1:end] if not l.strip().startswith(("source_type:", "confidence:"))]
    fm += [f"source_type: {st}", f"confidence: {conf}"]
    path.write_text("\n".join(["---", *fm, "---", *lines[end + 1:]]), encoding="utf-8")
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description="Stamp provenance into OKF concepts.")
    ap.add_argument("bundle", type=Path)
    ap.add_argument("pairs", nargs="*", help="relpath=source_type:confidence")
    ap.add_argument("--default", help="source_type:confidence for every unspecified concept "
                                      "that has NO provenance yet (never overwrites)")
    ap.add_argument("--force-default", action="store_true",
                    help="let --default overwrite provenance that is already set")
    args = ap.parse_args()
    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2

    overrides: dict[str, tuple[str, str]] = {}
    for p in args.pairs:
        rel, _, spec = p.partition("=")
        overrides[rel.replace("\\", "/")] = parse_spec(spec)
    default = parse_spec(args.default) if args.default else None

    done = skipped = 0
    for md in sorted(args.bundle.rglob("*.md")):
        if md.name in RESERVED:
            continue
        rel = md.relative_to(args.bundle).as_posix()
        from_default = False
        if rel in overrides:
            st_conf = overrides[rel]
        elif any(part.startswith("_") for part in rel.split("/")):
            skipped += 1  # meta files (_loop-state, _learning/…) never take the default
            continue
        else:
            st_conf = default
            from_default = True
        if not st_conf:
            skipped += 1
            continue
        ok, msg = stamp_file(md, *st_conf,
                             only_if_missing=from_default and not args.force_default)
        tag = f"{st_conf[0]}/{st_conf[1]}"
        print(f"  {'OK ' if ok else 'SKIP'} {rel}  [{tag}]" + ("" if ok else f"  ({msg})"))
        done += 1 if ok else 0
        skipped += 0 if ok else 1
    print(f"stamped {done}, skipped {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
