# Fidelity profiles — onexus

Each kind of knowledge needs a different kind of rigor. The skill detects the
profile from the subject (or the user forces it with "...(profile: health)"). Each
profile defines: what is **verbatim** (untouchable), what needs a **citation**,
the **extra check**, and how to mark a **gap/uncertainty**. When in doubt between
two, use the stricter one.

**Verbatim via the WEB (all profiles):** harness fetch tools may summarize or
paraphrase what they return — never treat their output as verbatim. Download the
raw source to a local file first and excerpt byte-exact (see SKILL.md "Embed
sources"); no raw copy ⇒ the verbatim is a gap, never a paraphrase.

## sacred — scripture, prayer, ritual, liturgy
- **Verbatim and untouchable:** sacred formulas, verses, prayers, invocations,
  divine names. Copy exactly from the source, in the **original script +
  transliteration**. NEVER paraphrase, "fix", or complete from memory.
- **OCR warning:** OCR corrupts ligatures and diacritics in non-Latin scripts (a
  single altered mark can change a sacred word). Verify the text against the
  source image; with OCR only, mark "⚠ verify against source".
- **Citation:** edition/recension of each verse/passage.
- **Gap:** a missing component (a prayer, a litany, an appended section…) is a
  declared gap, never filled from memory.
- **Weak-model lockout:** an executor model below the audit tier never AUTHORS
  sacred verbatim — structure and cited prose only; verbatim enters exclusively
  via `okf_excerpt.py` byte-copies, verified by `okf_verify.py`.

## health — health, nutrition, medicine, fitness, drugs
- **Verbatim:** doses, numbers, drug and study names.
- **Mandatory citation:** every clinical claim with a source (study, WHO, NIH…),
  marking the **level of evidence** (meta-analysis > RCT > observational > opinion).
- **Check:** adversarial fact-check of risky claims; separate consensus from hypothesis.
- **Never** invent advice; flag when the right answer is "see a doctor".

## legal — laws, regulations, contracts
- **Verbatim:** the text of the provision (article/statute/precedent) — copy,
  never paraphrase the letter of the law.
- **Citation:** exact reference (e.g. "Civil Code, Art. 12").
- **Watch:** validity (repealed/amended?) and jurisdiction.

## culinary — recipes, cooking technique
- **Verbatim:** ingredients, quantities, temperatures, times.
- **Structure:** yield + steps in exact order.
- **Citation:** book/author of the recipe.

## technical — software, code, engineering, APIs
- **Verbatim:** commands, code, versions, flags.
- **Citation:** official documentation.
- **Check:** don't invent an API/flag; record the version referred to.

## history — facts, history, geography, biography
- **Verbatim:** dates, proper names, places.
- **Citation:** verifiable source; distinguish consensus from historiographical dispute.

## philosophy — ideas, theory, comparative religion
- **Correct attribution:** each idea to the right author/work (classic error:
  swapping who said what).
- **Verbatim:** direct quotes in quotation marks, with the passage.
- **Citation:** work/section.

## general — any other subject
(education, study technique, productivity, self-improvement land here too)
- Prose faithful to the source, no invention. Every claim traceable to a source.
- Cite what grounds it; mark uncertainty explicitly; when a claim leans on
  research, name the study/author rather than "studies show".

## Provenance (every concept) — `source_type` + `confidence`
Regardless of profile, every concept carries WHERE it came from and HOW trustworthy it is:
- **`source_type`**: `digital` (clean e-text, e.g. a critical edition) · `ocr` (scan — verbatim suspect) · `web` · `mixed` · `none` (abstract).
- **`confidence`**: `high` (verified digital source / safe verbatim) · `medium` (web or secondary) · `low` (OCR, unverified verbatim).
- Key rule of the **sacred** profile: OCR ⇒ `low` and the verbatim becomes a gap; verified digital ⇒ `high`.
- Bulk/retroactive: `scripts/okf_stamp.py`. In the graph, the node's **border** shows confidence (green/yellow/red).
