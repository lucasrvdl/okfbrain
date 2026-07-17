#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""okf_verify.py — MECHANICAL fidelity checks for an OKF gem.

Weak/cheap models grade themselves leniently; this script doesn't. It checks
what a machine CAN check, so the human/strong-model audit only has to catch
what a machine can't:

  1. CITATIONS — every concept has a sources/citations heading with content.
  2. QUOTE MATCH — every blockquote (`> …`, the verbatim carrier) must appear,
     whitespace/markup-normalized, inside a SAVED source file under
     `references/` or `_sources/`. An invented quote fails HERE, not in the
     author's conscience. (Translations/glosses composed by the author should
     be prose or cite-marked, not blockquotes.)
  3. WEASEL LINT — "studies show / estudos mostram"-style lines with no
     citation marker on them.

Default is informational (exit 0). `--strict` exits 1 on any unmatched quote
or uncited concept — the mode weak-model loop cycles MUST run on the concepts
they wrote (`--concept <id>` to scope).

Run:  uv run okf_verify.py <gem> [--concept <id>] [--min-quote-len 20] [--strict] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

RESERVED = {"index.md", "log.md"}
CITES_HEAD = re.compile(r"^#{1,6}\s*(citations?|cita[cç][oõ]es|fontes|sources|refer[eê]ncias)\b", re.IGNORECASE)
WEASEL = re.compile(r"\b(estudos (mostram|indicam|comprovam)|pesquisas (mostram|indicam)|"
                    r"sabe-se que|é amplamente (aceito|conhecido)|especialistas (dizem|afirmam)|"
                    r"studies show|research (shows|indicates)|it is (well[- ]known|widely accepted)|"
                    r"experts say)\b", re.IGNORECASE)
# prose spans inside quotation marks — the gate-evasion carrier both pilot
# executors used (translated/remembered "quotes" in running prose)
QUOTE_SPAN = re.compile(r"[“«„]([^”»“]{8,600})[”»]|(?<!\w)\"([^\"]{8,600})\"(?!\w)")
YEAR = re.compile(r"\b(1[4-9]\d\d|20\d\d)\b")
SUPERLATIVE = re.compile(r"\b(pela primeira vez|primeir[ao] vez|o mais \w+|a mais \w+|"
                         r"o maior|a maior|for the first time|first time|the most \w+)\b",
                         re.IGNORECASE)
SOURCE_DIRS = ("references", "_sources")
SOURCE_EXTS = {".md", ".txt", ".html", ".htm", ".xml", ".json", ".csv"}


def is_meta(rel: str) -> bool:
    return any(part.startswith("_") for part in rel.split("/"))


def split_frontmatter(text: str):
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    if lines[0].strip() != "---":
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            try:
                meta = yaml.safe_load("".join(lines[1:i])) or {}
            except yaml.YAMLError:
                meta = {}
            return (meta if isinstance(meta, dict) else {}), "".join(lines[i + 1:])
    return {}, text


def norm(s: str) -> str:
    """Normalize for quote matching: drop blockquote markers, markdown emphasis,
    and collapse all whitespace — forgiving on formatting, unforgiving on words."""
    s = re.sub(r"^\s*>+\s?", "", s, flags=re.MULTILINE)
    s = re.sub(r"[*_`]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def quote_blocks(body: str) -> list[str]:
    blocks, cur, in_fence = [], [], False
    for line in body.splitlines():
        if re.match(r"^(```|~~~)", line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence and line.lstrip().startswith(">"):
            cur.append(line)
        else:
            if cur:
                blocks.append("\n".join(cur))
                cur = []
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def load_sources(gem: Path) -> list[tuple[str, str]]:
    out = []
    for d in SOURCE_DIRS:
        base = gem / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix.lower() in SOURCE_EXTS:
                try:
                    out.append((p.relative_to(gem).as_posix(),
                                norm(p.read_text(encoding="utf-8", errors="ignore"))))
                except OSError:
                    pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanical fidelity checks (citations, quote match, weasel lint).")
    ap.add_argument("gem", type=Path)
    ap.add_argument("--concept", help="check only this concept id (or path suffix)")
    ap.add_argument("--min-quote-len", type=int, default=20,
                    help="ignore normalized quotes shorter than this (default 20 chars)")
    ap.add_argument("--strict", action="store_true", help="exit 1 on unmatched quotes / uncited concepts")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.gem.is_dir():
        print(f"error: {args.gem} is not a directory", file=sys.stderr)
        return 2

    sources = load_sources(args.gem)
    src_blob_all = " ".join(stext for _, stext in sources)
    uncited, unmatched, weasel = [], [], []
    prose_unmatched, framing = [], []
    checked = quotes_total = quotes_matched = prose_total = prose_matched = 0

    for p in sorted(args.gem.rglob("*.md")):
        rel = p.relative_to(args.gem).as_posix()
        cid = rel[:-3]
        if p.name in RESERVED or is_meta(rel):
            continue
        if args.concept and not (cid == args.concept or cid.endswith(args.concept)):
            continue
        checked += 1
        _, body = split_frontmatter(p.read_text(encoding="utf-8").lstrip("﻿"))
        is_source_doc = cid.split("/")[0] in SOURCE_DIRS

        if not any(CITES_HEAD.match(l) for l in body.splitlines()) and not is_source_doc:
            uncited.append(cid)

        if not is_source_doc:  # source mirrors ARE the evidence; don't self-match
            for q in quote_blocks(body):
                nq = norm(q)
                if len(nq) < args.min_quote_len:
                    continue
                quotes_total += 1
                if any(nq in stext for _, stext in sources):
                    quotes_matched += 1
                else:
                    unmatched.append({"concept": cid, "quote": nq[:90] + ("…" if len(nq) > 90 else "")})

        in_cites = in_fence = False
        src_blob = src_blob_all
        for line in body.splitlines():
            if re.match(r"^(```|~~~)", line.strip()):
                in_fence = not in_fence
                continue
            if line.startswith("#"):
                in_cites = bool(CITES_HEAD.match(line))
                continue
            if in_cites or in_fence:
                continue
            if WEASEL.search(line) and "](" not in line and "[" not in line:
                weasel.append({"concept": cid, "line": line.strip()[:90]})
            if is_source_doc or line.lstrip().startswith(">"):
                continue
            # quoted spans in PROSE must also trace to a saved source (doctrine:
            # your own translations go in plain prose, never inside quotes)
            for m in QUOTE_SPAN.finditer(line):
                span = norm(m.group(1) or m.group(2) or "")
                if len(span) < args.min_quote_len or span[:1] in ")].,;:»”":
                    continue  # too short, or regex artifact between adjacent quotes
                prose_total += 1
                if span in src_blob:
                    prose_matched += 1
                elif len(span) < 40:
                    # short quoted span (often a title/term) — auditor hint, not a failure
                    framing.append({"concept": cid, "kind": "short-quoted-span",
                                    "line": f"“{span[:80]}”"})
                    prose_matched += 0
                else:
                    prose_unmatched.append({"concept": cid,
                                            "quote": span[:90] + ("…" if len(span) > 90 else "")})
            # bibliographic-framing hints (never fatal — they aim the auditor)
            for y in set(YEAR.findall(line)):
                if y not in src_blob:
                    framing.append({"concept": cid, "kind": "year-not-in-sources",
                                    "line": f"{y}: {line.strip()[:80]}"})
            sm = SUPERLATIVE.search(line)
            if sm and norm(sm.group(0)).lower() not in src_blob.lower():
                framing.append({"concept": cid, "kind": "superlative",
                                "line": line.strip()[:90]})

    report = {
        "gem": str(args.gem),
        "concepts_checked": checked,
        "sources_indexed": len(sources),
        "quotes": {"total": quotes_total, "matched": quotes_matched},
        "unmatched_quotes": unmatched,
        "prose_quotes": {"total": prose_total, "matched": prose_matched},
        "unmatched_prose": prose_unmatched,
        "uncited": uncited,
        "weasel": weasel,
        "framing_hints": framing,
    }
    failed = bool(unmatched or prose_unmatched or uncited)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if (args.strict and failed) else 0

    print(f"okf-verify — {args.gem.name} — {checked} concept(s), {len(sources)} saved source file(s)")
    print(f"  blockquotes: {quotes_matched}/{quotes_total} matched · prose quotes: "
          f"{prose_matched}/{prose_total} matched")
    for u in unmatched[:10]:
        print(f"  ✗ UNMATCHED  {u['concept']}: “{u['quote']}”")
    if len(unmatched) > 10:
        print(f"    … +{len(unmatched) - 10} more")
    for u in prose_unmatched[:10]:
        print(f"  ✗ PROSE-QUOTE {u['concept']}: “{u['quote']}” (quote em prosa sem fonte salva — "
              f"vire blockquote colado ou prosa sem aspas)")
    if len(prose_unmatched) > 10:
        print(f"    … +{len(prose_unmatched) - 10} more")
    print(f"  uncited concepts: {len(uncited)}" + (" — " + ", ".join(uncited[:6]) if uncited else ""))
    for w in weasel[:6]:
        print(f"  ! weasel     {w['concept']}: {w['line']}")
    for f in framing[:6]:
        print(f"  ! framing    {f['concept']} [{f['kind']}]: {f['line']}")
    if len(framing) > 6:
        print(f"    … +{len(framing) - 6} more framing hint(s)")
    if not failed and not weasel and not framing:
        print("  ✓ clean")
    if args.strict and failed:
        print("  STRICT: failing (fix the quote to match a saved source, save the source, or turn it into cited prose)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
