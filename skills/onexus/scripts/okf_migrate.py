#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""okf_migrate.py — normalize a pre-v2 OKF gem to the current canon. SAFE BY DEFAULT.

Fixes (only with --apply; default is a dry-run PLAN):
  1. Root index.md frontmatter -> exactly `okf_version` (extra keys dropped, reported).
  2. Root index.md fidelity-profile line — inserted with --profile <name> if absent.
  3. Gaps section (heading matching /lacunas|gaps/i): prose bullets -> `- [ ] ` checkboxes.
  4. Non-root index.md / log.md: frontmatter stripped (§6/§7).
Reports only (never auto-fixed — they need judgment or a different tool):
  - log.md date headings that are not pure `YYYY-MM-DD`
  - concepts missing provenance (fix with okf_stamp.py)
  - WikiLinks `[[...]]` in concept bodies (fix by hand — targets are ambiguous)

--backup <dir>: before modifying a file, copy it there (mirrored relative path).

Run:  uv run okf_migrate.py <gem> [--profile general] [--apply] [--backup <dir>]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

RESERVED = {"index.md", "log.md"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GAPS_HEAD = re.compile(r"^#{1,6}\s*.*\b(lacunas|gaps)\b", re.IGNORECASE)
PROFILE_LINE = re.compile(r"^(perfil de fidelidade|fidelity profile)\s*:", re.IGNORECASE)
BULLET = re.compile(r"^(\s*)[-*]\s+(?!\[[ x~-]\])(.+)$")
WIKILINK = re.compile(r"\[\[[^\]]+\]\]")


def is_meta(rel: str) -> bool:
    return any(part.startswith("_") for part in rel.split("/"))


def split_fm(text: str):
    """-> (fm_lines or None, body_text)."""
    if not text.startswith("---"):
        return None, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None, text


class Migrator:
    def __init__(self, gem: Path, apply: bool, backup: Path | None):
        self.gem, self.apply, self.backup = gem, apply, backup
        self.fixes: list[str] = []
        self.warns: list[str] = []

    def save(self, path: Path, text: str, what: str):
        rel = path.relative_to(self.gem).as_posix()
        self.fixes.append(f"{rel}: {what}")
        if not self.apply:
            return
        if self.backup:
            dest = self.backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(path, dest)
        path.write_text(text, encoding="utf-8")

    def root_index(self, path: Path):
        text = path.read_text(encoding="utf-8").lstrip("﻿")
        fm, body = split_fm(text)
        changed, notes = False, []
        version = "0.1"
        if fm is not None:
            try:
                meta = yaml.safe_load("\n".join(fm)) or {}
            except yaml.YAMLError:
                meta = {}
            if isinstance(meta, dict):
                version = str(meta.get("okf_version", "0.1"))
                extra = sorted(set(meta) - {"okf_version"})
                if extra:
                    changed = True
                    notes.append(f"dropped extra frontmatter keys {extra} (§11)")
        else:
            body = text
            changed = True
            notes.append("added okf_version frontmatter")

        lines = body.split("\n")
        # profile line
        if not any(PROFILE_LINE.match(l.strip()) for l in lines):
            if self.args_profile:
                ins = next((i + 1 for i, l in enumerate(lines) if l.startswith("# ")), 0)
                lines[ins:ins] = ["", f"Perfil de fidelidade: {self.args_profile}"]
                changed = True
                notes.append(f"inserted profile line ({self.args_profile})")
            else:
                self.warns.append("index.md: no fidelity-profile line (pass --profile <name> to insert)")
        # gaps checkboxes
        in_gaps, conv = False, 0
        for i, l in enumerate(lines):
            if l.startswith("#"):
                in_gaps = bool(GAPS_HEAD.match(l))
                continue
            if in_gaps:
                m = BULLET.match(l)
                if m:
                    lines[i] = f"{m.group(1)}- [ ] {m.group(2)}"
                    conv += 1
        if conv:
            changed = True
            notes.append(f"converted {conv} prose gap bullet(s) to checkboxes")

        if changed:
            new = "---\nokf_version: \"" + version + "\"\n---\n" + "\n".join(lines).lstrip("\n")
            self.save(path, new.rstrip("\n") + "\n", "; ".join(notes))

    def strip_fm(self, path: Path, spec: str):
        text = path.read_text(encoding="utf-8").lstrip("﻿")
        fm, body = split_fm(text)
        if fm is not None:
            self.save(path, body.lstrip("\n").rstrip("\n") + "\n", f"stripped frontmatter ({spec})")

    def check_log(self, path: Path):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## ") and not ISO_DATE.match(line[3:].strip()):
                self.warns.append(f"log.md: heading `{line[3:].strip()}` is not pure YYYY-MM-DD (fix by hand)")

    def check_concept(self, path: Path, rel: str):
        text = path.read_text(encoding="utf-8").lstrip("﻿")
        fm, body = split_fm(text)
        meta = {}
        if fm is not None:
            try:
                meta = yaml.safe_load("\n".join(fm)) or {}
            except yaml.YAMLError:
                pass
        if isinstance(meta, dict) and not ("source_type" in meta and "confidence" in meta):
            self.no_prov += 1
        n = len(WIKILINK.findall(body))
        if n:
            self.warns.append(f"{rel}: {n} WikiLink(s) `[[...]]` — convert to [title](relative.md) by hand")

    def run(self, profile: str | None):
        self.args_profile = profile
        self.no_prov = 0
        for p in sorted(self.gem.rglob("*.md")):
            rel = p.relative_to(self.gem).as_posix()
            if is_meta(rel):
                continue
            if p.name == "index.md":
                if p.parent == self.gem:
                    self.root_index(p)
                else:
                    self.strip_fm(p, "§6 non-root index")
            elif p.name == "log.md":
                self.strip_fm(p, "§7 log")
                self.check_log(p)
            else:
                self.check_concept(p, rel)
        if self.no_prov:
            self.warns.append(f"{self.no_prov} concept(s) missing provenance — fix with okf_stamp.py")


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize a pre-v2 OKF gem (dry-run by default).")
    ap.add_argument("gem", type=Path)
    ap.add_argument("--profile", help="fidelity profile to record in the root index if absent")
    ap.add_argument("--apply", action="store_true", help="write the fixes (default: plan only)")
    ap.add_argument("--backup", type=Path, help="copy each file here before modifying it")
    args = ap.parse_args()
    if not args.gem.is_dir():
        print(f"error: {args.gem} is not a directory", file=sys.stderr)
        return 2

    m = Migrator(args.gem, args.apply, args.backup)
    m.run(args.profile)

    mode = "APPLIED" if args.apply else "PLAN (dry-run — pass --apply to write)"
    print(f"okf-migrate — {args.gem.name} — {mode}")
    for f in m.fixes:
        print(f"  FIX  {f}")
    for w in m.warns:
        print(f"  warn {w}")
    if not m.fixes and not m.warns:
        print("  ✓ already canonical — nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
