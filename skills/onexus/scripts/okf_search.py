#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""okf_search.py — lexical search inside an OKF gem (pure Python BM25).

Why: grep misses inflections and diacritics. This ranks whole concepts with
BM25 over weighted fields (title > description/tags/id > body) and FOLDS
DIACRITICS both ways, so `diksa` finds "Dīkṣā" and `puja` finds "pūjā".
Original-script tokens (Devanagari etc.) are kept verbatim, so searching
in the source script works too. Lexical only — it does not know synonyms;
for those, try the other language/term the gem itself uses.

Use it before writing (deepen instead of duplicating), to answer "what does
the gem say about X", and to aim a loop cycle.

HYBRID: when the gem has a semantic index (`_index/embeddings.npz`, built by
okf_embed.py) and model2vec is installed, results fuse BM25 + cosine via RRF —
"iniciação" then finds "Dīkṣā". Falls back to pure BM25 otherwise (a note on
stderr says why). Force modes: --semantic (vectors only) / --no-semantic.

Run:  uv run okf_search.py <gem> "query" [--top 8] [--json]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from pathlib import Path
import os
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

RESERVED = {"index.md", "log.md"}
TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
K1, B = 1.5, 0.75
W_TITLE, W_META, W_BODY = 3.0, 2.0, 1.0


def is_meta(rel: str) -> bool:
    return any(part.startswith("_") for part in rel.split("/"))


def fold(s: str) -> str:
    """casefold + strip combining marks: Dīkṣā -> diksa, pūjā -> puja."""
    nk = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in nk if not unicodedata.combining(c))


def tokens(s: str) -> list[str]:
    return [t for t in TOKEN.findall(fold(s)) if len(t) > 1]


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


def build_index(gem: Path):
    docs = []
    for p in sorted(gem.rglob("*.md")):
        rel = p.relative_to(gem).as_posix()
        if p.name in RESERVED or is_meta(rel):
            continue
        meta, body = split_frontmatter(p.read_text(encoding="utf-8").lstrip("﻿"))
        title = str(meta.get("title", p.stem))
        desc = str(meta.get("description", ""))
        tags = " ".join(str(t) for t in meta.get("tags", []) if t) if isinstance(meta.get("tags"), list) else ""
        tf: dict[str, float] = {}
        for text, w in ((title, W_TITLE), (f"{desc} {tags} {rel[:-3]}", W_META), (body, W_BODY)):
            for t in tokens(text):
                tf[t] = tf.get(t, 0.0) + w
        docs.append({"id": rel[:-3], "title": title, "description": desc,
                     "tf": tf, "len": sum(tf.values()), "body": body})
    return docs


def bm25(docs, query: str, top: int):
    q = tokens(query)
    if not q or not docs:
        return []
    n = len(docs)
    avg = (sum(d["len"] for d in docs) / n) or 1.0
    df = {t: sum(1 for d in docs if t in d["tf"]) for t in set(q)}
    out = []
    for d in docs:
        s = 0.0
        for t in q:
            f = d["tf"].get(t, 0.0)
            if not f:
                continue
            idf = math.log(1 + (n - df[t] + .5) / (df[t] + .5))
            s += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * d["len"] / avg))
        if s > 0:
            out.append((s, d))
    out.sort(key=lambda x: -x[0])
    return out[:top]


def semantic_ranks(gem: Path, query: str, doc_ids: set[str]):
    """[(concept_id, cosine)] via the gem's static-embedding sidecar, or
    (None, reason) when unavailable — search then stays lexical."""
    idx = gem / "_index" / "embeddings.npz"
    if not idx.exists():
        return None, "no semantic index (build one: okf_embed.py <gem>)"
    try:
        import numpy as np
        from model2vec import StaticModel
    except ImportError:
        return None, "model2vec not installed (pip install model2vec numpy)"
    try:
        data = np.load(idx, allow_pickle=False)
        ids = [str(x) for x in data["ids"]]
        vecs = data["vectors"]
        model_name = str(data["model"])
    except Exception as exc:
        return None, f"index unreadable: {exc}"
    missing = doc_ids.symmetric_difference(ids)
    if missing and len(missing) > max(2, len(doc_ids) // 10):
        print(f"note: semantic index is stale ({len(missing)} concept(s) out of sync) — "
              f"refresh with okf_embed.py", file=sys.stderr)
    q = StaticModel.from_pretrained(model_name).encode([query])[0]
    n = (q ** 2).sum() ** 0.5 or 1.0
    sims = vecs @ (q / n)
    order = sims.argsort()[::-1][:60]
    return [(ids[i], float(sims[i])) for i in order if sims[i] > 0.05], ""


def snippet(body: str, query: str, width: int = 150) -> str:
    q = set(tokens(query))
    for line in body.splitlines():
        l = line.strip()
        if not l or l.startswith(("#", "---", "|")):
            continue
        if q & set(tokens(l)):
            l = re.sub(r"[*_`\[\]]", "", l)
            return (l[:width] + "…") if len(l) > width else l
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="BM25 search inside an OKF gem (diacritic-folded).")
    ap.add_argument("gem", type=Path)
    ap.add_argument("query")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--semantic", action="store_true", help="rank by vectors only (needs okf_embed index)")
    ap.add_argument("--no-semantic", action="store_true", help="pure BM25, ignore any semantic index")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.gem.is_dir():
        print(f"error: {args.gem} is not a directory", file=sys.stderr)
        return 2

    docs = build_index(args.gem)
    by_id = {d["id"]: d for d in docs}
    bm_hits = bm25(docs, args.query, max(args.top * 4, 24))

    sem, why = ((None, "disabled (--no-semantic)") if args.no_semantic
                else semantic_ranks(args.gem, args.query, set(by_id)))
    if sem is None and (args.semantic or not args.no_semantic):
        if args.semantic:
            print(f"error: --semantic unavailable — {why}", file=sys.stderr)
            return 2
        if "no semantic index" not in why:
            print(f"note: lexical only — {why}", file=sys.stderr)

    signals: dict[str, set] = {}
    if args.semantic and sem:
        fused = [(sim, by_id[cid]) for cid, sim in sem if cid in by_id][:args.top]
        for cid, _ in sem:
            signals.setdefault(cid, set()).add("sem")
        hits = fused
    elif sem:
        K = 60.0
        score: dict[str, float] = {}
        for rank, (s, d) in enumerate(bm_hits):
            score[d["id"]] = score.get(d["id"], 0.0) + 1.0 / (K + rank)
            signals.setdefault(d["id"], set()).add("bm25")
        for rank, (cid, _) in enumerate(sem):
            if cid in by_id:
                score[cid] = score.get(cid, 0.0) + 1.0 / (K + rank)
                signals.setdefault(cid, set()).add("sem")
        ordered = sorted(score.items(), key=lambda kv: -kv[1])[:args.top]
        hits = [(sc, by_id[cid]) for cid, sc in ordered]
    else:
        hits = bm_hits[:args.top]
        for _, d in hits:
            signals.setdefault(d["id"], set()).add("bm25")

    if args.json:
        print(json.dumps([{"id": d["id"], "title": d["title"], "score": round(s, 4),
                           "signals": sorted(signals.get(d["id"], [])),
                           "description": d["description"],
                           "snippet": snippet(d["body"], args.query)} for s, d in hits],
                         ensure_ascii=False, indent=2))
        return 0
    if not hits:
        print(f"no match for {args.query!r} in {len(docs)} concepts (lexical search — try the term the gem itself uses)")
        return 1
    print(f"{len(hits)} hit(s) for {args.query!r} — {args.gem.name}, {len(docs)} concepts")
    for i, (s, d) in enumerate(hits, 1):
        sig = "+".join(sorted(signals.get(d["id"], []))) or "bm25"
        print(f"  {i}. [{s:7.4f} {sig}] {d['id']} — {d['title']}")
        sn = snippet(d["body"], args.query)
        if sn:
            print(f"         {sn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
