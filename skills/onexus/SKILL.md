---
name: onexus
description: >-
  Build and maintain fidelity-first digital "Gems" — OKF knowledge bases: folders
  of cross-linked markdown any AI can read — and grow them to full field coverage,
  autonomously, in audit→expand loops. (Formerly okfbrain: a "brain"/"cérebro"
  is now called a Gem.)
  ONE intent-driven skill: say what you want in natural language (learn a subject,
  deepen it, fix/add a concept, ask it questions, audit, teach from it, merge
  Gems, or loop) and it applies the OKF method with per-domain fidelity,
  provenance, and explicit gaps. Triggers: "/onexus ...", "learn about X" /
  "aprenda sobre X", "build a Gem" / "monte uma Gem", "what does the Gem
  say about X" / "o que a Gem diz sobre X", "ingest this source" / "ingere
  essa fonte na Gem", "audit" / "audita", "teach me" / "me ensina", "merge" /
  "junta", "keep improving in a loop" / "fica melhorando em loop".
user-invocable: true
argument-hint: "<what you want, in natural language> (e.g. learn about X using these sources)"
allowed-tools: Read Write Edit Bash Grep Glob WebSearch WebFetch AskUserQuestion
---

# onexus — fidelity-first digital "Gems" in the Open Knowledge Format

A "Gem" here is a metaphor, and a modest one: just a folder of cross-linked
markdown files a human or any AI can read, query and extend. No magic implied.

ONE skill, driven by INTENT: the user says what they want in plain language; you
infer the operation (table below) — there are **no rigid subcommands**. Format =
Open Knowledge Format v0.1 — `reference/SPEC.md` is the normative truth; read it
before non-trivial structural work. **Loop / grow-to-done intent ⇒ read
`reference/LOOP.md` first — MANDATORY, every time it isn't verbatim in context.**

**Prime directive — every Gem is:**
1. **FAITHFUL** — every claim sourced; verbatim where the profile demands; no
   invention, ever. Fidelity is never traded for size.
2. **BIG** — it covers the FIELD. Map the subject to an authoritative outline and
   drive toward full coverage in atomic concepts: a serious field ⇒ hundreds of
   small linked files, not dozens of fat ones. Size comes from coverage, never
   from padding — a filler concept is worse than a declared gap. An EXPLICIT user
   bound ("small", "quick", "~N concepts") overrides BIG: honor it and declare
   the uncovered rest of the field in Gaps.
3. **SELF-EXPANDING** — map, queue, and state live ON DISK, so ANY model (Opus,
   Sonnet, Haiku, another vendor's) under ANY harness (Claude Code, Codex, Gemini
   CLI, a plain script) can open the Gem cold and keep growing it by following
   them. Write every handoff as if a smaller model in a different harness
   executes it.
4. **AUTONOMOUS** — act without asking. Ask ONLY before removing/overwriting
   existing content, or on a genuine scope fork. Never stall on a question you can
   answer with the conservative faithful choice — record it and keep working.

## What a "Gem" is

An OKF bundle — default base **`~/Documents/Onexus/<gem>/`** (same path on
macOS/Windows/Linux; a `Desktop/Onexus` shortcut may point there). Legacy base
`~/Documents/OKFBrain/` (this skill's pre-rebrand home): if it exists and
`~/Documents/Onexus` does not, KEEP using it — never split Gems across two
bases. The user may
save a Gem **anywhere** by saying so. A Gem is a folder of `.md` concept files
(**1 concept = 1 file**) with YAML frontmatter, cross-linked, navigable by any AI,
by Obsidian, and by the user. One subject = one Gem; umbrellas nest Gems.

## NON-NEGOTIABLE directives (always, regardless of intent)

- **Never invent — everything is research-based.** Copy **verbatim** what the
  profile requires (sacred verses, laws, formulas, doses, quotes). Every claim
  traces to a source you actually read; if you can't source it, it's a gap, not a
  guess.
- **Verbatim blocks are never typed** — any model, any size: they are byte-copied
  by `okf_excerpt.py` from a source file saved in the Gem (`references/`,
  `_sources/`), and `okf_verify.py` checks the match mechanically.
- **Contradictions are flagged, never silently resolved.** New evidence that
  contradicts an existing concept ⇒ add a `# Contradiction` (or `# Contradição`)
  section quoting BOTH sources with provenance, adjust `confidence` to reflect
  the dispute, and open a gap entry to resolve it. Overwriting the old claim
  without the flag is invention by deletion.
- **Gaps are explicit, never silent** — exact format under "Gaps" below; plus
  `log.md`. A cross-link to a not-yet-written file is valid (§5.3) = pending
  knowledge.
- **Provenance on every concept:** `source_type` (digital|ocr|web|mixed|none) +
  `confidence` (high|medium|low) — see `PROFILES.md`. OCR / unverified verbatim ⇒
  low.
- **Validate at the end of every run that wrote files**; fix every ERROR. Warnings
  on `_`-meta files are tolerated noise — never "fix" meta files to silence them.
- **Gem content in the user's language** (default: the language of their
  request). The framework is English; sacred texts keep original script +
  transliteration.
- **Cross-links are standard markdown RELATIVE links.** Same folder =
  `[title](other.md)`; another area = `[title](../area/concept.md)` — count the
  real folders; don't copy the `../` from examples blindly. NEVER Obsidian
  WikiLinks (`[[...]]` — Obsidian reads the standard form fine; the engine can't
  read WikiLinks), never `/`-leading (a DELIBERATE deviation from SPEC §5.1 for
  portability — don't "correct" it). After writing, `okf_status.py` must show
  your links as edges — 0 edges = your link paths are wrong.
- **Timestamps are real** — frontmatter field named exactly `timestamp` (ISO
  8601; not `created`/`date`), value from the system clock fetched once; never a
  guessed date.
- **File/folder names are kebab-case ASCII** (strip diacritics: `nao-verbal`, not
  `não-verbal`); the CONTENT keeps full diacritics.

## Resolve ONCE per session, then reuse (cache in `_loop-state.md` when looping)

- **SKILL_DIR** = the directory this SKILL.md lives in — you just read it, so you
  know the path. Canonical install: `~/.claude/skills/onexus`; other harnesses
  may vendor it elsewhere (search for `**/onexus/SKILL.md` if unsure). Do NOT
  rely on `$CLAUDE_SKILL_DIR` — it is often unset.
- **RUN** = `uv run <script>` if uv exists; else `py -3.11 <script>` on Windows /
  `python3 <script>` elsewhere (needs `pyyaml`). Test once; reuse the winner.
- **TODAY** = system date (`date -Iseconds` / `Get-Date -Format o`), fetched once.
- **Existing-Gem check** — before any create, list the TARGET base (the folder
  this run saves to: the user-given location if any, else the default base): if
  the subject's Gem already exists there, this is an EXPAND — never a duplicate
  folder, never an overwrite.

## Fidelity profile (choose per subject; see `PROFILES.md`)

sacred · health · legal · culinary · technical · history · philosophy · general —
the right rigor per kind of knowledge. The user may force it ("profile: health").
In doubt between two, the stricter wins.

## Anatomy of a great Gem (the quality bar)

- **Concepts live in AREA FOLDERS, never loose in the Gem root** — even a small
  Gem groups into 2–3 areas (the root holds only `index.md`, `log.md`,
  `references/`, `_`-meta, `viz.html`). Consistent shape at any size.
- **Atomic concepts** — one idea per file (~150–600 words of body). If a body
  explains 3+ separable, separately-sourceable ideas ⇒ SPLIT into linked child
  concepts. This is how Gems get big honestly.
- **Typed nodes** — vary `type` beyond `Concept`: `Person`, `Text`, `Practice`,
  `Method`, `Debate`, `Case`, `Glossary`, `Timeline`… A typed graph is a queryable
  graph. One file = one `type`: a mixed case takes the type of what the file
  primarily IS, and cross-links the other aspect.
- **Hubs** — every area folder has an `index.md`; big areas (≥5 concepts) also
  get a synthesis concept (an overview node) that links the area together.
- **Link density** — every concept links OUT to ≥2 related concepts (relative
  links) and should be linked TO by its area (no orphans).
- **Per-concept pass bar** — sourced body · provenance set · ≥2 relative
  cross-links · a citations section (`# Citations` / `# Fontes`) · frontmatter
  fields exactly as in `templates/concept.md` (copy the template; don't improvise
  field names).
- **Meta layers** (`_` prefix = meta, not knowledge): `_learning/` (tutor memory),
  `_loop-state.md` (growth state). Meta files still carry frontmatter `type`.

### Gaps (exact format, in the root `index.md`)

Heading in the Gem's language (`# Lacunas` in PT, `# Gaps` in EN), entries:

```
- [ ] <missing topic> — <which source is needed / why it's missing>
- [ ] blocked: needs <named unavailable source> — <topic>
- [-] <topic> — out of scope: <reason>
```

Closed gaps: flip to `- [x]` and move the line to `log.md` on the next pass.

## The method (create / expand)

1. **Scope** — subject, profile, user constraints.
2. **Coverage map, ≥2 levels** — RESEARCH an authoritative outline of the FIELD (a
   reference work's table of contents, a syllabus, a canonical taxonomy — looked
   up, not recalled): areas → topics, **every leaf topic ⇒ ≥1 concept**. The map
   is the yardstick "done" is measured against; the sources you happen to hold are
   NOT the map.
3. **Sources** — user-given first; then any local corpora/RAG folders the user
   has pointed you to, when plausibly relevant to the subject (resolve how to
   query each once; skip when clearly unrelated); then the web. Record where
   each thing came from. Cite ONLY pages you actually
   opened and read — never from a search-results synthesis (it blends many pages;
   the attribution lies). A failed fetch (403, timeout) is not a source: drop it
   or record the gap.
4. **Concepts** — distill into OKF docs per the anatomy above; verbatim where the
   profile requires; frontmatter (`type` + title/description/tags/timestamp +
   provenance); free body headings (`# Verse`, `# Dose`, `# Como aplicar`…);
   relative cross-links; split-when-fat. Content comes ONLY from sources read
   THIS run — never from your own memory of the subject.
5. **Structure** — one `index.md` per folder listing its contents. Frontmatter
   rules are STRICT: the root `index.md` frontmatter is EXACTLY
   `okf_version: "0.1"` and nothing else; every other `index.md` and `log.md`
   carry NO frontmatter at all. Record the chosen fidelity profile as a body
   line of the root `index.md` (e.g. `Perfil de fidelidade: general`) so future
   expanders know the rigor bar. Dated `log.md` at the root — `## YYYY-MM-DD`
   headings are pure dates; harness/model metadata goes in the entry line
   (that's what `okf_log.py` writes).
6. **Gaps** — diff reality against the phase-2 map; write the Gaps section in the
   exact format above.
7. **Fidelity** — per-profile check (fact-check / verbatim check / attribution);
   refute risky claims before writing them. Then the **source-trace re-read**:
   re-read every new concept asking, line by line, "which source that I read
   gives me this?" — anything untraceable (a remembered anecdote, an inferred
   superlative) is DELETED or moved to Gaps. `okf_verify.py` does the
   machine-checkable part (quote match, citations); the re-read covers what
   machines can't.
8. **Validate + visualize + report** — validator (fix ERRORs), regenerate
   `viz.html` whenever the graph changed, then report in the user's language:
   profile · sources used · #concepts by area · the honest gap list · paths ·
   and **the growth offer**: one ready-to-run loop command (e.g.
   `/onexus <gem> /loop`). If the user already asked for depth/completeness,
   don't offer — continue into the loop yourself.

## Intents (INFER from the request — not separate commands)

| Request looks like | Operation | Asking |
|---|---|---|
| learn/build X — no Gem yet | **Create**: full method 1–8 | never |
| learn X — Gem already exists | **Expand** the existing Gem (say so) | never |
| deepen / close gaps / grow area Y | **Expand** focused on Y, else worst gaps | never |
| add / fix one concept | **Edit** — surgical; update index + log | never |
| remove a concept | **Edit** — confirm FIRST | once |
| what does the Gem say about X? | **Ask** — answer FROM the Gem; a miss triggers learn-on-miss | never |
| ingest this URL / PDF / article / note | **Ingest** — absorb ONE source into the Gem | never |
| audit / review / check | **Audit** — READ-ONLY | never |
| audit and fix | Audit, THEN fix ERRORs (+confirmed removals) | removals only |
| teach / quiz / course / tour | **Teach** — read-only on knowledge; writes `_learning/` | never |
| merge / umbrella | **Merge** — COPY into subfolders | never |
| loop / keep improving / grow to done | **Loop** — read `reference/LOOP.md` NOW and follow it | never mid-loop |

- **Ask** = quick factual consult: locate the concepts (`okf_search.py`, then read
  them), answer ONLY from what they say, and cite each claim's concept id
  (`area/concept`). Never top up silently from general knowledge — whatever the
  Gem lacks goes through **learn-on-miss** (next bullet). Beyond that, no files
  are written — EXCEPT: if the answer synthesized something real that no concept
  states yet, OFFER in one line to save it as a concept (with the citations the
  answer already used). Explorations compound instead of evaporating in chat. (A
  longer session that turns into study ⇒ Teach.)
- **Learn-on-miss** (default inside Ask — asking teaches the Gem): when no
  concept answers the question, or answers only part of it, don't stop at "it's
  a gap":
  1. **Declare the miss** in one line, answering whatever IS covered from the
     Gem as usual.
  2. **Research the missing part** as a micro-Expand: sources actually read
     (user-pointed corpora first, then the web), at THIS Gem's fidelity
     profile. Your memory of the subject is still not a source.
  3. **Validate per profile** — fact-check, refute risky claims before relaying
     them; anything the profile wants verbatim enters only via saved raw source
     + `okf_excerpt.py`, never from a fetch summary.
  4. **Answer**, keeping Gem-claims (concept ids) visibly apart from fresh
     research (source citations).
  5. **Write it back**: dedup-search, then a proper concept in the right area
     (template frontmatter + provenance + ≥2 relative cross-links + area index
     updated + gates verify/validate), and `okf_log.py --kind Learn` naming the
     question it answers; if this closes an existing Gaps entry, flip it per the
     Gaps rule. Research that FAILED validation is delivered as explicitly
     uncertain and recorded as a Gaps entry, NOT a concept — a declared gap
     beats a weak concept.
  Log the question in `_learning/sessions.md` (asked-and-missed = a coverage
  signal for the next loop). The user can say "ask only" / "só a Gem" to
  skip research: then a miss is reported as a gap and nothing is written.
- **Ingest** = absorb ONE given source (URL, PDF, file, pasted text) — the
  source-push twin of the map-driven Expand:
  1. SAVE it immutable: raw download into `_sources/<date>-<slug>.<ext>` (or
     `okf_excerpt.py` the key passages into `references/`). Sanity-check the
     content matches what the source claims to be.
  2. Create/refresh the source's node (type `Text`/`Source`) with provenance.
  3. Find the 5–15 RELATED concepts (`okf_search.py`, hybrid) and UPDATE them:
     new evidence in, links wired both ways, contradictions flagged per the
     non-negotiable above.
  4. New topics the source opens ⇒ concepts (small Gems) or queue/map entries.
  5. Gates (verify --strict + validate), refresh `_index/` if present, and log
     `--kind Ingest` naming the source and every concept touched.
- **Expand never duplicates:** before writing, search the Gem
  (`okf_search.py <gem> "<topic>"`, plus grep for exact strings); if a concept
  exists, deepen/split it instead of adding a twin. Update the parent concept +
  indexes + log.
- **Audit** = validator `--json` + gap list + fidelity flags (`⚠` marks, missing
  sources, OCR, `confidence: low`, orphan concepts). **Never edit while
  auditing.**
- **Teach** teaches ONLY what's in the Gem, citing concepts; if it isn't there,
  say it's a gap — **don't fill from general knowledge**. A student question the
  Gem can't answer ⇒ note it (`_learning/sessions.md` to-revisit + Gaps) and
  run learn-on-miss AFTER the session — mid-lesson, the lesson comes first.
  Modes: tour / course / deep-dive / socratic / quiz. Every session updates
  `_learning/`.
- **Merge** = hierarchical umbrella: **COPY (don't move)** each Gem into a
  subfolder (skip `viz.html`; strip `okf_version` from each sub-Gem's root
  `index.md`); the NEW root `index.md` carries `okf_version: "0.1"` and maps the
  sub-Gems; stitch real cross-links (`../../<other>/...`). Originals stay
  intact. Re-nesting allowed.

## Embed sources (self-contained, portable Gems)

Prefer embedding the passage that **is** the concept (the verse, the law, the
formula) verbatim under `references/` over pointing at a path on this machine —
Gems must travel. Byte-exact, via the excerpt script:

```bash
<RUN> "<SKILL_DIR>/scripts/okf_excerpt.py" "<source-file>" "<gem>" "references/<name>.md" \
  --from "<start marker>" --to "<end marker>" --title "<Title>" --citation "<origin>"
```

(also `--lines A-B` or `--grep RE`). Set provenance to match the source. On the
FIRST excerpt from any source file, sanity-check its header/opening lines
against the work it claims to be — a mislabeled file is a dead-end to report,
never silent wrong evidence.

Embedding is for content the profile demands VERBATIM (verses, provisions,
formulas, key quotes) — ordinary prose needs only citations. **Verbatim from the
web:** harness fetch tools may summarize or paraphrase what they return (Claude
Code's WebFetch does) — NEVER trust their output as verbatim. Download the RAW
source to a local file first (e.g. `curl -L <url> -o <file>`), then excerpt
byte-exact from that file. No raw copy obtainable ⇒ the verbatim is a gap
(`⚠ verify against source`), never a paraphrase.

## Learning memory (`_learning/` — the Gem as a tutor that remembers)

- `progress.md` (type: Progress) — mastered / learning / not-yet-seen, mapped to
  concept ids — plus the **review schedule** (below).
- `sessions.md` (type: Sessions) — dated log: topic, questions, hits, to-revisit.
- `courses/<name>.md` (type: Course) — structured study paths through the Gem.

Teaching or answering ⇒ UPDATE these (question asked + got it or not; move
concepts across mastered/learning). Templates: `templates/learning-*.md`.

**Spaced repetition:** every teach/quiz session ends by scheduling reviews in
`progress.md` → "Revisões": answered well ⇒ next interval in the ladder
**1 → 3 → 7 → 16 → 35 days** (cap 35); missed ⇒ back to 1 day. Dates are real
(TODAY + interval). Start each teach session by checking for DUE reviews and
quizzing those first. If the session has a to-do integration (e.g. a TickTick
skill), OFFER ONCE per session to create the review tasks
("Revisar <concept> — Gem <gem>", due on the scheduled date) — never push
tasks without that one yes.

## Edit log (provenance of changes)

Every change appends a dated `date · harness · model · action` entry to `log.md`
— via the script (don't hand-format; it keeps `## YYYY-MM-DD` headings pure and
puts harness/model in the entry line):

```bash
<RUN> "<SKILL_DIR>/scripts/okf_log.py" "<gem>" --kind <Creation|Update|Expansion|Ingest|Embed|Edit|Learn|Merge|Deprecation|Loop> \
  --agent "<harness>" --model "<model>" --note "<what changed>"
```

## Versioning (optional — offer once, never impose)

A Gem is a folder, so git versions it for free. When creating a Gem (or when
asked), offer ONCE, in one line: *"version this Gem with git?"* If yes:
`git init` in the Gem, commit after every run that wrote files
(`git add -A && git commit -m "<kind>: <note>"` — same note as the `log.md`
entry), and for cross-machine sync offer a PRIVATE remote
(`gh repo create <gem> --private --source .`). Never init, commit elsewhere,
or push without that yes; `log.md` remains the human-readable history either way.

## The engine (deterministic — prefer scripts over judgment)

In `<SKILL_DIR>/scripts/`, run with RUN (see "Resolve ONCE"):
- `okf_validate.py <gem> [--strict] [--json]` — OKF v0.1 conformance; ERRORs
  must be fixed, always.
- `okf_status.py <gem> [--json]` — deterministic OBSERVE: counts by area/type,
  provenance histograms, orphans, thin nodes, UNCITED concepts, pending links,
  the Gaps section, loop-state summary. Start audits/expansions/loop cycles here.
- `okf_search.py <gem> "<query>" [--top N] [--json]` — search inside the Gem:
  BM25 diacritic-folded (`diksa` finds "Dīkṣā"), and HYBRID (+cosine via RRF)
  whenever `_index/embeddings.npz` exists — then synonyms work ("superhomem"
  finds Übermensch). Use it for Ask/Ingest, and ALWAYS before writing (dedup).
- `okf_embed.py <gem> [--model M] [--rebuild]` — build/refresh the semantic
  index: static embeddings (CPU-only, no GPU/torch/LLM tokens; multilingual
  model downloaded once), incremental by content hash, stored INSIDE the Gem
  (`_index/` is meta — it travels with the folder). Optional dep:
  `pip install model2vec numpy`; everything else works without it.
- `okf_migrate.py <gem> [--profile X] [--apply] [--backup <dir>]` — normalize a
  pre-v2 Gem (root-index frontmatter, profile line, prose gaps → checkboxes,
  stray frontmatter). DRY-RUN by default; `--apply` writes; use `--backup`.
- `okf_verify.py <gem> [--concept <id>] [--strict]` — MECHANICAL fidelity:
  citations present, every blockquote byte-matches a saved source under
  `references/`/`_sources/`, weasel-line lint. Run it on every concept you
  write; weak-model cycles run it `--strict`.
- `okf_visualize.py <gem>` — self-contained interactive HTML graph (`viz.html`).
- `okf_stamp.py <gem> <rel=source_type:confidence> ... [--default st:conf]` —
  bulk provenance.
- `okf_excerpt.py …` — verbatim source embedding (usage above).
- `okf_log.py …` — dated log entries (usage above).
- `okf_selftest.py` — 24 black-box checks over a throwaway mini-Gem; run it
  after ANY change to the skill (CI runs it on every push).
- `okf_loop.py <gem> (--cycles N|--minutes M|--until-dry|--forever)
  [--executor <name>] [--audit-executor <name>] [--miners N
  [--miner-executor <name>] [--no-integrate]]` — OPTIONAL headless driver for
  unattended runs WITHOUT this session (spawns a CLI agent per cycle; it does not
  inherit this session's access). `--miners N` = FAN-OUT mini-harness: N parallel
  miner agents per wave (ANY vendor via executors.json — DeepSeek, Ollama,
  OpenRouter…), write-fenced to `_staging/`, then a strong INTEGRATOR pass writes
  the Gem; `--no-integrate` mines one wave and hands `_staging/` to the master
  session (doctrine: LOOP.md "Fan-out"). Executor NAMES live in `executors.json`
  (SKILL_DIR; personal overrides in `~/.onexus/executors.json`, with legacy
  `~/.okfbrain/` still read; `--list-executors` shows them) — one config, any
  master harness. Interactive
  loops always use `reference/LOOP.md`, in-session.

## Templates

`templates/concept.md` · `index.md` · `log.md` · `loop-state.md` ·
`learning-progress.md` · `learning-sessions.md` · `learning-course.md`.

## Harness & OS notes

- This skill runs under ANY harness (Claude Code, Codex, Gemini CLI, …). Tool
  names here are generic — use your harness's equivalents for file search, text
  search, web search/fetch, and asking the user. Loops pace with the harness's
  scheduler when it has one; otherwise run cycles back-to-back in the session.
- **Sub-agent model policy:** in-session sub-agents (miners etc.) run ONLY on
  the models YOUR harness can spawn (Claude Code = Claude models). If the user
  names another vendor's model for them, say so in ONE line, offer the nearest
  harness tier (cost → small; fidelity → mid), and continue — never stall.
  ANY-vendor parallel mining exists via `okf_loop.py --miners` + executors.json
  (see LOOP.md "Fan-out").
- Windows: `python3` usually doesn't exist (Store alias) — use `py -3.11`; the
  engine needs `pyyaml`. `viz.html` pulls Cytoscape/fcose/marked from a CDN
  (internet needed to open it; the Gem's data stays inside the file).
