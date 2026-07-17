#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""okf_status.py — deterministic OBSERVE for an OKF gem.

One command that gives ANY model the same picture of a gem's state, so the
Observe step of a growth loop never depends on who is looking:
  - concept counts (total, by area, by type)
  - provenance histograms (confidence, source_type)
  - graph health: orphans (no inbound concept links), thin nodes (<2 outbound),
    pending links (targets not yet written — valid gaps under SPEC §5.3)
  - the root index Gaps section (checkbox lines)
  - `_loop-state.md`: STATUS line, queue length, open coverage-map lines

Meta files/dirs (`_` prefix) are reported separately and excluded from the
knowledge graph, matching okf_visualize.py.

Run:  uv run okf_status.py <gem> [--json]
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
except Exception:
    pass

RESERVED = {"index.md", "log.md"}
FENCE = re.compile(r"^(```|~~~)")
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CHECKBOX = re.compile(r"^\s*[-*]\s+\[( |x|X|-|~)\]\s+(.*)$")
CITES_HEAD = re.compile(r"^#{1,6}\s*(citations?|cita[cç][oõ]es|fontes|sources|refer[eê]ncias)\b", re.IGNORECASE)


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


def link_targets(text: str):
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.extend(LINK.findall(line))
    return out


def section(text: str, heading_prefix: str) -> list[str]:
    """Lines under the first `# <heading_prefix>…` heading, up to the next `# `."""
    lines, grab = [], False
    for line in text.splitlines():
        if line.startswith("# "):
            if grab:
                break
            grab = line[2:].strip().lower().startswith(heading_prefix.lower())
            continue
        if grab:
            lines.append(line)
    return lines


def scan(gem: Path) -> dict:
    files = sorted(p for p in gem.rglob("*.md") if p.is_file())
    concepts: dict[str, dict] = {}   # rel -> {type, conf, stype, area}
    meta_files: list[str] = []
    outlinks: dict[str, list[str]] = {}

    knowledge = []
    for p in files:
        rel = p.relative_to(gem).as_posix()
        if p.name in RESERVED:
            continue
        if is_meta(rel):
            meta_files.append(rel)
            continue
        knowledge.append((p, rel))

    ids = {rel[:-3] for _, rel in knowledge}
    cites: dict[str, bool] = {}
    for p, rel in knowledge:
        meta, body = split_frontmatter(p.read_text(encoding="utf-8").lstrip("﻿"))
        cid = rel[:-3]
        cites[cid] = any(CITES_HEAD.match(l) for l in body.splitlines())
        concepts[cid] = {
            "type": str(meta.get("type", "Untyped")),
            "confidence": str(meta.get("confidence", "")).lower() or "unrated",
            "source_type": str(meta.get("source_type", "")).lower() or "unset",
            "area": cid.split("/")[0] if "/" in cid else "(root)",
        }
        outs = []
        for t in link_targets(body):
            t = t.split("#", 1)[0]
            if not t.endswith(".md") or re.match(r"^[a-z][a-z0-9+.-]*://", t):
                continue
            if t.startswith("/"):
                tgt = t.lstrip("/")[:-3]
            else:
                resolved = (p.parent / t).resolve()
                tgt = resolved.relative_to(gem.resolve()).as_posix()[:-3] \
                    if resolved.is_relative_to(gem.resolve()) else None
            if tgt and tgt != cid:
                outs.append(tgt)
        outlinks[cid] = outs

    inbound: dict[str, int] = {cid: 0 for cid in concepts}
    pending: list[dict] = []
    for cid, outs in outlinks.items():
        for tgt in outs:
            if tgt in inbound:
                inbound[tgt] += 1
            elif tgt not in ids and not (gem / (tgt + ".md")).exists():
                pending.append({"from": cid, "target": tgt})  # file truly absent (§5.3)

    def hist(key: str) -> dict:
        h: dict[str, int] = {}
        for c in concepts.values():
            h[c[key]] = h.get(c[key], 0) + 1
        return dict(sorted(h.items(), key=lambda kv: -kv[1]))

    orphans = sorted(cid for cid, n in inbound.items() if n == 0)
    thin = sorted(cid for cid, outs in outlinks.items()
                  if len(outs) < 2 and not cid.startswith("references/"))
    uncited = sorted(cid for cid, has in cites.items()
                     if not has and not cid.startswith("references/"))

    # Gaps: checkbox lines anywhere in the root index.md
    gaps = {"open": [], "partial": [], "closed": [], "out_of_scope": []}
    root_index = gem / "index.md"
    if root_index.exists():
        _, body = split_frontmatter(root_index.read_text(encoding="utf-8").lstrip("﻿"))
        for line in body.splitlines():
            m = CHECKBOX.match(line)
            if not m:
                continue
            mark, text = m.group(1), m.group(2).strip()
            key = {" ": "open", "~": "partial", "-": "out_of_scope"}.get(mark, "closed")
            gaps[key].append(text)

    # Loop state
    ls = {"present": False}
    ls_path = gem / "_loop-state.md"
    if ls_path.exists():
        _, body = split_frontmatter(ls_path.read_text(encoding="utf-8").lstrip("﻿"))
        status = [l.strip() for l in section(body, "STATUS") if l.strip()]
        queue = [l.strip() for l in section(body, "Queue") if re.match(r"^\s*\d+\.", l)]
        cover = section(body, "Coverage map")
        open_map = sum(1 for l in cover if re.match(r"^\s*[-*]\s+\[( |~)\]", l))
        ls = {"present": True,
              "status": status[0] if status else "(no STATUS line)",
              "queue_len": len(queue),
              "open_map_lines": open_map}

    n_sources = sum(1 for cid in concepts if cid.split("/")[0] in ("references", "_sources"))
    return {
        "gem": str(gem),
        "concepts": len(concepts),
        "knowledge": len(concepts) - n_sources,
        "sources": n_sources,
        "meta_files": sorted(meta_files),
        "by_area": hist("area"),
        "by_type": hist("type"),
        "confidence": hist("confidence"),
        "source_type": hist("source_type"),
        "edges": sum(len(v) for v in outlinks.values()),
        "orphans": orphans,
        "thin_outlinks": thin,
        "uncited": uncited,
        "pending_links": pending,
        "gaps": gaps,
        "loop_state": ls,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic status/observe report for an OKF gem.")
    ap.add_argument("gem", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.gem.is_dir():
        print(f"error: {args.gem} is not a directory", file=sys.stderr)
        return 2

    s = scan(args.gem)
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0

    print(f"OKF status — {s['gem']}")
    print(f"  concepts: {s['knowledge']} knowledge (+{s['sources']} sources = {s['concepts']})   "
          f"edges: {s['edges']}   meta files: {len(s['meta_files'])}")
    print(f"  areas: " + ", ".join(f"{k} {v}" for k, v in s["by_area"].items()))
    print(f"  types: " + ", ".join(f"{k} {v}" for k, v in s["by_type"].items()))
    print(f"  confidence: " + ", ".join(f"{k} {v}" for k, v in s["confidence"].items())
          + "   source_type: " + ", ".join(f"{k} {v}" for k, v in s["source_type"].items()))
    print(f"  orphans (no inbound): {len(s['orphans'])}"
          + (" — " + ", ".join(s["orphans"][:8]) + ("…" if len(s["orphans"]) > 8 else "") if s["orphans"] else ""))
    print(f"  thin (<2 outbound):   {len(s['thin_outlinks'])}"
          + (" — " + ", ".join(s["thin_outlinks"][:8]) + ("…" if len(s["thin_outlinks"]) > 8 else "") if s["thin_outlinks"] else ""))
    print(f"  uncited (no sources heading): {len(s['uncited'])}"
          + (" — " + ", ".join(s["uncited"][:8]) + ("…" if len(s["uncited"]) > 8 else "") if s["uncited"] else ""))
    print(f"  pending links (§5.3): {len(s['pending_links'])}")
    for pl in s["pending_links"][:8]:
        print(f"    {pl['from']} -> {pl['target']}")
    g = s["gaps"]
    print(f"  gaps in root index: {len(g['open'])} open, {len(g['partial'])} partial, "
          f"{len(g['out_of_scope'])} out-of-scope, {len(g['closed'])} closed")
    for line in g["open"][:8]:
        print(f"    [ ] {line}")
    ls = s["loop_state"]
    if ls["present"]:
        print(f"  loop-state: {ls['status']}  | queue: {ls['queue_len']} item(s) | "
              f"open map lines: {ls['open_map_lines']}")
    else:
        print("  loop-state: (none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
