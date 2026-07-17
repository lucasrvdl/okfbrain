#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6", "numpy>=1.26", "model2vec>=0.3"]
# ///
"""okf_embed.py — build/refresh the gem's SEMANTIC index (static embeddings).

Humble-hardware by design: Model2Vec static embeddings are a distilled lookup
table — no attention, no torch, no GPU, no LLM tokens. Indexing a 1500-concept
gem takes seconds on a laptop CPU; querying is instant. The default model is
multilingual (~250MB, downloaded ONCE to the HF cache; offline afterwards).

The index is a sidecar INSIDE the gem — `_index/embeddings.npz` (`_` = meta,
so it travels with the gem and stays out of the graph/validation). It is
INCREMENTAL: only new/changed concepts are re-embedded (content hash).

okf_search.py automatically goes HYBRID (BM25 + cosine, RRF fusion) whenever
this index exists — "iniciação" then finds "Dīkṣā".

Run:  uv run okf_embed.py <gem> [--model NAME] [--rebuild] [--json]
      (pip users: pip install model2vec numpy)
Model override: --model or the OKF_EMBED_MODEL environment variable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

RESERVED = {"index.md", "log.md"}
DEFAULT_MODEL = os.environ.get("OKF_EMBED_MODEL", "minishlab/potion-multilingual-128M")
INDEX_REL = Path("_index") / "embeddings.npz"


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


def doc_text(meta: dict, body: str) -> str:
    title = str(meta.get("title", ""))
    desc = str(meta.get("description", ""))
    tags = " ".join(str(t) for t in meta.get("tags", []) if t) if isinstance(meta.get("tags"), list) else ""
    heads = " ".join(l.lstrip("# ").strip() for l in body.splitlines() if l.startswith("#"))
    return f"{title}\n{desc}\n{tags}\n{heads}\n{body[:1500]}"


def collect(gem: Path) -> list[tuple[str, str, str]]:
    """[(concept_id, content_hash, text_to_embed)] — same corpus as okf_search."""
    out = []
    for p in sorted(gem.rglob("*.md")):
        rel = p.relative_to(gem).as_posix()
        if p.name in RESERVED or is_meta(rel):
            continue
        raw = p.read_text(encoding="utf-8", errors="replace").lstrip("﻿")
        meta, body = split_frontmatter(raw)
        out.append((rel[:-3], hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest(),
                    doc_text(meta, body)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build/refresh a gem's semantic index (static embeddings).")
    ap.add_argument("gem", type=Path)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--rebuild", action="store_true", help="ignore the existing index and re-embed everything")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.gem.is_dir():
        print(f"error: {args.gem} is not a directory", file=sys.stderr)
        return 2

    try:
        import numpy as np
        from model2vec import StaticModel
    except ImportError:
        print("semantic index needs the (light, CPU-only) embedding lib:\n"
              "    pip install model2vec numpy      (or run me via `uv run`)\n"
              "Lexical search keeps working without it.", file=sys.stderr)
        return 3

    docs = collect(args.gem)
    idx_path = args.gem / INDEX_REL
    old_ids: list[str] = []
    old_hashes: dict[str, str] = {}
    old_vecs = None
    if idx_path.exists() and not args.rebuild:
        try:
            data = np.load(idx_path, allow_pickle=False)
            if str(data["model"]) == args.model:
                old_ids = [str(x) for x in data["ids"]]
                old_vecs = data["vectors"]
                old_hashes = {i: str(h) for i, h in zip(old_ids, data["hashes"])}
        except Exception as exc:
            print(f"warn: existing index unreadable ({exc}) — rebuilding", file=sys.stderr)

    keep_rows: dict[str, int] = {cid: i for i, cid in enumerate(old_ids)}
    todo = [(cid, h, txt) for cid, h, txt in docs if old_hashes.get(cid) != h]
    kept = len(docs) - len(todo)

    if not todo and set(old_ids) == {cid for cid, _, _ in docs}:
        msg = {"gem": str(args.gem), "concepts": len(docs), "embedded": 0,
               "kept": kept, "model": args.model, "index": str(idx_path)}
        print(json.dumps(msg, ensure_ascii=False) if args.json
              else f"index up-to-date — {len(docs)} concept(s), 0 re-embedded ({idx_path})")
        return 0

    model = StaticModel.from_pretrained(args.model)
    new_vecs = model.encode([txt for _, _, txt in todo]) if todo else None

    dim = (new_vecs.shape[1] if new_vecs is not None
           else (old_vecs.shape[1] if old_vecs is not None else 0))
    ids, hashes, rows = [], [], []
    for cid, h, _ in docs:
        ids.append(cid)
        hashes.append(h)
        rows.append(None)
    todo_pos = {cid: k for k, (cid, _, _) in enumerate(todo)}
    mat = np.zeros((len(docs), dim), dtype=np.float32)
    for r, (cid, h, _) in enumerate(docs):
        if cid in todo_pos:
            mat[r] = new_vecs[todo_pos[cid]]
        else:
            mat[r] = old_vecs[keep_rows[cid]]
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = (mat / norms).astype(np.float32)

    idx_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(idx_path, ids=np.array(ids), hashes=np.array(hashes),
                        vectors=mat, model=np.array(args.model), fmt=np.array("okf-embed-v1"))
    msg = {"gem": str(args.gem), "concepts": len(docs), "embedded": len(todo),
           "kept": kept, "model": args.model, "dim": dim, "index": str(idx_path)}
    print(json.dumps(msg, ensure_ascii=False) if args.json
          else f"embedded {len(todo)} (kept {kept}) of {len(docs)} concept(s) "
               f"[{args.model}, dim {dim}] -> {idx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
