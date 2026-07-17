# EXAMPLES — one exemplary growth cycle (imitate the SHAPE, not the subject)

The executor of a cycle behaves exactly like this. Subject here is a fictional
"Stoicism Gem, queue head = write practice/morning-preparation"; yours will differ.

## 1. OBSERVE
Read `_loop-state.md`: standing orders say content in the user's language,
profile philosophy, ceiling medium.
Queue head: `1. write practice/morning-preparation — source: _sources/meditations.md, Book II opening`.

## 2. EVIDENCE FIRST (before any writing)
The source is already local. Stage the exact passage byte-exact:

    python3 <SKILL_DIR>/scripts/okf_excerpt.py "<abs>/_sources/meditations.md" "<gem>" \
      "references/meditations-ii-1.md" --from "Begin the morning by saying" --to "and to act against" \
      --title "Meditations II.1 — morning preparation" --citation "Marcus Aurelius, Meditations, trans. G. Long" \
      --source-type digital --confidence high

(If the source were a web page: download RAW first — `curl -L <url> -o _sources/page.html` —
then excerpt from the saved file. NEVER quote from memory or from a fetch summary.)

## 3. WRITE — one concept, template shape, relative links
`practice/morning-preparation.md`:

    ---
    type: Practice
    title: Morning preparation
    description: Marcus Aurelius' exercise of rehearsing the day's difficult people before meeting them.
    tags: [practice, meditations, needs-review]
    timestamp: 2026-01-01T09:00:00Z
    source_type: digital
    confidence: medium
    ---

    # What it is

    Start the day by naming, in advance, the kinds of difficulty one will meet —
    described in [Meditations II.1](../references/meditations-ii-1.md). It pairs
    with the [evening review](evening-review.md) as the day's other bookend.

    # Source text (verbatim)

    > Begin the morning by saying to thyself, I shall meet with the busy-body,
    > the ungrateful, arrogant, deceitful, envious, unsocial.

    # Citations

    [1] [Meditations II.1 — trans. G. Long](../references/meditations-ii-1.md)

Note: the verbatim block was PASTED from the references file the excerpt script
created — not typed. Confidence stays `medium` + tag `needs-review` (ceiling).

## 4. VERIFY (mechanical — fix anything that fails before moving on)

    python3 <SKILL_DIR>/scripts/okf_verify.py "<gem>" --concept practice/morning-preparation --strict
    python3 <SKILL_DIR>/scripts/okf_validate.py "<gem>"

## 5. RECORD
- `_loop-state.md`: ledger `+ c7 practice/morning-preparation`; queue: remove
  item 1; map: `morning-preparation [x]`; no new dead-ends.
- Update `practice/index.md` with the new entry.
- `python3 <SKILL_DIR>/scripts/okf_log.py "<gem>" --kind Loop --agent "<harness>" --model "<model>" --note "c7: practice/morning-preparation (Meditations II.1 verbatim embedded)"`

## 6. REPORT (one line, nothing else)
    improved: practice/morning-preparation (Meditations II.1 staged + verbatim verified)

## Counter-examples (instant cycle failure)
- Writing the quote "from what I remember of the text" → verify FAILS, cycle invalid.
- "I couldn't find the source, so I summarized from general knowledge" → forbidden;
  correct move: `blocked: needs <named source>` in dead-ends, take next queue item.
- Editing 4 concepts "while I was at it" → one bounded task per cycle, nothing else.
- Reporting `nothing-resolvable` with open queue/map items → machine-rejected.
