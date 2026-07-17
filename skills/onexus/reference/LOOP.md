# onexus LOOP — grow a Gem to full field coverage, autonomously

You are here because the intent is loop/grow: `/onexus <gem> /loop [orders]`,
"fica melhorando em loop", "grow until done", or a create/expand where the user
asked for depth/completeness. This file is the loop doctrine. **If you start a
cycle and this checklist is not verbatim in your context (compaction, wake-up,
fresh session): RE-READ this file, and SKILL.md's non-negotiables with it.**

**Mission:** repeated audit→expand cycles, **in-session** (YOU drive them, with
full source/web access; SOLO by default — spawn sub-agents only under
"Fan-out" below, which the user must have asked for; pace with the harness's
scheduler when it has one, else run cycles back-to-back), until the Gem covers
the FIELD. Engineer it as a durable feedback machine, not a
free-running prompt. **Bigger is the default outcome:** a healthy loop keeps
finding MORE map, not less. Every fidelity rule of SKILL.md binds every cycle —
growth never relaxes fidelity.

## Durable memory — `<gem>/_loop-state.md`

Create it on cycle 1 if absent (template: `templates/loop-state.md`). Context WILL
be compacted on long runs; whatever lives only in context gets lost — coverage,
decisions, environment, the user's orders (the #1 historical failure mode). So the
loop's memory lives ON DISK: goal & scope · standing orders · environment
(resolved once) · coverage map · ledger · dead-ends · open questions · queue.

**READ it FIRST every cycle; UPDATE it LAST.** Never trust remembered state over
the file. Write it as if the next cycle will be executed by a smaller model — it
might be.

## The cycle — Observe → Choose → Act → Verify → Record → Repeat/Stop

1. **Observe** — read `_loop-state.md` + fresh Gem facts: `okf_status.py
   --json` (counts, orphans, thin nodes, pending links, gaps, queue) and
   `okf_validate.py --json` (errors). Never act on stale or remembered state.

2. **Choose** — pop the top item from the **queue**. Queue empty ⇒ REFILL it by a
   **Socratic, map-aware audit**: read the map (index tree + cross-link graph +
   weakest/orphan concepts) and ask, *as a scholar of the field*, what the FIELD
   still lacks — scored against the **coverage map**, NOT against the sources you
   happen to have. **Hard rule: "I read every source I found" ≠ "I covered the
   subject"** — sub-areas thin in your sources are still gaps (this exact
   confusion made old loops quit early). Refill along the **growth axes**:
   - **New leaf topics** the field outline demands and the Gem lacks.
   - **Split** any fat concept (3+ separable, separately-sourceable ideas) into
     linked children.
   - **Deepen** an existing concept: primary sources, counterpoints, variants,
     history, worked examples, practical application.
   - **Typed nodes** the area implies but doesn't have: `Person`, `Text`,
     `Practice`, `Method`, `Debate`, `Case`, `Glossary`, `Timeline`…
   - **Link density**: de-orphan concepts; wire area hubs.
   - **Map growth**: is a whole area of the FIELD missing from the map itself?
   For a repeatable item-type, score each item against its **completeness
   checklist** so half-done items show as `[~] partial`, never silently done.

3. **Act** — ONE bounded, faithful EXPAND (sources: user-given → local → web).
   Before creating any file, search the Gem (`okf_search.py`) for the topic —
   an existing concept gets deepened/split, never twinned.
   Additive only; no unrelated changes folded in; preserve existing work. The
   content comes **only from sources you actually read this loop** — never from
   your own memory of the subject; if nothing sourceable exists, the item becomes
   `blocked: needs <named source>`, never an invention.
   **Per-cycle floor (anti-laziness):** every cycle yields EITHER an artifact (a
   new or genuinely expanded concept file) OR a new dead-end naming the exact
   missing source. "Swept, nothing to do" with neither is an INVALID cycle — it
   means you scoped against the sources you already read; refill the queue from
   the FIELD outline and act again.

4. **Verify** — an observable, reproducible gate, NOT self-graded: the new/changed
   concepts are sourced, provenance set, links relative, `okf_validate.py` clean
   of ERRORs. Plus the **source-trace re-read**: every line of the new content
   traceable to a source read THIS cycle — untraceable lines (remembered
   anecdotes, inferred superlatives) are deleted or moved to Gaps; structural
   validators cannot catch inventions. Never report a blocked or invalid cycle
   as success.

5. **Record** — update `_loop-state.md` (ledger ← what was done; queue ← new gaps
   found; environment ← new facts; dead-ends ← new blocks; open questions ←
   anything you would have asked the user) AND append a `log.md` entry
   (`okf_log.py … --kind Loop`). This is the handoff to the next cycle.

6. **Repeat / Stop** — end each cycle in ONE line with a named terminal state:
   `improved: <what>` · `blocked: needs <source>` · `nothing-resolvable`.

## Map discipline (what makes Gems BIG and honest)

- **Anchor (cycle 1):** research an authoritative EXTERNAL outline of the field —
  a reference work's table of contents, a syllabus, a canonical taxonomy — and
  draw the coverage map from it, **≥2 levels** (areas → topics), every leaf topic
  ⇒ ≥1 concept. Maps recalled from memory are forbidden: they shrink the field to
  what you already know.
- **Re-challenge (every ~3 cycles):** run a **completeness-critic** pass whose
  ONLY job is to NAME missing nodes — new leaves, whole new areas, missing typed
  nodes, checklist parts nobody wrote. A map that keeps growing under challenge is
  real coverage work; a map that stopped growing only because nothing challenged
  it is the laziness to kill.
- **Checklists:** every repeatable item-type gets a completeness checklist in the
  state file (e.g. a "philosopher" model: life · works · key ideas · reception ·
  primary sources · debates). Items pass by checklist, not by vibes.

## Stopping (a gate, not a judgment)

You may declare `nothing-resolvable` ONLY when EVERY line of the coverage map is
`[x]` (passed its checklist) or `[-]` (named out-of-scope reason) or carries a
dead-end naming the exact missing source. Any bare `[ ]` / `[~]` ⇒ NOT done —
continue. "I think it covers everything" is never a valid stop; only the map's
state decides — the map **as re-challenged**, not as first drafted. **Default is
continue; stopping is what you must prove.** Otherwise run to the user's bound
(N cycles / M minutes / Esc).

## Autonomy & pacing

- **Never ask the user mid-loop.** A decision you can't make ⇒ take the faithful,
  conservative branch, record the fork under "Open questions" in the state file,
  keep moving. Surface open questions in the end-of-turn status, not as blockers.
- **Batch cycles:** run several full cycles per turn while healthy (3–6 is the
  proven rhythm — that is how the real Gems got built), each one passing its own
  gates and updating state. Then yield: a brief status in the user's language
  (cycles run, concepts added, map delta, next queue head, terminal line) and
  schedule the next wake-up (self-paced) or honor the fixed cadence the user
  gave. In a harness with no scheduler, don't yield — continue with the next
  batch until a stop condition.
- **No cadence given ⇒ self-paced until the stop-gate** or the user interrupts —
  do not stop to ask for a cadence.
- **Standing orders:** any instructions after `/loop` go into the state file's
  Standing orders on cycle 1 and BIND every later cycle, across compactions.
- **Resume:** an interrupted loop resumes from `_loop-state.md` alone — the first
  cycle of a resumed run is simply Observe on the existing file (honor its STATUS
  line: a loop closed as `nothing-resolvable` reopens only by re-challenging the
  map, e.g. from a "deepens" queue it left behind).

## Weak-model mode (cheap/local executors — DeepSeek, Gemma, small models)

Structure they follow; judgment they don't. When the model running cycles is a
cheap/local one, the loop compensates by moving every judgment into a script or
a stronger auditor:

- **Architect once, grind cheap.** The coverage map, checklists and queue are
  built (and re-challenged) by the strongest available model or the user; the
  cheap executor only works queue items. It never re-plans the map.
- **One micro-task per cycle.** The cycle prompt names the exact queue item /
  gap to resolve (okf_loop.py injects this automatically). No open-ended
  "improve the Gem".
- **Evidence first.** Save the raw source (download into `_sources/`, or
  `okf_excerpt.py` into `references/`) BEFORE writing; write only what traces
  to saved files. `_sources/` is `_`-meta: staging evidence, not knowledge.
  **First excerpt from any source FILE: sanity-check its header/opening lines
  against the work it claims to be** — a mislabeled file becomes a dead-end +
  a report line, not silent wrong evidence (field-tested: a file named after
  one book actually contained a different one).
- **Verbatim is never typed** — by ANY model, and doubly so here: verbatim
  blocks come only from `okf_excerpt.py` byte-copies. In the sacred profile an
  executor below the audit tier may not author verbatim at all — structure and
  cited prose only.
- **Confidence ceiling.** Executor output caps at `confidence: medium` and
  carries the tag `needs-review`. Only the audit pass (or the user) promotes.
- **Machine-checked gates.** Every cycle ends with `okf_verify.py --concept
  <id> --strict` (blockquotes AND quoted-prose spans must match saved sources;
  citations present) and `okf_validate.py`. The DRIVER re-runs both itself
  after every cycle and hands failures back to the executor for one fix pass —
  no self-report is trusted. A `nothing-resolvable` claim is verified against
  `okf_status.py` — open items ⇒ the stop is rejected and the top item pushed
  back (okf_loop.py does all of this automatically). Verify's `framing hints`
  (years/superlatives absent from staged sources) are the auditor's aim-list
  for the known fabricated-bibliographic-framing vice.
- **Driving loops from inside a harness turn:** run okf_loop as repeated
  `--cycles 1` invocations in the FOREGROUND — multi-cycle batches can outlive
  the harness's shell timeout (~10 min), and a master must NOT yield its turn
  waiting for a background notification unless its harness reliably re-wakes
  it (field-tested failure mode).
- **Audit pass by a stronger model** (`--audit-executor audit`, every N cycles
  and at the end): source-trace re-read of the delta, promote/demote/delete,
  log `Audit`. Budget rule of thumb: the strong model reviews ~10% of the
  tokens and catches ~90% of what scripts can't.
- **Executor profiles** (`executors.json`): name → agent CLI (opencode gateways,
  OpenRouter, Ollama local/cloud, LM Studio, claude -p …). Set the model once,
  run `okf_loop.py --executor <name>` from any master harness. Non-interactive
  opencode needs `permission: allow` blocks in `opencode.jsonc`.

## Fan-out — parallel miners (only when the user asks for it)

Solo in-session is the default. When the user asks for parallel workers
("miners", "mineradores", "agentes em paralelo", "N ao mesmo tempo"), run
ARCHITECT → MINERS → INTEGRATOR. Fidelity survives parallelism by ONE rule:
**miners never write knowledge into the Gem** — they stage evidence; a strong
integrator audits and writes.

**Roles**
- **Architect/Integrator** (the session model, or `--integrate-executor`): owns
  the map and the queue; the ONLY writer of concepts, indexes, `log.md` and
  `_loop-state.md`. Refills the queue by the Socratic map-aware audit (step 2
  of the cycle) — miners never re-plan the map.
- **Miners** (N in parallel; a cheap tier is fine): each takes ONE queue item
  and works ONLY inside `_staging/<slug>/` (a `_`-meta staging area):
  `draft.md` (every claim with inline `[source: …]`; `## Proposed links`;
  `## Verbatim wanted` = source file + start/end markers — verbatim is NEVER
  typed by a miner), `sources/` (raw downloads + MANIFEST.md), `notes.md`
  (unsourceable claims → candidate gaps; leads). Miners read the Gem freely
  but write NOTHING outside their staging folder and never touch `index.md`,
  `log.md`, `_loop-state.md`. Ceiling: `confidence: medium` + `needs-review`.
- **Integration, per staged folder:** source-trace the draft against its
  `sources/` (drop or Gap every untraceable line) → dedup via `okf_search.py`
  (deepen, don't twin) → write the real concept(s) → verbatim via
  `okf_excerpt.py` from the raw file moved into `references/`/`_sources/` →
  update indexes/hubs → delete the promoted staging folder → gates
  (`okf_verify --strict` + `okf_validate`) → ledger/queue/log.

**Model policy (the vendor lesson)**
- **In-session miners** run on the models THIS harness can spawn (e.g. Claude
  Code sub-agents = Claude models only). If the user names another vendor's
  model (DeepSeek, Gemini, GPT…), that cannot run as an in-session sub-agent:
  say so in ONE line, offer the nearest harness tier (cost → small tier;
  fidelity → mid tier), and keep moving — never stall on it.
- **Any-vendor miners** exist through the script mini-harness:
  `okf_loop.py <gem> --miners N [--miner-executor <alias>]
  [--integrate-executor audit]` — each miner is an executor CLI from
  `executors.json` (opencode → DeepSeek/OpenRouter/Ollama…, `claude -p`, …).
  With a strong session already open, prefer
  `--cycles 1 --miners N --no-integrate`: the wave mines to `_staging/` and
  STOPS, and YOU integrate in-session (keeping this session's RAG/MCP access
  for the integration); repeat wave-by-wave.
- In-session miner fan-out (harness sub-agents) follows the SAME write-fence
  and staging contract; the session model is the integrator.

One wave = refill (if the queue is short) → N miners in parallel → integrate →
gates → record. Waves batch like cycles; every fidelity rule binds every wave.

## Headless variant

`okf_loop.py` exists ONLY for unattended runs without this session (it spawns a
CLI agent per cycle — or per miner, with `--miners N`; those agents do NOT
inherit this session's access to local RAGs/MCP). Interactive = always this
doctrine, in-session.
