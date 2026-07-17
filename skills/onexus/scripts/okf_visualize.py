#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Render an Open Knowledge Format (OKF) bundle as a single self-contained,
interactive HTML graph (`viz.html`) — an Obsidian-grade graph view.

No backend, no install on the viewing side, no data leaves the page. Concepts
become nodes (colored by `type`, sized by connections, ringed by `confidence`),
markdown links become edges. Live d3-force physics (drag with springs, gentle
settle animation), semantic-zoom labels that fade with distance, hover that
dims everything but the neighborhood, click → a wiki drawer with the concept's
rendered markdown, links and backlinks, full-text search with fly-to, a local
(neighborhood) mode, type/confidence filters, and Obsidian-style force/display
sliders. `_`-meta files (e.g. `_loop-state.md`) are excluded — they are working
state, not knowledge.

Run:  uv run okf_visualize.py <bundle-dir> [-o viz.html]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

# Windows: force UTF-8 stdout (Unicode paths/titles break under cp1252)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

RESERVED = {"index.md", "log.md"}
FENCE = re.compile(r"^(```|~~~)")
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def is_meta(rel_parts) -> bool:
    """`_`-prefixed files/dirs (e.g. _loop-state.md, _learning/) are meta, not knowledge."""
    return any(part.startswith("_") for part in rel_parts)


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


def build(bundle: Path):
    nodes, edges, seen = [], [], set()
    ghosts: dict[str, str] = {}   # pending link targets (§5.3) → ghost nodes
    files = sorted(p for p in bundle.rglob("*.md")
                   if p.is_file() and p.name not in RESERVED
                   and not is_meta(p.relative_to(bundle).parts))
    ids = {p.relative_to(bundle).with_suffix("").as_posix() for p in files}
    for p in files:
        cid = p.relative_to(bundle).with_suffix("").as_posix()
        meta, body = split_frontmatter(p.read_text(encoding="utf-8").lstrip("﻿"))
        body = body.strip()
        nodes.append({
            "id": cid,
            "type": str(meta.get("type", "Untyped")),
            "conf": str(meta.get("confidence", "")).lower(),
            "stype": str(meta.get("source_type", "")).lower(),
            "title": str(meta.get("title", p.stem)),
            "description": str(meta.get("description", "")),
            "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
            "group": cid.split("/")[0] if "/" in cid else "(root)",
            "body": body[:8000],
        })
        for t in link_targets(body):
            t = t.split("#", 1)[0]
            if not t.endswith(".md"):
                continue
            if t.startswith("/"):
                tgt = t.lstrip("/")[:-3]
            else:
                rp = (p.parent / t).resolve()
                tgt = rp.relative_to(bundle.resolve()).as_posix()[:-3] \
                    if rp.is_relative_to(bundle.resolve()) else None
            if not tgt or tgt == cid or (cid, tgt) in seen:
                continue
            seen.add((cid, tgt))
            if tgt in ids:
                edges.append({"source": cid, "target": tgt})
            elif not (bundle / (tgt + ".md")).exists() \
                    and not any(part.startswith("_") for part in tgt.split("/")):
                # target file truly absent -> pending knowledge (§5.3), a ghost node
                ghosts[tgt] = tgt.rsplit("/", 1)[-1]
                edges.append({"source": cid, "target": tgt, "ghost": True})
    for gid, stem in sorted(ghosts.items()):
        nodes.append({"id": gid, "ghost": True, "type": "(pending)", "conf": "", "stype": "",
                      "title": stem, "description": "Pending link — concept not written yet (§5.3).",
                      "tags": [], "group": gid.split("/")[0] if "/" in gid else "(root)", "body": ""})
    return nodes, edges, len([e for e in edges if not e.get("ghost")])


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAME__ — OKF graph</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@14/marked.min.js"></script>
<style>
:root{
  --surface:#1a1a19; --plane:#0d0d0d; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781;
  --hairline:#2c2c2a; --line:#383835; --accent:#3987e5;
  --glass:rgba(13,13,13,.78); --ring:rgba(255,255,255,.10);
  --good:#0ca30c; --warn:#fab219; --crit:#d03b3b;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden;background:var(--surface);color:var(--ink);
  font:13px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}
#cv{position:fixed;inset:0;display:block;cursor:default;opacity:0;transition:opacity .8s ease}
#cv.ready{opacity:1}

/* ---------- chrome ---------- */
.hud{position:fixed;z-index:10;user-select:none}
#head{top:16px;left:18px;pointer-events:none}
#head h1{margin:0;font-size:15px;font-weight:650;letter-spacing:.01em}
#head .sub{color:var(--muted);font-size:11.5px;margin-top:2px}
#bar{top:14px;right:16px;display:flex;gap:8px;align-items:flex-start;
  transition:right .26s cubic-bezier(.2,.8,.2,1)}
body.drawer-open #bar{right:calc(min(400px,92vw) + 14px)}
body.drawer-open #settings{right:calc(min(400px,92vw) + 14px)}
.btn{width:34px;height:34px;border-radius:10px;border:1px solid var(--ring);background:var(--glass);
  backdrop-filter:blur(14px);color:var(--ink2);display:flex;align-items:center;justify-content:center;
  cursor:pointer;transition:color .15s,border-color .15s,background .15s;flex:none}
.btn:hover{color:var(--ink);border-color:rgba(255,255,255,.22)}
.btn.on{color:var(--accent);border-color:var(--accent)}
.btn svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}

/* search */
#searchWrap{position:relative}
#search{width:230px;height:34px;border-radius:10px;border:1px solid var(--ring);background:var(--glass);
  backdrop-filter:blur(14px);color:var(--ink);padding:0 12px 0 32px;outline:none;font-size:12.5px;
  transition:border-color .15s,width .2s ease}
#search:focus{border-color:rgba(255,255,255,.25);width:280px}
#search::placeholder{color:var(--muted)}
#searchWrap svg{position:absolute;left:10px;top:9px;width:15px;height:15px;stroke:var(--muted);fill:none;
  stroke-width:1.7;stroke-linecap:round;pointer-events:none}
#hits{position:absolute;top:40px;left:0;right:0;background:var(--glass);backdrop-filter:blur(16px);
  border:1px solid var(--ring);border-radius:12px;overflow:hidden;display:none;max-height:290px;overflow-y:auto}
#hits.open{display:block}
.hit{padding:8px 12px;cursor:pointer;display:flex;gap:8px;align-items:center}
.hit:hover,.hit.sel{background:rgba(255,255,255,.06)}
.hit .dot{width:8px;height:8px;border-radius:50%;flex:none}
.hit .t{font-size:12.5px;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hit .p{font-size:10.5px;color:var(--muted);margin-left:auto;flex:none}

/* settings panel */
#settings{position:fixed;top:58px;right:16px;width:250px;background:var(--glass);backdrop-filter:blur(18px);
  border:1px solid var(--ring);border-radius:14px;padding:14px 16px 12px;z-index:11;display:none}
#settings.open{display:block;animation:pop .18s cubic-bezier(.2,.9,.3,1.2)}
@keyframes pop{from{opacity:0;transform:translateY(-6px) scale(.98)}to{opacity:1;transform:none}}
#settings h3{margin:8px 0 6px;font-size:10.5px;font-weight:650;text-transform:uppercase;letter-spacing:.09em;color:var(--muted)}
#settings h3:first-child{margin-top:0}
.ctl{display:flex;align-items:center;gap:8px;margin:7px 0}
.ctl label{flex:1;font-size:12px;color:var(--ink2)}
.ctl output{font-size:10.5px;color:var(--muted);width:30px;text-align:right}
input[type=range]{-webkit-appearance:none;width:104px;height:3px;border-radius:2px;background:var(--line);outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;
  background:var(--ink2);cursor:pointer;transition:background .15s}
input[type=range]:hover::-webkit-slider-thumb{background:var(--accent)}
.switch{position:relative;width:30px;height:17px;flex:none;cursor:pointer}
.switch input{display:none}
.switch i{position:absolute;inset:0;border-radius:10px;background:var(--line);transition:background .15s}
.switch i:before{content:"";position:absolute;width:13px;height:13px;border-radius:50%;background:#cfcec6;
  top:2px;left:2px;transition:transform .15s}
.switch input:checked+i{background:var(--accent)}
.switch input:checked+i:before{transform:translateX(13px)}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;flex:none}
.seg button{border:0;background:transparent;color:var(--muted);font-size:11px;padding:4px 10px;cursor:pointer}
.seg button.on{background:rgba(57,135,229,.18);color:var(--accent)}

/* legends */
#legend{bottom:16px;left:18px;max-width:min(64vw,760px);display:flex;flex-direction:column;gap:7px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{display:flex;align-items:center;gap:7px;background:var(--glass);backdrop-filter:blur(12px);
  border:1px solid var(--ring);border-radius:20px;padding:4px 11px;font-size:11.5px;color:var(--ink2);
  cursor:pointer;transition:opacity .2s,border-color .15s,color .15s}
.chip:hover{border-color:rgba(255,255,255,.25);color:var(--ink)}
.chip.off{opacity:.32}
.chip .dot{width:9px;height:9px;border-radius:50%}
.chip .ringdot{width:9px;height:9px;border-radius:50%;background:transparent;border:2.5px solid}
.chip .n{color:var(--muted);font-size:10.5px}

/* local-mode pill */
#localPill{top:60px;left:18px;display:none;align-items:center;gap:9px;background:var(--glass);
  backdrop-filter:blur(12px);border:1px solid var(--accent);border-radius:20px;padding:5px 8px 5px 13px;font-size:12px}
#localPill.on{display:flex;animation:pop .18s ease}
#localPill b{font-weight:600;color:var(--accent)}
#localPill button{border:0;background:transparent;color:var(--muted);cursor:pointer;font-size:14px;line-height:1;padding:2px 4px}
#localPill button:hover{color:var(--ink)}

/* drawer */
#drawer{position:fixed;top:0;right:0;bottom:0;width:min(400px,92vw);background:var(--glass);
  backdrop-filter:blur(22px);border-left:1px solid var(--ring);z-index:20;
  transform:translateX(103%);transition:transform .26s cubic-bezier(.2,.8,.2,1),width .26s cubic-bezier(.2,.8,.2,1);
  display:flex;flex-direction:column}
#drawer.open{transform:none}
:root{--readw:720px;--readfs:14px}
#drawer.max{width:100vw;border-left:0;display:block;overflow-y:auto;
  background:#141413;backdrop-filter:none; /* solid: blur would turn fixed children into scroll-anchored */
  scrollbar-width:thin;scrollbar-color:var(--line) transparent}
#drawer.max #dhead,#drawer.max #dbody{max-width:var(--readw);margin:0 auto;width:100%;
  padding-left:max(18px,env(safe-area-inset-left));padding-right:max(18px,env(safe-area-inset-right))}
#drawer.max #dhead{position:static;padding-top:58px}
#drawer.max #dbody{overflow:visible;padding-bottom:110px}
#drawer.max .md{font-size:var(--readfs);line-height:1.75}
#drawer.max #dtitle{font-size:22px}
#drawer.max #ddesc{font-size:13.5px}
#drawer.max #dclose,#drawer.max #dmax{position:fixed;background:var(--glass);
  backdrop-filter:blur(14px);border:1px solid var(--ring);width:34px;height:34px;border-radius:10px}
#drawer.max #dclose{top:14px;right:16px}
#drawer.max #dmax{top:14px;right:58px}
#readCtl{display:none;position:fixed;bottom:18px;right:18px;z-index:26;gap:4px;align-items:center;
  background:var(--glass);backdrop-filter:blur(14px);border:1px solid var(--ring);border-radius:12px;padding:5px}
#drawer.max #readCtl{display:flex}
#readCtl button{border:0;background:transparent;color:var(--muted);cursor:pointer;font-size:12.5px;
  min-width:30px;height:28px;border-radius:8px;padding:0 7px}
#readCtl button:hover{color:var(--ink);background:rgba(255,255,255,.08)}
#readCtl .sep{width:1px;height:16px;background:var(--line);margin:0 3px}
#dhead{padding:16px 18px 0;flex:none;position:relative}
#dclose,#dmax{position:absolute;top:12px;width:28px;height:28px;border-radius:8px;border:0;
  background:transparent;color:var(--muted);cursor:pointer;font-size:15px;
  display:flex;align-items:center;justify-content:center}
#dclose{right:12px}
#dmax{right:46px}
#dclose:hover,#dmax:hover{color:var(--ink);background:rgba(255,255,255,.07)}
#dmax svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
#dbody{padding:4px 18px 24px;overflow-y:auto;flex:1;scrollbar-width:thin;scrollbar-color:var(--line) transparent}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.badge{font-size:10.5px;font-weight:600;border-radius:6px;padding:2.5px 8px;letter-spacing:.02em}
.badge.type{color:#0d0d0d}
.badge.conf{background:transparent;border:1px solid}
.badge.st{background:rgba(255,255,255,.06);color:var(--muted);font-weight:500}
#dtitle{font-size:17.5px;font-weight:650;margin:0 24px 4px 0;line-height:1.3}
#ddesc{color:var(--ink2);font-size:12.5px;margin:0 0 10px}
.tagrow{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px}
.tag{font-size:10.5px;color:var(--muted);background:rgba(255,255,255,.05);border:1px solid var(--hairline);
  border-radius:6px;padding:1.5px 7px}
#dlocal{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--accent);cursor:pointer;
  border:1px solid rgba(57,135,229,.35);border-radius:8px;padding:4px 10px;background:transparent;margin-bottom:14px}
#dlocal:hover{background:rgba(57,135,229,.12)}
.rel h4{margin:14px 0 4px;font-size:10.5px;font-weight:650;text-transform:uppercase;letter-spacing:.09em;color:var(--muted)}
.rel a{display:flex;gap:7px;align-items:center;color:var(--ink2);cursor:pointer;font-size:12.5px;
  padding:3.5px 8px;margin:0 -8px;border-radius:7px;text-decoration:none}
.rel a:hover{background:rgba(255,255,255,.06);color:var(--ink)}
.rel .dot{width:7px;height:7px;border-radius:50%;flex:none}
.md{border-top:1px solid var(--hairline);margin-top:16px;padding-top:14px;font-size:13px;color:var(--ink2);line-height:1.65}
.md h1,.md h2,.md h3,.md h4{color:var(--ink);line-height:1.3;margin:1.2em 0 .45em;font-weight:650}
.md h1{font-size:15.5px}.md h2{font-size:14.5px}.md h3{font-size:13.5px}.md h4{font-size:12.5px}
.md p{margin:.55em 0}
.md a{color:var(--accent);text-decoration:none}
.md a:hover{text-decoration:underline}
.md code{background:rgba(255,255,255,.07);padding:1px 5px;border-radius:5px;font-size:12px}
.md pre{background:var(--plane);border:1px solid var(--hairline);padding:10px 12px;border-radius:10px;overflow:auto}
.md pre code{background:none;padding:0}
.md blockquote{border-left:2px solid var(--line);margin:.7em 0;padding:.1em 0 .1em 12px;color:var(--muted)}
.md table{border-collapse:collapse;display:block;overflow-x:auto;margin:.7em 0}
.md td,.md th{border:1px solid var(--hairline);padding:4px 9px;font-size:12px}
.md th{color:var(--ink);background:rgba(255,255,255,.04)}
.md img{max-width:100%;border-radius:8px}
.md hr{border:0;border-top:1px solid var(--hairline);margin:1em 0}
.md ul,.md ol{padding-left:1.3em;margin:.5em 0}
#dpath{border-top:1px solid var(--hairline);margin-top:16px;padding-top:10px;color:var(--muted);
  font-size:10.5px;font-family:ui-monospace,Consolas,monospace;word-break:break-all}

#legBtn{display:none}
@media (max-width:640px){
  #head h1{font-size:13.5px;max-width:52vw;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  #head .sub{font-size:10px;max-width:52vw}
  #bar{top:54px;left:16px;right:16px}
  #searchWrap{flex:1;min-width:0}
  #search,#search:focus{width:100%}
  #settings{top:98px;right:12px;max-height:70vh;overflow-y:auto}
  body.drawer-open #bar{right:16px}
  #drawer{width:100vw;border-left:0}
  #legend{max-width:calc(100vw - 32px)}
  #legBtn{display:inline-flex}
  #legend .chips{display:none}
  #legend.open .chips{display:flex;max-height:38vh;overflow-y:auto}
  #localPill{top:100px}
}
#toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(60px);background:var(--glass);
  backdrop-filter:blur(14px);border:1px solid var(--ring);color:var(--ink2);font-size:12px;border-radius:10px;
  padding:8px 14px;z-index:30;transition:transform .25s ease;pointer-events:none}
#toast.show{transform:translateX(-50%)}
#offline{position:fixed;inset:0;display:none;align-items:center;justify-content:center;color:var(--muted);
  font-size:13px;text-align:center;padding:0 30px;line-height:1.7}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style></head><body>
<canvas id="cv" role="img" aria-label="Knowledge graph: __N__ concepts, __E__ links"></canvas>

<div class="hud" id="head"><h1>__NAME__</h1><div class="sub" id="subline">__N__ concepts · __E__ links · OKF v0.1</div></div>

<div class="hud" id="bar">
  <div id="searchWrap">
    <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.8-3.8"/></svg>
    <input id="search" placeholder="Search concepts…" autocomplete="off" spellcheck="false" aria-label="Search concepts">
    <div id="hits" role="listbox"></div>
  </div>
  <button class="btn" id="fitBtn" title="Fit graph to view" aria-label="Fit graph to view">
    <svg viewBox="0 0 24 24"><path d="M4 9V5a1 1 0 0 1 1-1h4M15 4h4a1 1 0 0 1 1 1v4M20 15v4a1 1 0 0 1-1 1h-4M9 20H5a1 1 0 0 1-1-1v-4"/></svg>
  </button>
  <button class="btn" id="gearBtn" title="Graph settings" aria-label="Graph settings" aria-expanded="false">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.55-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.01a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55h.01a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.01a1.7 1.7 0 0 0 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.55 1z"/></svg>
  </button>
</div>

<div id="settings" role="dialog" aria-label="Graph settings">
  <h3>Forces</h3>
  <div class="ctl"><label>Center</label><input type="range" id="fCenter" min="0" max="2" step="0.05" value="1"><output></output></div>
  <div class="ctl"><label>Repel</label><input type="range" id="fRepel" min="0.1" max="3" step="0.05" value="1"><output></output></div>
  <div class="ctl"><label>Link force</label><input type="range" id="fLink" min="0" max="2" step="0.05" value="1"><output></output></div>
  <div class="ctl"><label>Link distance</label><input type="range" id="fDist" min="0.4" max="2.5" step="0.05" value="1"><output></output></div>
  <h3>Display</h3>
  <div class="ctl"><label>Color by</label><span class="seg" id="dColorBy">
    <button data-v="type" class="on">Type</button><button data-v="area">Area</button></span></div>
  <div class="ctl"><label>Node size</label><input type="range" id="dSize" min="0.5" max="2" step="0.05" value="1"><output></output></div>
  <div class="ctl"><label>Link thickness</label><input type="range" id="dEdge" min="0.4" max="2.5" step="0.05" value="1"><output></output></div>
  <div class="ctl"><label>Text fade</label><input type="range" id="dFade" min="0.2" max="2.2" step="0.05" value="1"><output></output></div>
  <div class="ctl"><label>Arrows</label><label class="switch"><input type="checkbox" id="dArrows"><i></i></label></div>
  <div class="ctl"><label>Confidence rings</label><label class="switch"><input type="checkbox" id="dRings" checked><i></i></label></div>
  <div class="ctl"><label>Pending links</label><label class="switch"><input type="checkbox" id="dGhosts" checked><i></i></label></div>
  <div class="ctl"><label>Highlight orphans</label><label class="switch"><input type="checkbox" id="dOrph"><i></i></label></div>
  <div class="ctl"><label>Freeze physics</label><label class="switch"><input type="checkbox" id="dFreeze"><i></i></label></div>
</div>

<div class="hud" id="localPill"><span>Local graph · <b id="localName"></b> · depth <b id="localDepth">2</b></span>
  <button id="localExit" title="Exit local graph" aria-label="Exit local graph">✕</button></div>

<div class="hud" id="legend">
  <span class="chip" id="legBtn" role="button" aria-label="Toggle legend">Legend ▾</span>
  <div class="chips" id="typeChips"></div>
  <div class="chips" id="confChips"></div>
</div>

<aside id="drawer" aria-label="Concept details">
  <div id="dhead">
    <button id="dclose" title="Close (Esc)" aria-label="Close panel">✕</button>
    <button id="dmax" title="Expand for reading (E)" aria-label="Expand note for reading">
      <svg viewBox="0 0 24 24"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
    </button>
    <div class="badges" id="dbadges"></div>
    <h2 id="dtitle"></h2>
    <p id="ddesc"></p>
    <div class="tagrow" id="dtags"></div>
    <button id="dlocal"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="m6.6 6.6 3.2 3.2m4.4 0 3.2-3.2M6.6 17.4l3.2-3.2m4.4 0 3.2 3.2"/></svg> Local graph</button>
  </div>
  <div id="dbody">
    <div class="rel" id="dout"></div>
    <div class="rel" id="din"></div>
    <div class="md" id="dmd"></div>
    <div id="dpath"></div>
  </div>
  <div id="readCtl" aria-label="Reading controls">
    <button id="rfMinus" title="Smaller text">A−</button>
    <button id="rfPlus" title="Larger text">A+</button>
    <span class="sep"></span>
    <button id="rwMinus" title="Narrower column">⇥⇤</button>
    <button id="rwPlus" title="Wider column">⇤⇥</button>
  </div>
</aside>

<div id="toast"></div>
<div id="offline"><div>This graph needs internet on first open (d3 + marked come from a CDN).<br>The gem's data itself is embedded in this file.</div></div>

<script>
const NODES=__NODES__, EDGES=__EDGES__;
if(!window.d3){document.getElementById('offline').style.display='flex';}
else (function(){
"use strict";
/* ---------- palette (validated: dataviz skill, dark surface #1a1a19) ---------- */
const CAT=["#3987e5","#199e70","#c98500","#008300","#9085e9","#e66767","#d55181","#d95926"];
const OTHER="#898781";
const CONF={high:"#0ca30c",medium:"#fab219",low:"#d03b3b"};
const CONF_LABEL={high:"high",medium:"medium",low:"low","":"unrated"};
const SURF="#1a1a19", INK="#ffffff", INK2="#c3c2b7", MUTED="#898781", EDGE="#3a3a37", EDGE_HL="#c3c2b7";
const reduceMotion=matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- graph model ---------- */
const byId=Object.fromEntries(NODES.map(n=>[n.id,n]));
const outL={}, inL={};
NODES.forEach(n=>{outL[n.id]=[];inL[n.id]=[];});
EDGES.forEach(e=>{outL[e.source].push(e.target);inL[e.target].push(e.source);});
NODES.forEach(n=>{n.deg=outL[n.id].length+inL[n.id].length;});
/* color slots: fixed order by count desc, >8 fold to Other; two modes — BASE type
   ("Text / Essay" → "Text") or AREA (top folder). Ghosts are always muted. */
const REAL=NODES.filter(n=>!n.ghost);
const baseType=t=>String(t).split("/")[0].trim()||"Untyped";
const typeCount={};REAL.forEach(n=>{const b=baseType(n.type);typeCount[b]=(typeCount[b]||0)+1;});
const typeOrder=Object.keys(typeCount).sort((a,b)=>typeCount[b]-typeCount[a]||a.localeCompare(b));
const typeColor={};typeOrder.forEach((t,i)=>typeColor[t]=i<CAT.length?CAT[i]:OTHER);
const areaCount={};REAL.forEach(n=>{areaCount[n.group]=(areaCount[n.group]||0)+1;});
const areaOrder=Object.keys(areaCount).sort((a,b)=>areaCount[b]-areaCount[a]||a.localeCompare(b));
const areaColor={};areaOrder.forEach((g,i)=>areaColor[g]=i<CAT.length?CAT[i]:OTHER);
const colorOf=n=>n.ghost?MUTED:(S.colorBy==="area"?areaColor[n.group]:typeColor[baseType(n.type)]);
const R=n=>(n.ghost?3.2:Math.min(13,2.6+1.6*Math.sqrt(n.deg)))*S.size;
const realInDeg={};REAL.forEach(n=>realInDeg[n.id]=0);
EDGES.forEach(e=>{if(!e.ghost&&e.target in realInDeg)realInDeg[e.target]+=1;});
NODES.forEach((n,i)=>{ /* golden-angle seed → visible bloom settle */
  const a=i*2.39996, r=14*Math.sqrt(i);
  n.x=Math.cos(a)*r; n.y=Math.sin(a)*r; n.dim=1; n.dimT=1;
});
const LINKS=EDGES.map(e=>({source:e.source,target:e.target,ghost:!!e.ghost}));

/* ---------- state ---------- */
const S={center:1,repel:1,link:1,dist:1,size:1,edge:1,fade:1,arrows:false,rings:true,
  ghosts:true,orphHl:false,colorBy:"type",freeze:false,readfs:14,readw:720};
try{Object.assign(S,JSON.parse(localStorage.getItem("okfviz:__NAME__")||"{}"));}catch(e){}
const hiddenTypes=new Set(), hiddenAreas=new Set(), hiddenConf=new Set();
let hover=null, selected=null, local=null;      // local = Set of visible ids
let dragging=false, needsFit=true;

/* ---------- canvas ---------- */
const cv=document.getElementById("cv"), ctx=cv.getContext("2d");
let W=0,H=0,DPR=1;
function resize(){DPR=Math.min(devicePixelRatio||1,2);W=innerWidth;H=innerHeight;
  cv.width=W*DPR;cv.height=H*DPR;cv.style.width=W+"px";cv.style.height=H+"px";draw&&(draw.dirty=true);}
addEventListener("resize",resize);resize();

/* ---------- simulation ---------- */
const linkF=d3.forceLink(LINKS).id(d=>d.id);
const sim=d3.forceSimulation(NODES)
  .force("link",linkF)
  .force("charge",d3.forceManyBody().distanceMax(480))
  .force("x",d3.forceX(0)).force("y",d3.forceY(0))
  .force("collide",d3.forceCollide().strength(.8))
  .velocityDecay(.32).alphaDecay(reduceMotion?.15:.022);
function applyForces(){
  linkF.distance(l=>(58+6*Math.sqrt(l.source.deg+l.target.deg))*S.dist).strength(.32*S.link);
  sim.force("charge").strength(-280*S.repel).distanceMax(620);
  sim.force("x").strength(.04*S.center);sim.force("y").strength(.04*S.center);
  sim.force("collide").radius(n=>R(n)+4);
}
applyForces();
function reheat(a){if(!S.freeze){sim.alpha(a).restart();}draw.dirty=true;}

/* ---------- visibility ---------- */
function visibleReal(n){return !n.ghost&&!hiddenTypes.has(baseType(n.type))&&!hiddenAreas.has(n.group)
  &&!hiddenConf.has(n.conf||"")&&(!local||local.has(n.id));}
function visible(n){
  if(!n.ghost)return visibleReal(n);
  if(!S.ghosts)return false;
  if(local&&!local.has(n.id))return false;
  return [...outL[n.id],...inL[n.id]].some(m=>byId[m]&&visibleReal(byId[m]));
}
function refilter(){
  const vn=NODES.filter(visible), vset=new Set(vn.map(n=>n.id));
  const vl=LINKS.filter(l=>vset.has(l.source.id||l.source)&&vset.has(l.target.id||l.target));
  sim.nodes(vn);linkF.links(vl);reheat(.5);
  const rn=vn.filter(n=>!n.ghost).length, rl=vl.filter(l=>!l.ghost).length,
        gp=vn.length-rn;
  document.getElementById("subline").textContent=
    `${rn} concept${rn===1?"":"s"} · ${rl} link${rl===1?"":"s"}`+
    (gp?` · ${gp} pending`:"")+` · OKF v0.1`;
}

/* ---------- zoom / drag ---------- */
let autoFit=true;
const zoom=d3.zoom().scaleExtent([.08,9])
  .on("zoom",ev=>{if(ev.sourceEvent){needsFit=false;autoFit=false;}draw.dirty=true;});
const cvSel=d3.select(cv);
function T(){return d3.zoomTransform(cv);}
cvSel.call(zoom.transform,d3.zoomIdentity.translate(W/2,H/2)); /* bloom starts centered */
function pick(px,py){const t=T(),[gx,gy]=t.invert([px,py]);
  const n=sim.find(gx,gy,26/t.k);
  return n&&visible(n)&&Math.hypot(n.x-gx,n.y-gy)<=R(n)+7/t.k?n:null;}
const drag=d3.drag().container(cv)
  .filter(ev=>!ev.button&&!!pick(...d3.pointer(ev,cv)))
  .subject(ev=>pick(...d3.pointer(ev,cv)))
  .on("start",ev=>{dragging=true;if(!ev.active&&!S.freeze)sim.alphaTarget(.3).restart();
    ev.subject.fx=ev.subject.x;ev.subject.fy=ev.subject.y;})
  .on("drag",ev=>{const t=T();ev.subject.fx+= ev.dx/t.k;ev.subject.fy+=ev.dy/t.k;draw.dirty=true;})
  .on("end",ev=>{dragging=false;if(!ev.active)sim.alphaTarget(0);
    ev.subject.fx=null;ev.subject.fy=null;});
cvSel.call(drag).call(zoom).on("dblclick.zoom",null);
cv.addEventListener("mousemove",ev=>{if(dragging)return;
  const n=pick(ev.offsetX,ev.offsetY);
  if(n!==hover){hover=n;cv.style.cursor=n?"pointer":"default";retarget();draw.dirty=true;}});
cv.addEventListener("mouseleave",()=>{hover=null;retarget();draw.dirty=true;});
cv.addEventListener("click",ev=>{const n=pick(ev.offsetX,ev.offsetY);
  if(n)select(n.id,{fly:false});else clearSelect();});
cv.addEventListener("dblclick",ev=>{const n=pick(ev.offsetX,ev.offsetY);if(n)enterLocal(n.id);});

/* ---------- highlight targets ---------- */
function retarget(){
  const focusId=hover?hover.id:(selected||null);
  if(!focusId){NODES.forEach(n=>n.dimT=1);return;}
  const keep=new Set([focusId,...outL[focusId],...inL[focusId]]);
  NODES.forEach(n=>n.dimT=keep.has(n.id)?1:.11);
}

/* ---------- fit & fly ---------- */
function fit(dur=700){
  const vn=sim.nodes();if(!vn.length)return;
  let x0=1/0,y0=1/0,x1=-1/0,y1=-1/0;
  vn.forEach(n=>{x0=Math.min(x0,n.x);y0=Math.min(y0,n.y);x1=Math.max(x1,n.x);y1=Math.max(y1,n.y);});
  const pad=90,k=Math.min(2,.92/Math.max((x1-x0+1)/(W-pad*2),(y1-y0+1)/(H-pad*2)));
  const tf=d3.zoomIdentity.translate(W/2,H/2).scale(k).translate(-(x0+x1)/2,-(y0+y1)/2);
  (reduceMotion?cvSel:cvSel.transition().duration(dur).ease(d3.easeCubicInOut)).call(zoom.transform,tf);
}
function flyTo(n,dur=650){
  const dw=document.body.classList.contains("drawer-open")
    ?Math.min(drawer.getBoundingClientRect().width||400,W):0;
  if(dw>=W-60)return; // full-screen reading — graph hidden, don't move the camera
  const k=Math.max(T().k,1.6);
  const tf=d3.zoomIdentity.translate(Math.max(W-dw,120)/2,H/2).scale(k).translate(-n.x,-n.y);
  (reduceMotion?cvSel:cvSel.transition().duration(dur).ease(d3.easeCubicInOut)).call(zoom.transform,tf);
}

/* ---------- render loop ---------- */
function lerp(a,b,t){return a+(b-a)*t;}
function draw(){
  requestAnimationFrame(draw);
  const active=sim.alpha()>sim.alphaMin()&&!S.freeze;
  let fading=false;
  NODES.forEach(n=>{if(Math.abs(n.dim-n.dimT)>.004){n.dim=lerp(n.dim,n.dimT,reduceMotion?1:.16);fading=true;}else n.dim=n.dimT;});
  if(!active&&!fading&&!draw.dirty)return;
  draw.dirty=false;
  const t=T(),k=t.k;
  ctx.setTransform(DPR,0,0,DPR,0,0);
  ctx.fillStyle=SURF;ctx.fillRect(0,0,W,H);
  ctx.translate(t.x*1,t.y*1);ctx.scale(k,k);
  const vn=sim.nodes(),vl=linkF.links();
  const focus=hover||((selected&&byId[selected])||null);
  /* edges */
  const ew=Math.max(.3,.9*S.edge)/k;
  vl.forEach(l=>{
    const d=Math.min(l.source.dim,l.target.dim);
    const hl=focus&&(l.source.id===focus.id||l.target.id===focus.id)&&d>.5;
    ctx.globalAlpha=hl?(l.ghost?.6:.85):(l.ghost?.22:.38)*d;
    ctx.strokeStyle=hl?EDGE_HL:EDGE;
    ctx.lineWidth=hl?ew*1.7:ew;
    if(l.ghost)ctx.setLineDash([4/k,3/k]);
    ctx.beginPath();ctx.moveTo(l.source.x,l.source.y);ctx.lineTo(l.target.x,l.target.y);ctx.stroke();
    if(l.ghost)ctx.setLineDash([]);
    if(S.arrows&&(hl||k>1.15)){
      const dx=l.target.x-l.source.x,dy=l.target.y-l.source.y,len=Math.hypot(dx,dy)||1;
      const ux=dx/len,uy=dy/len,rt=R(l.target)+2/k,ax=l.target.x-ux*rt,ay=l.target.y-uy*rt,s=4.6/k;
      ctx.fillStyle=hl?EDGE_HL:EDGE;ctx.beginPath();
      ctx.moveTo(ax,ay);ctx.lineTo(ax-ux*s*1.9-uy*s,ay-uy*s*1.9+ux*s);
      ctx.lineTo(ax-ux*s*1.9+uy*s,ay-uy*s*1.9-ux*s);ctx.closePath();ctx.fill();
    }
  });
  /* nodes */
  vn.forEach(n=>{
    const r=R(n),isF=focus&&n.id===focus.id,isSel=selected===n.id;
    ctx.globalAlpha=n.dim;
    if(n.ghost){ /* pending link — hollow dashed dot (§5.3: declared, not yet written) */
      ctx.strokeStyle=MUTED;ctx.lineWidth=1.1/k;ctx.setLineDash([2.6/k,2.2/k]);
      ctx.globalAlpha=n.dim*.85;
      ctx.beginPath();ctx.arc(n.x,n.y,r,0,6.2832);ctx.stroke();ctx.setLineDash([]);
      return;
    }
    if((isF||isSel)&&!reduceMotion){ctx.shadowColor=colorOf(n);ctx.shadowBlur=16*k;}
    ctx.fillStyle=colorOf(n);
    ctx.beginPath();ctx.arc(n.x,n.y,r,0,6.2832);ctx.fill();
    ctx.shadowBlur=0;
    if(S.rings&&CONF[n.conf]){ctx.strokeStyle=CONF[n.conf];ctx.lineWidth=1.1/k;
      ctx.globalAlpha=n.dim*.95;
      ctx.beginPath();ctx.arc(n.x,n.y,r+1.9/k,0,6.2832);ctx.stroke();ctx.globalAlpha=n.dim;}
    if(S.orphHl&&realInDeg[n.id]===0){ctx.strokeStyle=INK2;ctx.lineWidth=1/k;
      ctx.setLineDash([3/k,2.4/k]);
      ctx.beginPath();ctx.arc(n.x,n.y,r+3.4/k,0,6.2832);ctx.stroke();ctx.setLineDash([]);}
    if(isSel){ctx.strokeStyle=INK;ctx.lineWidth=1.2/k;
      ctx.beginPath();ctx.arc(n.x,n.y,r+(S.rings&&CONF[n.conf]?4/k:2.4/k),0,6.2832);ctx.stroke();}
  });
  /* labels — semantic zoom: fade in as you zoom past the threshold */
  const gA=Math.max(0,Math.min(1,(k-.55*S.fade)/.45));
  ctx.textAlign="center";ctx.textBaseline="top";
  vn.forEach(n=>{
    const isF=(focus&&n.id===focus.id)||selected===n.id;
    const a=(isF?1:gA*(n.ghost?.55:Math.min(1,.3+n.deg*.12)))*n.dim;
    if(a<.03)return;
    const fs=(isF?12:10.5)/k;
    ctx.font=(isF?"600 ":n.ghost?"italic ":"")+fs+"px system-ui,-apple-system,'Segoe UI',sans-serif";
    ctx.globalAlpha=a;
    ctx.fillStyle=isF?INK:(n.ghost?MUTED:INK2);
    const y=n.y+R(n)+4/k;
    ctx.strokeStyle=SURF;ctx.lineWidth=2.5/k;ctx.lineJoin="round";
    ctx.strokeText(n.title,n.x,y);ctx.fillText(n.title,n.x,y);
  });
  ctx.globalAlpha=1;
  if(needsFit&&sim.alpha()<.05){needsFit=false;fit(reduceMotion?0:900);}
}
sim.on("tick",()=>{draw.dirty=true;});
sim.on("end",()=>{if(autoFit)fit(reduceMotion?0:600);});
draw.dirty=true;requestAnimationFrame(draw);
cv.classList.add("ready");

/* ---------- selection / drawer ---------- */
const drawer=document.getElementById("drawer");
function esc(s){return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function relRow(id){const n=byId[id];const c=n?colorOf(n):MUTED;
  return `<a data-go="${esc(id)}"><span class="dot" style="background:${c}"></span>${esc(n?n.title:id)}</a>`;}
function resolveHref(fromId,href){
  if(/^[a-z][a-z0-9+.-]*:/.test(href))return{ext:href};
  let h=href.split("#")[0];if(!h.endsWith(".md"))return null;
  h=h.slice(0,-3);
  const base=fromId.includes("/")?fromId.slice(0,fromId.lastIndexOf("/")).split("/"):[];
  const parts=h.startsWith("/")?h.slice(1).split("/"):base.concat(h.split("/"));
  const out=[];for(const p of parts){if(p==="."||p==="")continue;if(p==="..")out.pop();else out.push(p);}
  return{id:out.join("/")};
}
function select(id,{fly=true}={}){
  const n=byId[id];if(!n)return;
  if(n.ghost){toast("Pending link — concept not written yet (§5.3)");return;}
  selected=id;retarget();draw.dirty=true;
  document.getElementById("dbadges").innerHTML=
    `<span class="badge type" style="background:${colorOf(n)}">${esc(n.type)}</span>`+
    `<span class="badge conf" style="color:${CONF[n.conf]||MUTED};border-color:${CONF[n.conf]||"var(--hairline)"}">● ${CONF_LABEL[n.conf]??esc(n.conf)}</span>`+
    (n.stype?`<span class="badge st">${esc(n.stype)}</span>`:"");
  document.getElementById("dtitle").textContent=n.title;
  document.getElementById("ddesc").textContent=n.description||"";
  document.getElementById("dtags").innerHTML=(n.tags||[]).map(t=>`<span class="tag">#${esc(String(t))}</span>`).join("");
  const outs=outL[id],ins=inL[id];
  document.getElementById("dout").innerHTML=outs.length?`<h4>Links to · ${outs.length}</h4>`+outs.map(relRow).join(""):"";
  document.getElementById("din").innerHTML=ins.length?`<h4>Cited by · ${ins.length}</h4>`+ins.map(relRow).join(""):"";
  const md=document.getElementById("dmd");
  md.innerHTML=n.body?marked.parse(n.body):"<span style='color:var(--muted)'>empty body</span>";
  md.querySelectorAll("a[href]").forEach(a=>{
    const r=resolveHref(id,a.getAttribute("href")||"");
    if(!r){a.removeAttribute("href");return;}
    if(r.ext){a.target="_blank";a.rel="noopener";return;}
    a.addEventListener("click",ev=>{ev.preventDefault();
      if(byId[r.id])select(r.id);else toast("Pending link — concept not written yet (§5.3)");});
  });
  document.getElementById("dpath").textContent=id+".md";
  drawer.querySelectorAll("[data-go]").forEach(a=>a.onclick=()=>select(a.getAttribute("data-go")));
  drawer.classList.add("open");document.body.classList.add("drawer-open");
  document.body.classList.toggle("drawer-max",drawer.classList.contains("max"));
  document.getElementById("dbody").scrollTop=0;
  if(fly)flyTo(n);
}
function clearSelect(){selected=null;drawer.classList.remove("open");
  document.body.classList.remove("drawer-open","drawer-max");retarget();draw.dirty=true;}
document.getElementById("dclose").onclick=clearSelect;
function applyRead(){
  S.readfs=Math.max(12,Math.min(20,S.readfs));
  S.readw=Math.max(540,Math.min(1080,S.readw));
  document.documentElement.style.setProperty("--readfs",S.readfs+"px");
  document.documentElement.style.setProperty("--readw",S.readw+"px");
}
applyRead();
function toggleMax(){
  const on=drawer.classList.toggle("max");
  document.body.classList.toggle("drawer-max",on&&drawer.classList.contains("open"));
  document.getElementById("dmax").title=on?"Back to side panel (E)":"Expand for reading (E)";
  if(on)applyRead();
}
document.getElementById("dmax").onclick=toggleMax;
document.getElementById("rfMinus").onclick=()=>{S.readfs-=1;applyRead();save();};
document.getElementById("rfPlus").onclick=()=>{S.readfs+=1;applyRead();save();};
document.getElementById("rwMinus").onclick=()=>{S.readw-=60;applyRead();save();};
document.getElementById("rwPlus").onclick=()=>{S.readw+=60;applyRead();save();};
document.getElementById("dlocal").onclick=()=>{if(selected)enterLocal(selected);};

/* ---------- local graph ---------- */
function enterLocal(id,depth=2){
  const keep=new Set([id]);let frontier=[id];
  for(let d=0;d<depth;d++){const nx=[];
    frontier.forEach(f=>[...outL[f],...inL[f]].forEach(m=>{if(!keep.has(m)){keep.add(m);nx.push(m);}}));
    frontier=nx;}
  local=keep;refilter();select(id,{fly:false});needsFit=true;autoFit=true;
  document.getElementById("localName").textContent=byId[id].title;
  document.getElementById("localPill").classList.add("on");
}
document.getElementById("localExit").onclick=()=>{local=null;refilter();needsFit=true;autoFit=true;
  document.getElementById("localPill").classList.remove("on");};

/* ---------- search ---------- */
const sInput=document.getElementById("search"),hits=document.getElementById("hits");
let hitIds=[],hitSel=-1;
function renderHits(q){
  q=q.trim().toLowerCase();
  if(!q){hits.classList.remove("open");hitIds=[];return;}
  const scored=NODES.filter(n=>!n.ghost&&visible(n)).map(n=>{
    const hay=(n.title+" "+n.id+" "+(n.tags||[]).join(" ")+" "+n.type).toLowerCase();
    const i=hay.indexOf(q);return i<0?null:{n,score:(n.title.toLowerCase().startsWith(q)?0:1)*100+i};
  }).filter(Boolean).sort((a,b)=>a.score-b.score).slice(0,8);
  hitIds=scored.map(s=>s.n.id);hitSel=scored.length?0:-1;
  hits.innerHTML=scored.map((s,i)=>`<div class="hit${i===0?" sel":""}" data-id="${esc(s.n.id)}" role="option">
    <span class="dot" style="background:${colorOf(s.n)}"></span>
    <span class="t">${esc(s.n.title)}</span><span class="p">${esc(s.n.group)}</span></div>`).join("");
  hits.classList.toggle("open",scored.length>0);
  hits.querySelectorAll(".hit").forEach(h=>h.onclick=()=>{go(h.getAttribute("data-id"));});
}
function go(id){hits.classList.remove("open");sInput.blur();select(id);}
sInput.addEventListener("input",()=>renderHits(sInput.value));
sInput.addEventListener("keydown",ev=>{
  if(ev.key==="Enter"&&hitSel>=0&&hitIds[hitSel])go(hitIds[hitSel]);
  else if(ev.key==="ArrowDown"||ev.key==="ArrowUp"){ev.preventDefault();
    hitSel=Math.max(0,Math.min(hitIds.length-1,hitSel+(ev.key==="ArrowDown"?1:-1)));
    hits.querySelectorAll(".hit").forEach((h,i)=>h.classList.toggle("sel",i===hitSel));}
  else if(ev.key==="Escape"){sInput.value="";renderHits("");sInput.blur();}});
document.addEventListener("click",ev=>{if(!ev.target.closest("#searchWrap"))hits.classList.remove("open");});

/* ---------- legends ---------- */
function buildLegends(){
  const tc=document.getElementById("typeChips"),MAX=10;
  const byArea=S.colorBy==="area";
  const ord=byArea?areaOrder:typeOrder, cnt=byArea?areaCount:typeCount,
        col=byArea?areaColor:typeColor, hidden=byArea?hiddenAreas:hiddenTypes;
  tc.innerHTML=ord.map((t,i)=>`<span class="chip${i>=MAX?" extra":""}${hidden.has(t)?" off":""}" data-key="${esc(t)}"${i>=MAX?' style="display:none"':""}>
    <span class="dot" style="background:${col[t]}"></span>${esc(t)}<span class="n">${cnt[t]}</span></span>`).join("")
    +(ord.length>MAX?`<span class="chip" id="moreChip">+${ord.length-MAX} more</span>`:"");
  const more=document.getElementById("moreChip");
  if(more)more.onclick=()=>{const open=more.dataset.open==="1";
    tc.querySelectorAll(".extra").forEach(e=>e.style.display=open?"none":"flex");
    more.dataset.open=open?"0":"1";more.textContent=open?`+${ord.length-MAX} more`:"less";};
  tc.querySelectorAll(".chip[data-key]").forEach(ch=>ch.onclick=()=>{
    const t=ch.getAttribute("data-key");
    hidden.has(t)?hidden.delete(t):hidden.add(t);
    ch.classList.toggle("off");refilter();});
  const confCount={};REAL.forEach(n=>{const c=n.conf||"";confCount[c]=(confCount[c]||0)+1;});
  const order=["high","medium","low",""];
  document.getElementById("confChips").innerHTML=order.filter(c=>confCount[c]).map(c=>
    `<span class="chip" data-conf="${c}"><span class="ringdot" style="border-color:${CONF[c]||MUTED}"></span>${CONF_LABEL[c]}<span class="n">${confCount[c]}</span></span>`).join("");
  document.querySelectorAll("#confChips .chip").forEach(ch=>ch.onclick=()=>{
    const c=ch.getAttribute("data-conf");
    hiddenConf.has(c)?hiddenConf.delete(c):hiddenConf.add(c);
    ch.classList.toggle("off");refilter();});
}
buildLegends();

/* ---------- settings ---------- */
const panel=document.getElementById("settings"),gear=document.getElementById("gearBtn");
gear.onclick=()=>{const open=panel.classList.toggle("open");gear.classList.toggle("on",open);
  gear.setAttribute("aria-expanded",open);};
document.addEventListener("click",ev=>{
  if(!ev.target.closest("#settings")&&!ev.target.closest("#gearBtn")){
    panel.classList.remove("open");gear.classList.remove("on");}});
function bindRange(id,key,onchange){
  const el=document.getElementById(id),out=el.nextElementSibling;
  el.value=S[key];out.value=Number(S[key]).toFixed(2).replace(/\.?0+$/,"");
  el.addEventListener("input",()=>{S[key]=+el.value;out.value=Number(el.value).toFixed(2).replace(/\.?0+$/,"");
    onchange();save();});
}
function bindSwitch(id,key,onchange){
  const el=document.getElementById(id);el.checked=!!S[key];
  el.addEventListener("change",()=>{S[key]=el.checked;onchange();save();});
}
function save(){try{localStorage.setItem("okfviz:__NAME__",JSON.stringify(S));}catch(e){}}
const forceChange=()=>{applyForces();reheat(.5);};
bindRange("fCenter","center",forceChange);bindRange("fRepel","repel",forceChange);
bindRange("fLink","link",forceChange);bindRange("fDist","dist",forceChange);
bindRange("dSize","size",()=>{sim.force("collide").radius(n=>R(n)+2.5);reheat(.25);});
bindRange("dEdge","edge",()=>draw.dirty=true);
bindRange("dFade","fade",()=>draw.dirty=true);
bindSwitch("dArrows","arrows",()=>draw.dirty=true);
bindSwitch("dRings","rings",()=>draw.dirty=true);
bindSwitch("dGhosts","ghosts",()=>refilter());
bindSwitch("dOrph","orphHl",()=>draw.dirty=true);
bindSwitch("dFreeze","freeze",()=>{S.freeze?sim.stop():sim.alpha(.3).restart();draw.dirty=true;});
const segBy=document.getElementById("dColorBy");
segBy.querySelectorAll("button").forEach(b=>{
  if(b.dataset.v===S.colorBy)segBy.querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));
  b.onclick=()=>{S.colorBy=b.dataset.v;save();
    segBy.querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));
    buildLegends();draw.dirty=true;};});
document.getElementById("fitBtn").onclick=()=>fit();
const legBtn=document.getElementById("legBtn"),legEl=document.getElementById("legend");
legBtn.onclick=()=>{const open=legEl.classList.toggle("open");
  legBtn.textContent=open?"Legend ▴":"Legend ▾";};

/* ---------- misc ---------- */
let toastT=null;
function toast(msg){const el=document.getElementById("toast");el.textContent=msg;el.classList.add("show");
  clearTimeout(toastT);toastT=setTimeout(()=>el.classList.remove("show"),2200);}
document.addEventListener("keydown",ev=>{
  if(ev.key==="Escape"){if(panel.classList.contains("open")){panel.classList.remove("open");gear.classList.remove("on");}
    else if(drawer.classList.contains("open")&&drawer.classList.contains("max"))toggleMax();
    else if(drawer.classList.contains("open"))clearSelect();
    else if(local)document.getElementById("localExit").click();}
  else if(ev.key==="/"&&document.activeElement!==sInput){ev.preventDefault();sInput.focus();}
  else if(ev.key.toLowerCase()==="f"&&document.activeElement!==sInput)fit();
  else if(ev.key.toLowerCase()==="e"&&document.activeElement!==sInput
          &&drawer.classList.contains("open"))toggleMax();});
document.addEventListener("visibilitychange",()=>{if(document.hidden)sim.stop();
  else if(!S.freeze&&sim.alpha()>sim.alphaMin())sim.restart();});
setInterval(()=>{if(hover||selected)retarget();},400); /* keep highlight honest after sim moves */
retarget();refilter();
if(!NODES.length){toast("This gem has no concepts yet.");}
/* test/debug hook */
window.__okf={select,fit,enterLocal,state:S,nodes:NODES};
})();
</script></body></html>"""


def render(bundle: Path, out: Path):
    nodes, edges, real_edges = build(bundle)
    real_nodes = len([n for n in nodes if not n.get("ghost")])
    name = bundle.resolve().name
    html = (HTML.replace("__NAME__", name)
            .replace("__N__", str(real_nodes)).replace("__E__", str(real_edges))
            .replace("__NODES__", json.dumps(nodes, default=str))
            .replace("__EDGES__", json.dumps(edges, default=str)))
    out.write_text(html, encoding="utf-8")
    return real_nodes, real_edges


def main() -> int:
    ap = argparse.ArgumentParser(description="Render an OKF bundle as a self-contained HTML graph.")
    ap.add_argument("bundle", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None)
    args = ap.parse_args()
    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2
    out = args.out or (args.bundle / "viz.html")
    n, e = render(args.bundle, out)
    print(f"rendered {n} concepts, {e} links -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
