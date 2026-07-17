---
type: Loop State
title: <gem name> — loop state
description: Durable working memory of the growth loop for this Gem.
tags: [loop, meta]
timestamp: <ISO 8601 — REAL system date>
---

<!--
The loop's DURABLE working memory. Read FIRST every cycle, update LAST, so the
loop survives context compaction and wake-ups. Keep it small and CURRENT — this
is state, not history (history lives in log.md). Write it so a smaller model
could run the next cycle from this file alone.
-->

# STATUS

RUNNING (cycle <N>) | CLOSED: nothing-resolvable (<date>, <N> cycles) — how to
reopen: re-challenge the map / pull from "Deepens".

# Goal & scope (the yardstick)

- **Gem:** <path> · **Profile:** <profile>
- **Field anchor:** <the authoritative EXTERNAL outline the map is drawn from —
  reference-work ToC / syllabus / taxonomy, researched, not recalled>
- Done is measured against the FIELD, not against the sources you can read.
  Areas thin in your sources are still gaps.

# Standing orders (from the user — never drop on a context reset)

- Sources to use / avoid: <...>
- Scope decisions / constraints: <...>
- Executor model / tier: <e.g. gemma3 local — weak-model mode ON, ceiling medium>
- Audit model: <e.g. claude opus — every 4 cycles>. Weak-model mode ⇒ LOOP.md
  "Weak-model mode" rules bind every cycle.
- Fan-out: <e.g. 6× flash miners (DeepSeek) + sonnet integrator — LOOP.md
  "Fan-out" binds; miners write-fenced to _staging/> — or "none (solo)".

# Environment (resolve once, reuse — re-check only on a surprise)

- RUN = <uv run | py -3.11 | python3> · SKILL_DIR = <path>
- Reachable sources + how to query each: <...>
- Out of reach, and why: <...>

# Coverage map (vs the field — ≥2 levels: area → topics)

`[x]` done (passed its checklist) · `[~]` partial (say what's thin) · `[ ]`
pending · `[-]` out-of-scope (reason) · `blocked:` names the missing source.

- **<item-type> checklist:** <part A> · <part B> · <part C> · …
- [ ] <Area 1>
  - [x] <topic> — <concept-id>
  - [~] <topic> — thin: <what is missing>
  - [ ] <topic>
- [ ] <Area 2>
  - [ ] <topic> — blocked: needs <named source>

**Stop-gate:** the loop may end (`nothing-resolvable`) only when EVERY line above
is `[x]`, `[-]`, or carries a dead-end naming the exact missing source. Any bare
`[ ]`/`[~]` means NOT done — keep going. Default is continue; stopping must be
proven against the map as re-challenged.

# Ledger (done — compact, newest first)

- c<N> <concept-id> — <one line>

# Dead-ends (do NOT re-attempt — record the reason)

- <item> — blocked: needs <unavailable source>

# Open questions (for the user — never block on these)

- <fork taken + what you would have asked>

# Queue (next actions, highest-value first — refill via the growth axes when empty)

1. <action> — <why it is the top gap vs the coverage map>
2. …
