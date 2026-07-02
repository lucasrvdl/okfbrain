# 🧠 okfbrain

**Build fidelity-first digital "brains" — knowledge bases any AI can read — from a single phrase.**

okfbrain is a **single, intent-driven agent skill** (Claude Code first, any harness
welcome) that turns any subject into
an [Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
(OKF) **"brain"**: a folder of cross-linked markdown that humans, Obsidian, and any AI
can read — with **per-domain fidelity**, **provenance**, and **explicit gaps** — and
then **grows it, autonomously, until it covers the field**. The "brain" is a metaphor,
and a modest one: it's all just markdown files.

*A rigorous superset of the "LLM wiki" pattern: wikis that mechanically verify their
own quotes, grown by fleets of cheap models under strong audit.*

> You say: `learn about Stoicism`.
> It researches, distills into cross-linked concepts, marks what's missing,
> validates, and draws the graph.

## Why
RAG re-derives knowledge from raw chunks at query time and can miss what matters.
A *brain* stores **curated, cross-linked concepts** an agent reads and updates
directly. okfbrain adds what generic tools don't:
- **Fidelity by profile** — sacred = verbatim + faithful transliteration; health = scientific source;
  legal = exact article; etc.
- **Provenance** — every concept carries `source_type` + `confidence`; the graph colors
  node borders by confidence.
- **Source discernment** — clean digital e-text is quoted verbatim; corrupted OCR is
  refused and marked as a gap. Never invents.
- **Explicit gaps** — a broken link = "not yet written": visible, closeable.
- **Portable** — just markdown. Obsidian, the bundled graph, or any AI. No lock-in.

## One skill, intent-driven
Instead of rigid subcommands, **`okfbrain` is a single skill of directives**. You say
what you want in natural language and the AI infers the operation:
- *learn / build* a subject → full method on a new brain
- *expand / deepen / close gaps* → focused research on an existing brain
- *edit* → add / remove / fix one concept
- *audit* → read-only health + gaps + fidelity check
- *teach* → read-only tutoring, anchored in the brain
- *merge* → hierarchical umbrella of brains
- *loop* → autonomous audit→expand cycles (doctrine in `reference/LOOP.md`)

The non-negotiables are always on: never invent, gaps explicit, provenance on every
concept, validate at the end.

## What's new in 0.10 — semantic search + the LLM-Wiki complements
- **`okf_embed.py`**: humble-hardware semantic index — Model2Vec STATIC embeddings
  (no attention, no torch, no GPU, zero LLM tokens; multilingual model downloaded
  once). Incremental by content hash; lives in `_index/` INSIDE the brain, so the
  index travels with the folder. 45 concepts embed in <1s on CPU.
- **Hybrid search**: `okf_search.py` fuses BM25 + cosine (RRF) automatically when
  the index exists — synonym queries now work ("superhomem" finds Übermensch);
  graceful lexical fallback without the optional dep.
- **Ingest intent** (Karpathy LLM-Wiki pattern): absorb ONE source — immutable raw
  save, source node, update the 5–15 related concepts, wire links both ways.
- **Contradiction protocol** (non-negotiable): new evidence vs existing concept ⇒
  flagged `# Contradiction` section quoting both sources — never silent overwrite.
- **Compounding answers**: an Ask that synthesizes something unwritten offers to
  save itself as a concept, citations included.

## What's new in 0.9 — concurrency-safe, self-testing
- **Brain lock**: one loop per brain at a time (`.okf-loop.lock` with pid/host;
  `--force-unlock` for stale locks) — two writers on `_loop-state.md` was the last
  easy way to corrupt a brain.
- **Process-tree kill on timeout** (Windows included) — no more zombie integrators
  finishing behind the driver's back.
- **Queue items reach executors whole**: continuation lines (the architect's source
  pointers) are folded into the item instead of being dropped.
- **`--log-dir`**: full prompt+output of every agent call on disk, labeled per
  cycle/miner/integrator — debuggable waves.
- **`okf_selftest.py` + CI**: 22 black-box checks over a throwaway mini-brain
  (all scripts, guards and parsers); GitHub Actions runs it on every push. The
  selftest already paid for itself: it caught a same-line `--from/--to` excerpt
  edge case, fixed in this release.

## What's new in 0.8 — fan-out (parallel miners)
`okf_loop.py --miners N --miner-executor flash --integrate-executor audit`: N cheap
executors mine queue items IN PARALLEL, write-fenced to `_staging/<item>/` (draft +
raw sources — never the brain); ONE strong integrator then source-traces each draft,
embeds verbatim via okf_excerpt, writes the real concepts and passes the gates.
`--no-integrate` leaves staging for the master session to integrate in-session.
Doctrine: SOLO by default — fan-out only when the user asks. Baptized on a live
brain (3 DeepSeek miners + Sonnet integrator, 3/3 integrated, strict clean); the
baptism fixes shipped with it: staggered miner starts (parallel CLIs fight over a
local db), `_staging/` excluded from validation, claude profiles reordered (variadic
--allowedTools swallowed the trailing prompt), dedicated integrator timeout (2x,
min 30min) with a Windows survives-timeout warning.

## What's new in 0.7 — the driver trusts no one
Lessons from a full field run (an Opus master driving a DeepSeek executor through
9 concepts on a real brain):
- **Driver-enforced gates**: okf_loop re-runs okf_verify + okf_validate ITSELF after
  every cycle (baseline-delta aware) and hands new failures back to the executor for
  one fix pass — executor self-reports are never trusted.
- **Quoted-prose verification**: verify now checks “quoted spans” in prose against
  saved sources (the gate-evasion both pilot executors used); short spans and
  years/superlatives absent from staged sources become *framing hints* — the
  auditor's aim-list for the fabricated-bibliographic-framing vice.
- **Status splits knowledge vs sources** (`15 knowledge (+22 sources = 37)`).
- Doctrine: first-excerpt source sanity-check (mislabeled files become dead-ends,
  field-tested), foreground `--cycles 1` batches inside harness turns, masters
  never yield waiting on background notifications.

## What's new in 0.6 — executor profiles
`executors.json` maps friendly names to agent CLIs (OpenCode Go/Zen gateways,
OpenRouter, Ollama local/cloud, LM Studio, `claude -p`): set the model once,
run `okf_loop.py --executor flash --audit-executor audit` from any master
harness. Personal overrides in `~/.okfbrain/executors.json`; `--list-executors`
shows the fleet; placeholders are refused until edited. Field-certified
executors so far: Claude Haiku and DeepSeek V4 Flash (via opencode; needs
`permission: allow` config for non-interactive runs).

## What's new in 0.5 — cheap/local models without cheap results
Structure they follow; judgment they don't. 0.5 moves the judgment into scripts and a
stronger auditor, so DeepSeek/Gemma-class executors can grind brains safely:
- **Evidence-first**: sources saved into `_sources/`/`references/` BEFORE writing;
  **verbatim is never typed** (any model) — only `okf_excerpt.py` byte-copies, verified
  mechanically by the new `okf_verify.py`.
- **Script-checked stop-gate**: a "nothing-resolvable" claim is verified against
  `okf_status`; open items ⇒ rejected and pushed back into the next cycle prompt.
- **Micro-task cycles**: the loop injects queue head + open gaps into each prompt —
  strong model architects the map once, cheap model grinds the queue.
- **Producer/auditor split**: executor capped at `confidence: medium` + `needs-review`;
  `--audit-agent` (stronger model) source-trace re-reads the delta, promotes/demotes.
- **Sacred lockout**: below-audit-tier models never author sacred verbatim.

## What's new in 0.4
- **Ask intent** — "what does the brain say about X?": read-only answers strictly from the
  brain, citing concept ids; absent ⇒ declared gap, never filled from general knowledge.
- **`okf_search.py`** — in-brain BM25 with diacritic folding; mandatory pre-write dedup.
- **`okf_migrate.py`** — one-shot normalizer for pre-v2 brains (safe dry-run default).
- **Spaced repetition** — teach sessions schedule reviews (1→3→7→16→35d) in
  `_learning/progress.md` and can push them to a to-do integration (opt-in).
- **Optional git versioning** — offered once per brain; private remote for cross-machine sync.
- **Graph view**: pending links as dashed ghost nodes (§5.3 made visible), orphan
  highlighting, color-by-area mode; `okf_status` counts uncited concepts.

## What's new in 0.3
- **Graph view rebuilt Obsidian-style** — d3-force live physics on canvas (61 fps at 300+
  nodes), gentle bloom settle, drag springs, semantic-zoom label fading, neighborhood
  highlight with smooth dimming, wiki drawer (markdown, links, backlinks, provenance
  badges), double-click local graph with depth pill, search with fly-to, Obsidian-style
  force sliders, auto-fit that yields to the user. Colors follow the dataviz method:
  validated categorical palette by base type, status palette for confidence rings.

## What's new in 0.2
- **Growth doctrine (`reference/LOOP.md`)** — coverage map ≥2 levels anchored to a
  researched external outline of the field; growth axes so the queue never runs dry
  (new leaves, split fat concepts, deepen, typed nodes, de-orphan, grow the map);
  per-cycle anti-laziness floor; stop-gate that must be proven, never felt.
- **`okf_status.py`** — deterministic OBSERVE: any model, any harness sees the same
  brain X-ray (orphans, thin nodes, pending links, gaps, loop queue).
- **Anti-invention gate** — the *source-trace re-read*: every line must trace to a
  source read this run; structural validators can't catch inventions, this pass does.
- **Web-verbatim rule** — harness fetch tools paraphrase; verbatim from the web now
  requires a raw local download first (`curl`) + `okf_excerpt.py`, else it's a gap.
- **Multi-model consistency** — stress-tested by having Haiku and Sonnet execute the
  skill cold; every stumble became an explicit rule (link forms, area folders, strict
  frontmatter, `timestamp` field, log via script).
- **Provenance safety** — `okf_stamp.py --default` now only fills missing provenance
  (never silently overwrites a deliberate `low`); meta files excluded from viz/stamp.

## Engine
Deterministic Python scripts (run via [`uv`](https://docs.astral.sh/uv/), or
`py -3.11` / `python3` + `pyyaml`), in `skills/okfbrain/scripts/`:
- `okf_validate.py` — OKF v0.1 conformance checker.
- `okf_status.py` — deterministic observe/status report (orphans, thin nodes, uncited concepts, pending links, gaps, loop queue).
- `okf_search.py` — BM25 search inside the brain, diacritic-folded (`diksa` finds "Dīkṣā"); powers Ask and pre-write dedup.
- `okf_migrate.py` — normalize pre-v2 brains (frontmatter, profile line, prose gaps → checkboxes); dry-run by default.
- `okf_visualize.py` — Obsidian-grade graph view (d3-force on canvas): live physics with
  spring dragging, semantic-zoom labels, hover that dims to the neighborhood, wiki drawer
  with rendered markdown + backlinks, local-graph mode, search with fly-to, force/display
  sliders, type + confidence legends. Self-contained `viz.html`.
- `okf_stamp.py` — bulk-stamp provenance into frontmatter (fills missing; never silently overwrites).
- `okf_excerpt.py` — embed a byte-exact verbatim passage from a local source into `references/`.
- `okf_log.py` — dated `date · harness · model · action` entries in `log.md`.
- `okf_verify.py` — MECHANICAL fidelity: every blockquote must byte-match a saved source
  (`references/`/`_sources/`); citations presence; weasel-line lint. `--strict` gates
  weak-model output.
- `okf_loop.py` — headless audit→expand loop hardened for cheap executors: injects the
  machine-read state (queue head, open gaps) into every cycle prompt, REJECTS
  "nothing-resolvable" while okf_status shows open items, `--confidence-ceiling`, and
  `--audit-agent`/`--audit-every` for a stronger model to promote/demote the delta.

## Install
New machine in ~10 minutes: **[SETUP.md](SETUP.md)** (skill copy, Python, executors,
brain sync, smoke tests). Short version: copy `skills/okfbrain/` into
`~/.claude/skills/` (Claude Code) or the equivalent skills folder of your harness.

## Roadmap
- `okfbrain` deep audit — multi-model "fusion" audit.

## Credits & license
- OKF spec (`skills/okfbrain/reference/SPEC.md`) — Google Cloud Data team, **Apache-2.0**, vendored.
- `okf_validate.py` & `okf_visualize.py` — derived from
  [okf-skills](https://github.com/scaccogatto/okf-skills) by Marco Boffo (**MIT**).
- Everything else — **MIT © 2026 Lucas Lucena**.
