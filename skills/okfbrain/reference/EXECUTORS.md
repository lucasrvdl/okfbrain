# EXECUTORS — adding models, backends and API keys to the fleet

The fleet is `executors.json` (skill dir = shipped defaults; `~/.okfbrain/executors.json`
= personal overrides, wins on conflict). Each entry is just `"alias": "<agent CLI>"`.
`okf_loop.py --list-executors` shows the fleet; `--executor <alias>` uses one.

**GOLDEN RULE: no API keys in executors.json** — it is versioned/shared. Keys live in
the harness's own vault (`opencode auth login` → `~/.local/share/opencode/auth.json`)
or in environment variables referenced from `opencode.jsonc` as `{env:VAR_NAME}`.

## One-time: provider blocks in opencode.jsonc (needed by recipes 3–5)

opencode only routes `ollama/…`, `lmstudio/…` and `ollama-cloud/…` if those providers
are declared in `~/.config/opencode/opencode.jsonc`. Paste once (no keys in the file):

```jsonc
"provider": {
  "ollama": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "Ollama (local)",
    "options": { "baseURL": "http://localhost:11434/v1" },
    "models": { "<your-model>": { "tools": true } }
  },
  "lmstudio": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "LM Studio (local)",
    "options": { "baseURL": "http://localhost:1234/v1" },
    "models": {}
  },
  "ollama-cloud": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "Ollama Cloud",
    "options": { "baseURL": "https://ollama.com/v1", "apiKey": "{env:OLLAMA_API_KEY}" },
    "models": {}
  }
}
```

OpenRouter and the OpenCode Go/Zen gateways need NO block — they are native opencode
providers; `opencode auth login` is enough.

## Recipes

### 1. New model on an already-logged gateway (OpenCode Go / Zen)
```
opencode models | grep -i <nome>          # discover the exact id
```
Add to executors.json: `"apelido": "opencode run --model opencode-go/<id>"`. Done.

### 2. OpenRouter (hundreds of models, one key)
1. Create a key at openrouter.ai.
2. `opencode auth login` → pick OpenRouter → paste the key (stored in opencode's vault).
3. Alias: `"kimi": "opencode run --model openrouter/<provider/model>"`.

### 3. New local Ollama model
1. `ollama pull <modelo>`
2. Declare it in `~/.config/opencode/opencode.jsonc` under `provider.ollama.models`:
   `"<modelo>": { "name": "<display>", "tools": true }`
3. Alias: `"x": "opencode run --model ollama/<modelo>"`.

### 4. LM Studio (local)
1. Load the model in LM Studio → Developer → Start Server (port 1234).
2. Copy the model id shown by LM Studio.
3. Declare it under `provider.lmstudio.models` in opencode.jsonc (block above).
4. Replace the `<placeholder>` in the `lmstudio` alias.

### 5. Ollama Cloud
1. Get a key at ollama.com → set it as an environment variable (e.g. `OLLAMA_API_KEY`).
2. The `ollama-cloud` provider block (above) reads it via `"apiKey": "{env:OLLAMA_API_KEY}"`.
3. Declare the subscribed models under `provider.ollama-cloud.models`; fix the alias.

### 6. Any other OpenAI-compatible API (DeepSeek direct, Groq, Mistral, Z.AI, …)
New block in opencode.jsonc:
```jsonc
"minha-api": {
  "npm": "@ai-sdk/openai-compatible",
  "name": "Minha API",
  "options": { "baseURL": "https://api.exemplo.com/v1", "apiKey": "{env:MINHA_API_KEY}" },
  "models": { "<model-id>": { "tools": true } }
}
```
Alias: `"m": "opencode run --model minha-api/<model-id>"`.

### 7. Pi coding agent (pi.dev — multi-provider, zero shared state)
Pi is a minimal agentic CLI (read/write/edit/bash) whose providers and keys are
configured in Pi itself — never in executors.json.
1. `npm install -g --ignore-scripts @earendil-works/pi-coding-agent` (CLI: `pi`).
2. Configure the provider/key once inside Pi (run `pi`, then `/login`; stored
   under `~/.pi/agent/`).
3. Alias: `"pi-x": "pi -p -nc --no-session --provider <provider> --model <id>"`.
   - `-p` non-interactive · `-nc` ignores AGENTS.md/CLAUDE.md (miners run clean)
   - `--no-session` = ephemeral, nothing written to shared state — parallel pi
     miners never contend (session-database CLIs are the ones that deadlock).
Note: `pi -p` waits forever when stdin is an open pipe — okf_loop closes stdin
for you; spawning pi from your own scripts, append `</dev/null`.
Windows note: npm installs pi as a `.cmd` shim, and cmd.exe truncates command
lines at the first newline — so okf_loop hands multiline prompts to `.cmd`
CLIs via stdin instead (pi reads piped stdin as the message; nothing to set).

### 8. Agent CLIs that aren't opencode (claude, codex, gemini, hermes…)
The alias is just the full command, e.g.
`"haiku": "claude -p --model haiku --permission-mode acceptEdits --allowedTools Bash(py:*),Bash(uv:*),WebFetch,WebSearch"`.
Requirement: the CLI must be AGENTIC (file+shell tools) and run non-interactively.
A bare LLM call (`ollama run`, `curl` to a chat API) is NOT an executor — no hands.

## Checks before trusting a new executor
1. Echo test: `opencode run --model <x> "Responda apenas: OK"`.
2. Non-interactive permissions: opencode needs the `permission: allow` block in
   opencode.jsonc (edit/bash/webfetch/external_directory) or it auto-rejects tools.
3. **Admission test** (the real gate): 1–2 cycles on a scratch/pilot brain,
   `okf_loop.py <brain> --cycles 2 --executor <alias> --confidence-ceiling medium`,
   then a strong-model audit of the delta. Approve if the audit demote-rate is low
   (~≤20%) and okf_verify/validate pass. Record the verdict in the brain's log.

Batch-size note: when a MASTER agent drives okf_loop from inside a harness turn,
invoke it as repeated `--cycles 1` (multi-cycle batches can exceed the harness
shell timeout of ~10 min). From a plain terminal, any batch size works.

## Fan-out (parallel miners)

Any alias above can be a MINER — this is how non-Claude models (DeepSeek,
Ollama, OpenRouter…) work for a brain in parallel:

```
okf_loop.py <brain> --cycles 3 --miners 6 --miner-executor flash --integrate-executor audit
okf_loop.py <brain> --cycles 1 --miners 6 --no-integrate   # master session integrates _staging/
```

Miners are write-fenced to `_staging/<slug>/` (draft + raw sources); only the
integrator writes the brain. Prefer stateless miners (recipe 7's `--no-session`
pi aliases) for big waves — CLIs with a shared session store can lock under
concurrency. Doctrine: LOOP.md "Fan-out". Timing note from a
harness turn: one wave lasts about as long as its SLOWEST miner — with the
~10 min shell timeout, prefer `--cycles 1` per invocation and background runs
for big waves.
