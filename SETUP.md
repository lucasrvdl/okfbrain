# SETUP — a new machine in ~10 minutes

Get okfbrain running on a fresh computer (Windows, macOS or Linux). "Brains" are
just folders of markdown — the "installation" is only the skill, Python, and
whichever executors you plan to use.

## 1. The skill

```bash
git clone <this-repo-url> ~/okfbrain-repo
cp -r ~/okfbrain-repo/skills/okfbrain ~/.claude/skills/     # Claude Code
```

Other master harnesses (optional — the skill is harness-agnostic):

```bash
cp -r ~/okfbrain-repo/skills/okfbrain ~/.config/opencode/skills/   # opencode
# codex/gemini/etc.: your harness's equivalent skills folder
```

Updating later: `git -C ~/okfbrain-repo pull`, then repeat the `cp`.

## 2. Python (the scripts' only dependency)

- **macOS/Linux**: `python3` is already there → `pip3 install pyyaml`
  (or install [uv](https://docs.astral.sh/uv/) and forget about it:
  `uv run script.py` resolves dependencies by itself).
- **Windows**: `py -3.11` + `py -3.11 -m pip install pyyaml`
  (`python3` usually does NOT exist on Windows — it's a Store alias).

Test: `python3 ~/.claude/skills/okfbrain/scripts/okf_validate.py --help`

## 3. Executors (only the ones you'll use on THIS machine)

The fleet is defined by aliases in `executors.json` (inside the skill; no keys
in it, by design). Full recipes: `reference/EXECUTORS.md`.

### 3a. Claude (profiles `haiku`, `sonnet`, `audit`)
Install Claude Code and log in. Done — nothing else.

### 3b. Cloud gateways via opencode (profiles `flash`, `flash-pro`, `openrouter`, …)
These are CLOUD models: they run fine on any low-power machine, no GPU.

1. Install [opencode](https://opencode.ai) and run `opencode auth login`
   (pick your gateway — e.g. OpenCode Go or OpenRouter; the key lives in
   opencode's vault, per machine).
2. Permissions for UNATTENDED runs (otherwise `opencode run` auto-rejects
   every tool) — in `~/.config/opencode/opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "edit": "allow",
    "bash": "allow",
    "webfetch": "allow",
    "external_directory": "allow"
  }
}
```

3. Echo test: `opencode run --model <provider/model> "Reply with: OK"`

### 3c. Local models / other APIs (optional)
Ollama, LM Studio, Ollama Cloud, any OpenAI-compatible API — each is one
config block + one alias. See `reference/EXECUTORS.md`. Golden rule: **API
keys never go into executors.json** (they live in the CLI's vault or in
environment variables referenced as `{env:VAR}`).

### 3d. Personal preferences (survive repo updates)
Create `~/.okfbrain/executors.json`:

```json
{ "default": "haiku", "executors": {} }
```

Set `"default"` to whichever alias you want as your everyday executor, and add
your own aliases under `"executors"` — this file wins over the skill's defaults.

### 3e. Semantic search (optional, recommended)
One light CPU-only dependency turns search hybrid (BM25 + vectors — synonyms work):

```bash
pip3 install model2vec numpy
python3 ~/.claude/skills/okfbrain/scripts/okf_embed.py <a-brain>   # builds _index/ inside the brain
```

The multilingual model (~250MB) downloads once, then everything is offline. No GPU,
no torch, no LLM tokens. Without it, search stays lexical — everything else works.

## 4. Your brains

They're folders — three ways to bring them to a new machine:
- **git** (recommended): version each brain in a private repo (the skill offers
  this at creation time) and clone it anywhere;
- **cloud drive**: drag the folder;
- **scp/rsync** between machines.

Each brain's `viz.html` opens in any browser (internet needed only on first
load, for the CDN libraries).

## 5. Final smoke test (2 minutes)

```bash
cd ~/.claude/skills/okfbrain
python3 scripts/okf_selftest.py                               # 24 checks — ALL GREEN?
python3 scripts/okf_loop.py --list-executors                  # fleet visible?
python3 scripts/okf_validate.py <a-brain>                     # 0 errors?
python3 scripts/okf_status.py   <a-brain>                     # X-ray ok?
python3 scripts/okf_search.py   <a-brain> "some term"         # search ok?
```

A new executor NEVER goes to production without the **admission test**
(`reference/EXECUTORS.md`, "Checks" section): 1–2 cycles on a scratch brain +
a strong-model audit of the delta; demote-rate ≤ ~20% = approved.

## Per-machine notes

- **Low-power machine (thin laptop, mini PC)**: master = your harness's default
  model in-session; miners/executors = cloud profiles (they don't need local
  compute). Don't bother with local models here. Short sessions work well: the
  `_loop-state.md` makes interruption free.
- **GPU workstation**: add local models via Ollama/LM Studio (config blocks in
  `reference/EXECUTORS.md`) and run overnight loops with `--minutes N` or
  fan-out with `--miners N`.
- **Windows**: use `py -3.11` instead of `python3` in every command above.
