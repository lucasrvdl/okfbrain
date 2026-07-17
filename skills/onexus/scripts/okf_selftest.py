#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""okf_selftest.py — one command that proves the factory is sane.

Builds a throwaway mini-gem in a temp dir and exercises every script as a
BLACK BOX (subprocess, like real callers do): validate, status, search,
verify (blockquote match + prose-quote fail + strict exit codes), excerpt
(happy path + empty-selector + missing --to guards), stamp (fill-only-missing),
migrate (dry-run plan), log, and okf_loop's queue parser (continuation lines)
+ gem lock. Run it after ANY change to the skill, on any machine:

    python3 okf_selftest.py        (or: py -3.11 / uv run)

Exit 0 = all green. Exit 1 = something regressed (each failure is printed).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PY = sys.executable
FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("  ✓ " if ok else "  ✗ ") + name + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(HERE / script), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def build_gem(root: Path) -> Path:
    b = root / "selftest-gem"
    (b / "area-a").mkdir(parents=True)
    (b / "references").mkdir()
    (b / "_learning").mkdir()
    (b / "index.md").write_text(
        '---\nokf_version: "0.1"\n---\n\n# Selftest gem\n\n'
        "Fidelity profile: general\n\n"
        "# Areas\n\n* [Area A](area-a/) - test area\n\n"
        "# Gaps\n\n- [ ] future topic — needs source X\n- [-] out of topic — out of scope: test\n",
        encoding="utf-8")
    (b / "log.md").write_text("# Update Log\n\n## 2026-01-01\n* **Creation**: selftest gem.\n",
                              encoding="utf-8")
    (b / "references" / "src.md").write_text(
        "---\ntype: Source\ntitle: Test source\ndescription: verbatim source\n"
        "tags: [source]\nsource_type: digital\nconfidence: high\n---\n\n# Text\n\n"
        "The quick brown fox jumps over the lazy philosopher of Dīkṣā.\n"
        "A second sentence exists purely to be excerpted precisely.\n",
        encoding="utf-8")
    (b / "area-a" / "good.md").write_text(
        "---\ntype: Concept\ntitle: Good concept about Dīkṣā\n"
        "description: A well-formed concept.\ntags: [test]\n"
        "timestamp: 2026-01-01T00:00:00Z\nsource_type: digital\nconfidence: high\n---\n\n"
        "# Overview\n\nLinks to [bad](bad.md) and a [future one](future.md).\n\n"
        "> The quick brown fox jumps over the lazy philosopher of Dīkṣā.\n\n"
        "# Citations\n\n[1] [Test source](../references/src.md)\n",
        encoding="utf-8")
    (b / "area-a" / "bad.md").write_text(
        "---\ntype: Concept\ntitle: Bad concept\ndescription: Uncited, with a fabricated quote.\n"
        "tags: [test]\ntimestamp: 2026-01-01T00:00:00Z\nsource_type: web\nconfidence: medium\n---\n\n"
        "# Overview\n\nIt is said that \"this exact long sentence was never saved into any source file at all\".\n"
        "Linked from [good](good.md).\n",
        encoding="utf-8")
    (b / "area-a" / "index.md").write_text(
        "# Area A\n\n* [Good](good.md) - good\n* [Bad](bad.md) - bad\n", encoding="utf-8")
    (b / "_loop-state.md").write_text(
        "---\ntype: Loop State\ntitle: selftest — loop state\ndescription: test state.\n"
        "tags: [loop, meta]\ntimestamp: 2026-01-01T00:00:00Z\n---\n\n"
        "# STATUS\n\nRUNNING (test)\n\n# Coverage map\n\n- [ ] area-a\n  - [x] good · [ ] future\n\n"
        "# Queue\n\n1. write area-a/future — the first line\n"
        "   + continuation with the SOURCE POINTER that must reach the executor\n"
        "2. second item single line\n\n# Dead-ends\n\n- (none)\n",
        encoding="utf-8")
    return b


def main() -> int:
    print(f"okf-selftest — scripts at {HERE}")
    tmp = Path(tempfile.mkdtemp(prefix="okf-selftest-"))
    try:
        b = build_gem(tmp)

        # --- validate ---
        r = run("okf_validate.py", str(b), "--json")
        d = json.loads(r.stdout or "{}")
        check("validate: conformant, 0 errors", d.get("conformant") is True and not d.get("errors"),
              str(d.get("errors"))[:120])
        (b / "_staging" / "x").mkdir(parents=True)
        (b / "_staging" / "x" / "draft.md").write_text("no frontmatter at all", encoding="utf-8")
        r = run("okf_validate.py", str(b), "--json")
        d = json.loads(r.stdout or "{}")
        check("validate: ignores _staging/ drafts", not d.get("errors"), str(d.get("errors"))[:120])

        # --- status ---
        r = run("okf_status.py", str(b), "--json")
        s = json.loads(r.stdout or "{}")
        check("status: knowledge/sources split", s.get("knowledge") == 2 and s.get("sources") == 1,
              f"knowledge={s.get('knowledge')} sources={s.get('sources')}")
        check("status: pending link detected", len(s.get("pending_links", [])) == 1,
              str(s.get("pending_links")))
        check("status: gaps parsed", len(s.get("gaps", {}).get("open", [])) == 1
              and len(s.get("gaps", {}).get("out_of_scope", [])) == 1, str(s.get("gaps"))[:120])
        check("status: loop-state queue seen", s.get("loop_state", {}).get("queue_len") == 2,
              str(s.get("loop_state")))

        # --- search (diacritic folding) ---
        r = run("okf_search.py", str(b), "diksa", "--json")
        hits = json.loads(r.stdout or "[]")
        check("search: 'diksa' finds Dīkṣā", any("good" in h["id"] for h in hits), r.stdout[:120])

        # --- verify ---
        r = run("okf_verify.py", str(b), "--json")
        v = json.loads(r.stdout or "{}")
        check("verify: blockquote matched", v.get("quotes", {}).get("matched") == 1, str(v.get("quotes")))
        check("verify: fabricated prose quote caught", len(v.get("unmatched_prose", [])) == 1,
              str(v.get("unmatched_prose"))[:120])
        check("verify: uncited caught", v.get("uncited") == ["area-a/bad"], str(v.get("uncited")))
        r = run("okf_verify.py", str(b), "--strict")
        check("verify --strict exits 1 on failures", r.returncode == 1, f"rc={r.returncode}")
        r = run("okf_verify.py", str(b), "--concept", "area-a/good", "--strict")
        check("verify --concept scoping clean", r.returncode == 0, f"rc={r.returncode} {r.stdout[-80:]}")

        # --- excerpt guards ---
        r = run("okf_excerpt.py", str(b / "references" / "src.md"), str(b), "references/cut.md",
                "--from", "A second sentence", "--to", "precisely.", "--title", "Cut")
        check("excerpt: happy path", r.returncode == 0 and (b / "references" / "cut.md").exists(),
              r.stderr[-80:])
        r = run("okf_excerpt.py", str(b / "references" / "src.md"), str(b), "references/x.md",
                "--lines", "99-99", "--title", "X")
        check("excerpt: empty selection refused", r.returncode != 0, f"rc={r.returncode}")
        r = run("okf_excerpt.py", str(b / "references" / "src.md"), str(b), "references/y.md",
                "--from", "The quick", "--to", "NO-SUCH-MARKER", "--title", "Y")
        check("excerpt: missing --to refused", r.returncode != 0, f"rc={r.returncode}")

        # --- stamp (fill-only-missing) ---
        r = run("okf_stamp.py", str(b), "--default", "web:low")
        check("stamp: --default never overwrites", "already stamped" in r.stdout
              and "OK" not in r.stdout.replace("OK ", "OK", 1)[:0 or None] or "stamped 0" in r.stdout,
              r.stdout[-120:])

        # --- migrate (dry-run plan on a legacy-style index) ---
        legacy = tmp / "legacy-gem"
        legacy.mkdir()
        (legacy / "index.md").write_text(
            "---\nokf_version: \"0.1\"\nextra: nope\n---\n\n# Legacy\n\n# Gaps\n\n* prose gap one\n",
            encoding="utf-8")
        r = run("okf_migrate.py", str(legacy))
        check("migrate: dry-run plans fixes", "FIX" in r.stdout and "checkbox" in r.stdout,
              r.stdout[-120:])
        check("migrate: dry-run writes nothing", "extra: nope" in
              (legacy / "index.md").read_text(encoding="utf-8"), "")

        # --- embed (optional dep: pass either way) + search fallback ---
        r = run("okf_embed.py", str(b))
        check("embed: builds or degrades gracefully",
              r.returncode == 0 or (r.returncode == 3 and "model2vec" in r.stderr),
              f"rc={r.returncode} {r.stderr[-80:]}")
        r = run("okf_search.py", str(b), "diksa", "--json")
        hits = json.loads(r.stdout or "[]")
        check("search: works with/without semantic index",
              r.returncode == 0 and any("good" in h["id"] for h in hits), r.stdout[:100])

        # --- log ---
        r = run("okf_log.py", str(b), "--note", "selftest entry", "--kind", "Update")
        check("log: appends", r.returncode == 0 and "selftest entry" in
              (b / "log.md").read_text(encoding="utf-8"), r.stdout[-80:])

        # --- loop: queue parser (continuation) + lock + list-executors ---
        sys.path.insert(0, str(HERE))
        import importlib.util
        spec = importlib.util.spec_from_file_location("okf_loop", HERE / "okf_loop.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        items = mod.queue_items(b, 2)
        check("loop: queue continuation folded", len(items) == 2
              and "SOURCE POINTER" in items[0] and items[1].startswith("2."),
              str(items)[:140])
        (b / ".okf-loop.lock").write_text("pid=0 host=test started=now", encoding="utf-8")
        r = run("okf_loop.py", str(b), "--cycles", "1", "--agent", "echo-nothing")
        check("loop: gem lock refuses second run", r.returncode == 3 and "LOCKED" in (r.stderr + r.stdout),
              f"rc={r.returncode}")
        (b / ".okf-loop.lock").unlink()
        r = run("okf_loop.py", str(b), "--list-executors")
        check("loop: --list-executors", r.returncode == 0 and "executor profiles" in r.stdout,
              r.stdout[:80])

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'ALL GREEN — factory sane' if not FAILS else f'{len(FAILS)} FAILURE(S): ' + ', '.join(FAILS)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
