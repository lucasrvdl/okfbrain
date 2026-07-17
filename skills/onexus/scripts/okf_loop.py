#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""okf_loop.py — autonomous audit->expand loop for an OKF gem (headless driver).

Built so CHEAP/LOCAL executor models produce trustworthy work:
  - every cycle prompt carries the CURRENT machine-read state (top gaps, queue
    head, orphans, uncited) — the model executes a concrete micro-task instead
    of planning open-endedly;
  - "nothing-resolvable" is a CLAIM, verified against okf_status: while open
    items remain, the stop is REJECTED and the top item is pushed back;
  - --confidence-ceiling caps what the executor may claim; --audit-agent runs
    a stronger model over the recent delta (source-trace re-read + okf_verify)
    to promote/demote, every --audit-every cycles and at the end.

Stop conditions: --cycles N | --minutes M | --until-dry | --forever.
The spawned agent CLI is swappable: claude -p, codex exec, gemini -p,
ollama run <model>, deepseek CLI, etc.

FAN-OUT (mini-harness): --miners N runs N executor agents IN PARALLEL per wave,
one queue item each, write-fenced to _staging/<slug>/ (draft + raw sources —
never the gem itself); then ONE strong INTEGRATOR pass source-traces, embeds
verbatim via okf_excerpt, writes the real concepts and passes the gates. This is
how non-Claude miners (DeepSeek, Ollama, OpenRouter...) work for a gem in
parallel — vendor-free, one executor CLI per miner.

Usage:
  uv run okf_loop.py <gem> --cycles 8
  uv run okf_loop.py <gem> --minutes 120 --agent "ollama run gemma3" \\
     --confidence-ceiling medium --audit-agent "claude -p --permission-mode acceptEdits" --audit-every 4
  uv run okf_loop.py <gem> --until-dry --dry-run      # preview state + prompt, no agent
  uv run okf_loop.py <gem> --cycles 3 --miners 6 --miner-executor flash \\
     --integrate-executor audit                          # fan-out waves, any vendor
  uv run okf_loop.py <gem> --cycles 1 --miners 6 --no-integrate
     # mine ONE wave to _staging/, then the MASTER session integrates in-session
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
VALIDATE = HERE / "okf_validate.py"
STATUS = HERE / "okf_status.py"
VERIFY = HERE / "okf_verify.py"
DEFAULT_AGENT = "claude -p --permission-mode acceptEdits"


def load_executors() -> tuple[str, dict[str, str]]:
    """Merge SKILL_DIR/executors.json with the user's executors.json (user wins):
    legacy ~/.okfbrain/ is still read; ~/.onexus/ has the highest precedence.
    Returns (default_name, {name: agent_cmd})."""
    default, table = "", {}
    for p in (HERE.parent / "executors.json",
              Path.home() / ".okfbrain" / "executors.json",
              Path.home() / ".onexus" / "executors.json"):
        try:
            if p.exists():
                d = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(d.get("default"), str):
                    default = d["default"]
                if isinstance(d.get("executors"), dict):
                    table.update({str(k): str(v) for k, v in d["executors"].items()})
        except Exception as exc:
            print(f"warn: ignoring bad executors file {p}: {exc}", file=sys.stderr)
    return default, table


def resolve_executor(name: str, table: dict[str, str]) -> str:
    if name in table:
        cmd = table[name]
        if "<" in cmd:
            raise SystemExit(f"executor '{name}' still has a <placeholder> — edit executors.json first: {cmd}")
        return cmd
    raise SystemExit(f"unknown executor '{name}'. Available: {', '.join(sorted(table)) or '(none)'}")

CYCLE_PROMPT = """You are running ONE growth cycle on the OKF gem at:
{gem}

CURRENT STATE (machine-read via okf_status — trust this over your memory):
{state}

THIS CYCLE'S TASK: resolve the queue head above; if the queue is empty, take the
top open gap; if both are empty, de-orphan or cite an uncited concept from the
lists above. ONE bounded, faithful expansion — nothing else.

Doctrine (follow strictly):
1. OBSERVE — read `_loop-state.md` FIRST (standing orders, coverage map,
   dead-ends). Never act on remembered state.
2. EVIDENCE FIRST — before writing, SAVE the raw source material you will use
   (download/copy into `_sources/` or embed via okf_excerpt.py into
   `references/`). You may only write claims traceable to those saved files or
   to pages you actually opened. NEVER from your own memory of the subject.
   Verbatim blocks (mantras, verses, law text, formulas) are NEVER typed by
   you: only copied byte-exact by `{here}/okf_excerpt.py` from a saved file.
   Nothing sourceable => mark the item `blocked: needs <named source>` in the
   state file and take the next item.
3. WRITE — one new or deepened concept: frontmatter per templates/concept.md,
   RELATIVE markdown links (>=2), a citations section, provenance set. When the
   concept draws on a primary source, include AT LEAST ONE direct quote as a
   `>` blockquote PASTED from the references/ file you staged (quoted prose or
   your own translation in quotation marks is NOT a quote — it cannot be
   machine-verified).{ceiling}
4. VERIFY (mechanical, not vibes) — run:
     {py} "{here}/okf_verify.py" "{gem}" --concept <the-concept-id> --strict
     {py} "{here}/okf_validate.py" "{gem}"
   Fix every failure before finishing the cycle.
5. RECORD — update `_loop-state.md` (ledger, queue, dead-ends) and log.md via
   okf_log.py --kind Loop; keep folder index.md files current. If `_index/`
   exists, refresh it: {py} "{here}/okf_embed.py" "{gem}"
6. Report in ONE line: `improved: <what>` | `blocked: needs <source>` |
   `nothing-resolvable` (claim it ONLY if you believe every map line is closed —
   it will be machine-checked and rejected if open items remain).
"""

AUDIT_PROMPT = """You are the AUDIT pass over recent changes to the OKF gem at:
{gem}

A cheaper executor model wrote the recent concepts (see log.md, newest entries,
and `_loop-state.md` ledger). Your job — adversarial, not charitable:
1. For each concept added/changed in the recent batch: SOURCE-TRACE RE-READ —
   every line must be traceable to a saved file under references/ or _sources/
   or to a cited page you can open. Remembered anecdotes, inferred
   superlatives, wrong attributions => delete the line or move it to the Gaps
   section of the root index.md.
2. Run: {py} "{here}/okf_verify.py" "{gem}" --strict   and
        {py} "{here}/okf_validate.py" "{gem}"
   Fix or demote whatever fails.
3. PROMOTE clean concepts tagged needs-review: remove the tag and set the
   confidence the evidence supports. DEMOTE bad ones: confidence: low + a "⚠"
   note in the body + a gap entry naming what must be re-verified.
4. Update `_loop-state.md` (dead-ends, queue) and append a log.md entry via
   okf_log.py --kind Audit --note "audited <n>: promoted <n>, demoted <n>".
Report in ONE line: `audited: N, promoted: N, demoted: N, deleted-lines: N`.
"""


FIX_PROMPT = """Your last cycle on the OKF gem at {gem} INTRODUCED failures in the
mechanical gates (the driver checked — this is not an opinion):
{detail}

Fix ONLY this, in the files you created/changed this cycle:
- a quote (blockquote OR quoted prose) with no saved source => paste it from a
  references/ file as a blockquote, or rewrite it as plain prose WITHOUT quotes;
- an uncited concept => add its citations section;
- a validate error => fix the frontmatter/structure.
Then run until clean:
  {py} "{here}/okf_verify.py" "{gem}" --strict
  {py} "{here}/okf_validate.py" "{gem}"
Reply in ONE line with what you fixed."""


MINER_PROMPT = """You are MINER `{slug}`, one of several PARALLEL miners on the OKF gem at:
{gem}

YOUR ITEM (work ONLY this — other miners have the others):
{item}

You STAGE evidence + a draft; a stronger INTEGRATOR audits and writes the gem.
HARD WRITE-FENCE: you may create/edit files ONLY inside:
{staging}
Everything else is READ-ONLY (read concepts freely for context; NEVER edit them;
never touch index.md, log.md, `_loop-state.md`).

Steps:
1. Read `_loop-state.md` (standing orders bind you too) and check for related
   concepts: {py} "{here}/okf_search.py" "{gem}" "<term>" — note in your draft
   whether your topic should DEEPEN an existing concept instead of twinning it.
2. RESEARCH the item: sources named in standing orders first, then local
   corpora, then the web. SAVE the raw material you actually used into
   {staging}/sources/ (download the raw file — curl, or python urllib via your
   shell; list each file in sources/MANIFEST.md: exact URL/origin + access
   date). A failed fetch (403, timeout) is not a source.
3. Write {staging}/draft.md (more: draft-2.md ...) — a DRAFT concept:
   frontmatter per templates/concept.md; every claim in the body ends with
   `[source: <file-in-sources/ or URL you opened>]`; a `## Proposed links` list
   of existing concept ids; a `## Verbatim wanted` list — for each verbatim the
   profile demands (mantra, verse, law text, formula, key quote): the source
   file in sources/ + exact start/end markers for okf_excerpt. NEVER type the
   verbatim text yourself. Cap `confidence: medium`; tag `needs-review`.
4. Write {staging}/notes.md: what you could NOT source (candidate gaps and
   dead-ends with the missing source NAMED), open questions, and leads for
   OTHER items you noticed (do not work them).
5. Report in ONE line: `mined: {slug} — <what you staged>` or
   `blocked: needs <named source> — {slug}`.

Fidelity: nothing from your own memory of the subject — only what you read THIS
run. A claim you cannot source goes in notes.md as a gap, never in draft.md.
"""


INTEGRATE_PROMPT = """You are the INTEGRATOR for the OKF gem at:
{gem}

Parallel miners staged folders under `_staging/` (each: draft.md + sources/ +
notes.md). You are the ONLY writer of knowledge. Adversarial first, then build:

1. Per staged folder:
   a. SOURCE-TRACE the draft line by line against its sources/ (or cited pages
      you can open). Sanity-check each sources/ file's opening lines against
      what its MANIFEST entry claims it is. Untraceable lines are DROPPED or
      become explicit Gaps — never promoted.
   b. Dedup first ({py} "{here}/okf_search.py" "{gem}" "<topic>"): an existing
      concept gets deepened/split, never twinned. Then write the real concept
      file(s) in the right area folder: frontmatter per templates/concept.md,
      >=2 RELATIVE links (verify the miner's proposed ones), citations section,
      provenance set to what the evidence supports.
   c. For each "Verbatim wanted" entry: move/copy the raw file into
      `references/` (or `_sources/`), then embed byte-exact via:
        {py} "{here}/okf_excerpt.py" "<source-file>" "{gem}" "references/<name>.md" --from "<start>" --to "<end>" --title "<title>" --citation "<origin>"
      and paste the blockquote from that references/ file. NEVER type verbatim.
   d. Update the area index.md (and root index/hubs if a new area appeared);
      link the new concept FROM its hub (no orphans).
   e. DELETE the staged folder once promoted (its evidence now lives in
      `references/` / `_sources/`). A `blocked` folder: record the dead-end in
      `_loop-state.md`, keep any useful saved sources, delete the folder.
2. Gates — run and FIX until clean:
     {py} "{here}/okf_verify.py" "{gem}" --strict
     {py} "{here}/okf_validate.py" "{gem}"
3. RECORD (refresh `_index/` first if it exists: {py} "{here}/okf_embed.py" "{gem}"):
   `_loop-state.md` (ledger one line per item; remove done items from
   the Queue; add new gaps/leads from the miners' notes.md; dead-ends; open
   questions) and ONE log.md entry:
     {py} "{here}/okf_log.py" "{gem}" --kind Loop --agent "okf_loop fan-out" --model "<your model>" --note "wave: integrated <n>/<m> staged items"
   If the Queue is now shorter than the miner count, REFILL it (Socratic,
   map-aware — scored against the coverage map; grow the map if the field
   demands; skip Dead-ends).
Report in ONE line: `integrated: <n>/<m>, gaps: <n>, dead-ends: <n>`.
"""


REFILL_PROMPT = """The Queue in `_loop-state.md` of the OKF gem at
{gem}
has fewer than {n} items. You are the ARCHITECT: refill it — do NOT write concepts.

1. Read `_loop-state.md` (standing orders, coverage map, dead-ends) and run:
     {py} "{here}/okf_status.py" "{gem}" --json
2. Socratic, map-aware audit (LOOP.md doctrine): score the gem against the
   COVERAGE MAP, not against sources already read. Grow the map if the field
   demands (new areas/leaves). Growth axes: new leaf topics · split fat
   concepts · deepen (primary sources, counterpoints, variants) · missing typed
   nodes (Person, Text, Practice, Method, Debate, Case, Glossary, Timeline) ·
   de-orphan · map growth.
3. REWRITE the Queue section of `_loop-state.md`: numbered items, highest value
   first, each ONE bounded minable task naming its target area/topic. Skip
   anything in Dead-ends. Update the coverage map if you grew it.
Report in ONE line: `refilled: <n> items` or `map-closed: nothing to add`.
"""


def run_json(script: Path, gem: Path) -> dict:
    try:
        out = subprocess.run([sys.executable, str(script), str(gem), "--json"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=300)
        return json.loads(out.stdout or "{}")
    except Exception as exc:
        return {"error": str(exc)}


def gate_counts(gem: Path) -> tuple[int, int, str]:
    """Driver-run machine gates: (fidelity failures, validate errors, detail text).
    The driver TRUSTS NO executor self-report — it checks itself after every cycle."""
    v = run_json(VERIFY, gem)
    fid = (len(v.get("unmatched_quotes", [])) + len(v.get("unmatched_prose", []))
           + len(v.get("uncited", [])))
    val = run_json(VALIDATE, gem)
    errs = len(val.get("errors", []))
    parts = []
    for u in (v.get("unmatched_quotes", []) + v.get("unmatched_prose", []))[:4]:
        parts.append(f"- quote sem fonte em {u.get('concept')}: “{u.get('quote')}”")
    for c in v.get("uncited", [])[:3]:
        parts.append(f"- sem citações: {c}")
    for e in val.get("errors", [])[:3]:
        parts.append(f"- validate: {e}")
    return fid, errs, "\n".join(parts)


def queue_head(gem: Path) -> str:
    items = queue_items(gem, 1)
    return items[0] if items else ""


def queue_items(gem: Path, n: int) -> list[str]:
    """First n numbered items of the Queue section in _loop-state.md.
    Continuation lines (indented, or starting with +/-/·) are folded into the
    item, so the architect's source pointers reach the executor intact."""
    ls = gem / "_loop-state.md"
    if not ls.exists():
        return []
    items: list[str] = []
    grab = done = False
    for line in ls.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("# "):
            grab = line[2:].strip().lower().startswith("queue")
            continue
        if not grab or done:
            continue
        st = line.strip()
        if not st:
            continue
        if st[0].isdigit() and "." in st[:4]:
            if len(items) >= n:
                done = True
                continue
            items.append(st)
        elif items and len(items) <= n and not st.startswith("~~")                 and (line[:1] in (" ", "	") or st[0] in "+-·—"):
            items[-1] += " " + st
    return [i[:700] for i in items[:n]]


def slugify(text: str) -> str:
    """kebab-case ASCII folder name for a queue item (strip leading number)."""
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    t = re.sub(r"^\W*\d+[.)]?\s*", "", t)
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()
    return t[:60] or "item"


def state_block(gem: Path) -> tuple[str, int]:
    """(human block for the prompt, count of machine-open items)."""
    s = run_json(STATUS, gem)
    if "error" in s:
        return f"- (status unavailable: {s['error']})", 1
    g = s.get("gaps", {})
    open_gaps = g.get("open", [])
    ls = s.get("loop_state", {})
    open_map = int(ls.get("open_map_lines", 0) or 0)
    qlen = int(ls.get("queue_len", 0) or 0)
    head = queue_head(gem)
    lines = [
        f"- concepts: {s.get('concepts')} · edges: {s.get('edges')}",
        f"- queue: {qlen} item(s)" + (f" · HEAD: {head}" if head else ""),
        f"- open gaps in root index: {len(open_gaps)}"
        + (" · top: " + " | ".join(x[:80] for x in open_gaps[:3]) if open_gaps else ""),
        f"- coverage map open lines ([ ]/[~]): {open_map}",
        f"- orphans: {len(s.get('orphans', []))}"
        + (" (" + ", ".join(s.get("orphans", [])[:4]) + ")" if s.get("orphans") else ""),
        f"- uncited concepts: {len(s.get('uncited', []))}"
        + (" (" + ", ".join(s.get("uncited", [])[:4]) + ")" if s.get("uncited") else ""),
        f"- validate errors: {len(run_json(VALIDATE, gem).get('errors', []))}",
    ]
    open_items = len(open_gaps) + open_map + qlen
    return "\n".join(lines), open_items


LOG_DIR: Path | None = None  # set by --log-dir


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the agent AND its children (on Windows, subprocess timeout alone
    leaves the tree alive — field-tested: an integrator survived its timeout)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, timeout=30)
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_agent(agent_cmd: str, prompt: str, gem: Path, timeout: int,
              label: str = "agent") -> str:
    out = ""
    try:
        kw: dict = dict(cwd=str(gem), stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True,
                        encoding="utf-8", errors="replace")
        if os.name == "nt":
            kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kw["preexec_fn"] = os.setsid
        argv = agent_cmd.split() + [prompt]
        # stdin must be CLOSED (pi -p blocks forever reading an open pipe) and
        # the executable resolved via PATH (npm ships .cmd shims Windows's
        # CreateProcess won't find bare) — both field-tested.
        exe = shutil.which(argv[0])
        if exe:
            argv[0] = exe
        # Windows script shims (.cmd/.bat) run through cmd.exe, which cuts the
        # command line at the first newline — a multiline prompt arrives as its
        # first line only (field-tested: a miner got one line of its contract
        # and ignored the write-fence). For those, deliver the prompt on stdin
        # (piped-stdin-to-EOF is the message convention of such CLIs, e.g. pi).
        via_stdin = (os.name == "nt"
                     and Path(argv[0]).suffix.lower() in (".cmd", ".bat", ".ps1"))
        if via_stdin:
            argv = argv[:-1]
            kw["stdin"] = subprocess.PIPE
        proc = subprocess.Popen(argv, **kw)
        try:
            out, _ = proc.communicate(input=prompt if via_stdin else None,
                                      timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            try:
                rest, _ = proc.communicate(timeout=30)
                out = (out or "") + (rest or "")
            except Exception:
                pass
            out = (out or "") + "\n(agent timed out — process tree killed)"
    except Exception as exc:
        out = f"(agent error: {exc})"
    out = (out or "").strip()
    if LOG_DIR:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in label)[:60]
            (LOG_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{safe}.log").write_text(
                f"$ {agent_cmd}\n--- PROMPT ---\n{prompt}\n--- OUTPUT ---\n{out}\n",
                encoding="utf-8")
        except Exception:
            pass
    return out[-800:] or "(no output)"


def wave_mode(args, miner_cmd: str, miner_label: str,
              integrate_cmd: str, integrate_label: str) -> int:
    """Fan-out: waves of N parallel miners (write-fenced to _staging/) + one
    strong integrator pass per wave. Driver-enforced gates, same as solo mode."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    gem = args.gem
    stop = (f"cycles={args.cycles}" if args.cycles else
            f"minutes={args.minutes}" if args.minutes else
            "until-dry" if args.until_dry else "forever")
    print(f"== okf-loop FAN-OUT on '{gem.name}' | stop: {stop} | "
          f"miners: {args.miners}x {miner_label} -> {miner_cmd}")
    print(f"   integrator: "
          f"{integrate_label + ' -> ' + integrate_cmd if integrate_cmd else '(none — the MASTER session integrates)'} ==")

    start = time.time()
    wave = 0
    base_fid, base_err, _ = gate_counts(gem) if not args.dry_run else (0, 0, "")
    if base_fid or base_err:
        print(f"(pre-loop baseline: {base_fid} fidelity failure(s), {base_err} validate error(s) "
              f"already present — only NEW failures fail a wave)")
    while True:
        if args.cycles and wave >= args.cycles:
            break
        if args.minutes and (time.time() - start) >= args.minutes * 60:
            break
        wave += 1
        _, open_items = state_block(gem)
        print(f"\n--- wave {wave} | machine-open items: {open_items} ---")
        if args.until_dry and open_items == 0:
            print("  DRY — status shows nothing open. Stopping.")
            break

        items = queue_items(gem, args.miners)
        if len(items) < args.miners and integrate_cmd and not args.dry_run:
            print(f"  queue has {len(items)} item(s) < {args.miners} miners — REFILL pass (architect)")
            out = run_agent(integrate_cmd,
                            REFILL_PROMPT.format(gem=gem, n=args.miners,
                                                 here=HERE, py=sys.executable),
                            gem, args.agent_timeout, label=f"wave-{wave}-refill")
            print(f"  refill: {out[-200:]}")
            items = queue_items(gem, args.miners)
        if not items:
            print("  queue empty and no refill possible — stopping. Refill the Queue in "
                  "_loop-state.md (master session / --integrate-executor) and rerun.")
            break

        if args.dry_run:
            print("  [dry-run] this wave would mine these items in parallel:")
            for it in items:
                print(f"    - _staging/{slugify(it)}/  <-  {it}")
            print("  [dry-run] then " + ("the integrator pass would run." if integrate_cmd
                                         else "the master session would integrate."))
            break

        results: dict[str, str] = {}

        def mine(item: str, idx: int) -> tuple[str, str]:
            time.sleep(idx * 2.5)  # stagger: parallel CLI startups can fight over a local db
            slug = slugify(item)
            staging = gem / "_staging" / slug
            (staging / "sources").mkdir(parents=True, exist_ok=True)
            prompt = MINER_PROMPT.format(gem=gem, item=item, slug=slug,
                                         staging=staging, here=HERE, py=sys.executable)
            return slug, run_agent(miner_cmd, prompt, gem, args.agent_timeout, label=f"miner-{slug[:40]}")

        with ThreadPoolExecutor(max_workers=args.miners) as pool:
            futs = {pool.submit(mine, it, i): it for i, it in enumerate(items)}
            for fut in as_completed(futs):
                slug, out = fut.result()
                results[slug] = out
                print(f"  miner[{slug}]: {out[-160:]}")

        if not integrate_cmd:
            print(f"\n  staging ready: {gem / '_staging'} ({len(results)} folder(s)).")
            print("  No integrator in this run — the MASTER session must integrate NOW, per "
                  "LOOP.md 'Fan-out': source-trace each draft, dedup, promote (verbatim via "
                  "okf_excerpt), wire links + indexes, run okf_verify --strict + okf_validate, "
                  "update _loop-state.md + log.md, delete promoted staging folders.")
            break

        print("  == INTEGRATE pass ==")
        itimeout = args.integrate_timeout or max(args.agent_timeout * 2, 1800)
        out = run_agent(integrate_cmd,
                        INTEGRATE_PROMPT.format(gem=gem, here=HERE, py=sys.executable),
                        gem, itimeout, label=f"wave-{wave}-integrate")
        print(f"  integrator: {out[-300:]}")
        if "timed out" in out:
            print("  (note: on Windows the integrator process may SURVIVE the timeout and finish "
                  "on its own — check the ledger before re-running the wave)")

        fid, errs, detail = gate_counts(gem)
        if fid > base_fid or errs > base_err:
            print(f"  GATES: FAILED (fidelity {base_fid}→{fid} · validate {base_err}→{errs}) "
                  f"— handing back to the integrator")
            out2 = run_agent(integrate_cmd,
                             FIX_PROMPT.format(gem=gem, detail=detail,
                                               here=HERE, py=sys.executable),
                             gem, args.agent_timeout, label=f"wave-{wave}-integrate-fix")
            print(f"  fix: {out2[-200:]}")
            fid, errs, _ = gate_counts(gem)
            print("  GATES: " + ("ok after fix" if fid <= base_fid and errs <= base_err
                                 else "STILL FAILING — resolve before the next wave"))
        else:
            print(f"  GATES: ok (fidelity {fid} · validate {errs})")
        base_fid, base_err = min(base_fid, fid), min(base_err, errs)

        if args.cycles and wave >= args.cycles:
            break
        time.sleep(args.interval)

    print(f"\n== done: {wave} wave(s), {round(time.time() - start)}s ==")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Autonomous audit->expand loop for an OKF gem.")
    ap.add_argument("gem", type=Path, nargs="?",
                    help="path to the gem folder (optional only with --list-executors)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--cycles", type=int)
    g.add_argument("--minutes", type=float)
    g.add_argument("--until-dry", action="store_true")
    g.add_argument("--forever", action="store_true")
    ap.add_argument("--agent", default="",
                    help="raw executor CLI (overrides --executor)")
    ap.add_argument("--executor", default="",
                    help="named profile from executors.json (SKILL_DIR, overridden by ~/.onexus/ or legacy ~/.okfbrain/)")
    ap.add_argument("--audit-agent", default="",
                    help="raw CLI for the audit pass (overrides --audit-executor)")
    ap.add_argument("--audit-executor", default="",
                    help="named profile for the audit pass (e.g. 'audit')")
    ap.add_argument("--list-executors", action="store_true", help="print the executor profiles and exit")
    ap.add_argument("--audit-every", type=int, default=0,
                    help="run the audit every N cycles (default: only at the end, when --audit-agent is set)")
    ap.add_argument("--confidence-ceiling", choices=["low", "medium"], default="",
                    help="cap the executor's confidence claims; audit promotes later")
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between cycles")
    ap.add_argument("--agent-timeout", type=int, default=900)
    ap.add_argument("--integrate-timeout", type=int, default=0,
                    help="integrator timeout (default: 2x agent-timeout, min 1800s — "
                         "it writes N concepts in one pass)")
    ap.add_argument("--dry-run", action="store_true", help="print state + the exact cycle prompt, no agent")
    ap.add_argument("--log-dir", default="", help="write FULL prompt+output of every agent call here (default: only the tail is shown)")
    ap.add_argument("--force-unlock", action="store_true", help="break a stale .okf-loop.lock left by a dead run")
    ap.add_argument("--miners", type=int, default=0,
                    help="FAN-OUT: N parallel miner agents per wave (write-fenced to _staging/), "
                         "then one integrator pass. Any executor can mine — incl. non-Claude models.")
    ap.add_argument("--miner-agent", default="",
                    help="raw CLI for the miners (overrides --miner-executor)")
    ap.add_argument("--miner-executor", default="",
                    help="named profile for the miners (default: the main executor)")
    ap.add_argument("--integrate-executor", default="",
                    help="named profile for the integrator (default: the audit executor, "
                         "else the 'audit' profile)")
    ap.add_argument("--no-integrate", action="store_true",
                    help="mine ONE wave and stop — the MASTER session integrates in-session")
    args = ap.parse_args()

    default_name, table = load_executors()
    if args.list_executors:
        print(f"executor profiles (default: {default_name or '(builtin claude)'})")
        for k in sorted(table):
            print(f"  {k:14s} {table[k]}")
        return 0
    if args.gem is None:
        print("error: gem path is required (except with --list-executors)", file=sys.stderr)
        return 2
    if not args.gem.is_dir():
        print(f"error: {args.gem} is not a directory", file=sys.stderr)
        return 2
    if not (args.cycles or args.minutes or args.until_dry or args.forever):
        print("error: choose a stop condition: --cycles N | --minutes M | --until-dry | --forever",
              file=sys.stderr)
        return 2

    global LOG_DIR
    if args.log_dir:
        LOG_DIR = Path(args.log_dir)

    # one loop per gem at a time — two writers on _loop-state.md is corruption
    lock = args.gem / ".okf-loop.lock"
    if not args.dry_run:
        if lock.exists() and not args.force_unlock:
            age_min = int((time.time() - lock.stat().st_mtime) / 60)
            info = lock.read_text(encoding="utf-8", errors="ignore").strip()
            print(f"error: gem is LOCKED by another running loop ({info}; started {age_min} min ago).",
                  file=sys.stderr)
            print("       If that loop is dead, rerun with --force-unlock.", file=sys.stderr)
            return 3
        host = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "?"
        lock.write_text(f"pid={os.getpid()} host={host} started={time.strftime('%Y-%m-%dT%H:%M:%S')}",
                        encoding="utf-8")
        import atexit
        atexit.register(lambda: lock.unlink(missing_ok=True))

    if args.agent:
        agent_cmd, agent_label = args.agent, "(raw)"
    elif args.executor:
        agent_cmd, agent_label = resolve_executor(args.executor, table), args.executor
    elif default_name and default_name in table:
        agent_cmd, agent_label = resolve_executor(default_name, table), f"{default_name} (default)"
    else:
        agent_cmd, agent_label = DEFAULT_AGENT, "(builtin claude)"
    if args.audit_agent:
        audit_cmd = args.audit_agent
    elif args.audit_executor:
        audit_cmd = resolve_executor(args.audit_executor, table)
    else:
        audit_cmd = ""

    if args.miners:
        if args.miner_agent:
            miner_cmd, miner_label = args.miner_agent, "(raw)"
        elif args.miner_executor:
            miner_cmd, miner_label = resolve_executor(args.miner_executor, table), args.miner_executor
        else:
            miner_cmd, miner_label = agent_cmd, agent_label
        if args.no_integrate:
            integrate_cmd, integrate_label = "", ""
        elif args.integrate_executor:
            integrate_cmd, integrate_label = resolve_executor(args.integrate_executor, table), args.integrate_executor
        elif audit_cmd:
            integrate_cmd, integrate_label = audit_cmd, (args.audit_executor or "(raw audit)")
        elif "audit" in table and "<" not in table["audit"]:
            integrate_cmd, integrate_label = table["audit"], "audit (fallback)"
        else:
            print("error: fan-out needs a STRONG integrator — pass --integrate-executor / "
                  "--audit-executor, or --no-integrate to integrate from the master session.",
                  file=sys.stderr)
            return 2
        return wave_mode(args, miner_cmd, miner_label, integrate_cmd, integrate_label)

    ceiling = ""
    if args.confidence_ceiling:
        ceiling = (f"\n   CONFIDENCE CEILING: you may not set confidence above "
                   f"`{args.confidence_ceiling}`; add the tag `needs-review` to new concepts — "
                   f"the audit pass promotes them.")

    examples = ""
    ex_path = HERE.parent / "reference" / "EXAMPLES.md"
    if ex_path.exists():
        examples = ("\n\nEXEMPLARY CYCLE — imitate the SHAPE (evidence → write → verify → "
                    "record → one-line report):\n" +
                    ex_path.read_text(encoding="utf-8", errors="ignore")[:4000])

    def make_prompt(extra: str = "") -> str:
        state, open_items = state_block(args.gem)
        return (CYCLE_PROMPT.format(gem=args.gem, state=state + extra,
                                    here=HERE, py=sys.executable, ceiling=ceiling) + examples,
                open_items)

    def audit():
        if not audit_cmd:
            return
        print("  == AUDIT pass ==")
        out = run_agent(audit_cmd,
                        AUDIT_PROMPT.format(gem=args.gem, here=HERE, py=sys.executable),
                        args.gem, args.agent_timeout, label="audit")
        print(f"  audit: {out[-300:]}")

    stop = (f"cycles={args.cycles}" if args.cycles else
            f"minutes={args.minutes}" if args.minutes else
            "until-dry" if args.until_dry else "forever")
    print(f"== okf-loop on '{args.gem.name}' | stop: {stop} | executor: "
          f"{'(dry-run)' if args.dry_run else agent_label + ' → ' + agent_cmd}"
          + (f" | audit: {audit_cmd} every {args.audit_every or 'end'}" if audit_cmd else "")
          + " ==")

    start = time.time()
    cycle = rejected_stops = 0
    base_fid, base_err, _ = gate_counts(args.gem) if not args.dry_run else (0, 0, "")
    if not args.dry_run and (base_fid or base_err):
        print(f"(pre-loop baseline: {base_fid} fidelity failure(s), {base_err} validate error(s) "
              f"already present — only NEW failures fail a cycle)")
    while True:
        if args.cycles and cycle >= args.cycles:
            break
        if args.minutes and (time.time() - start) >= args.minutes * 60:
            break
        cycle += 1
        prompt, open_items = make_prompt()
        print(f"\n--- cycle {cycle} | machine-open items: {open_items} ---")
        if args.until_dry and open_items == 0:
            print("  DRY — status shows nothing open. Stopping.")
            break
        if args.dry_run:
            print(prompt.split("Doctrine")[0].rstrip())
            print("  [dry-run] would invoke the executor here.")
            break
        out = run_agent(agent_cmd, prompt, args.gem, args.agent_timeout, label=f"cycle-{cycle}")
        print(f"  agent: {out[-300:]}")

        # driver-enforced gates — never trust the executor's self-report
        fid, errs, detail = gate_counts(args.gem)
        if fid > base_fid or errs > base_err:
            print(f"  GATES: FAILED (fidelity {base_fid}->{fid} · validate {base_err}->{errs}) "
                  f"— handing back to the executor")
            out2 = run_agent(agent_cmd,
                             FIX_PROMPT.format(gem=args.gem, detail=detail,
                                               here=HERE, py=sys.executable),
                             args.gem, args.agent_timeout, label=f"cycle-{cycle}-fix")
            print(f"  fix: {out2[-200:]}")
            fid, errs, _ = gate_counts(args.gem)
            if fid > base_fid or errs > base_err:
                print("  GATES: STILL FAILING — cycle flagged for the audit pass")
            else:
                print("  GATES: ok after fix")
        else:
            print(f"  GATES: ok (fidelity {fid} · validate {errs})")
        base_fid, base_err = min(base_fid, fid), min(base_err, errs)

        if "nothing-resolvable" in out.lower():
            _, open_now = state_block(args.gem)
            if open_now == 0:
                print("  stop ACCEPTED — status agrees: nothing open.")
                break
            rejected_stops += 1
            print(f"  stop REJECTED ({rejected_stops}/3) — {open_now} open item(s) remain; pushing back.")
            if rejected_stops >= 3:
                print("  executor cannot close the remaining items — stopping; run a stronger model "
                      "or resolve the dead-ends by hand.")
                break
        else:
            rejected_stops = 0

        if args.audit_every and audit_cmd and cycle % args.audit_every == 0:
            audit()
        if args.cycles and cycle >= args.cycles:
            break
        time.sleep(args.interval)

    if not args.dry_run:
        audit()
    print(f"\n== done: {cycle} cycle(s), {round(time.time() - start)}s ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
