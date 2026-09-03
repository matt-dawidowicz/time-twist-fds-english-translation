# Translation intent-gap audit

The intent-gap audit identifies playable scenario lines that deserve renewed
editorial attention under the project's intent-first translation policy. It is a
**triage tool**, not an automatic Japanese translator and not a numerical grade
of translation quality.

## Why it exists

Earlier prose passes sometimes optimized visible character count before the
current compression and layout tooling existed. Those passes produced valuable
Japanese, register, voice, dialect, sentiment, and characterization analysis,
but a short playable line could still become flatter than the reviewed natural
reading.

The current workflow reverses that pressure:

1. establish the best English supported by the Japanese and review evidence;
2. preserve meaning, implication, sentiment, stance, register, voice, subtext,
   humor, hesitation, emphasis, and dramatic rhythm;
3. choose a safe minimum-row layout;
4. recompress the complete bank, using the verified Rust accelerator when useful;
5. shorten prose only if the source-faithful target still cannot satisfy hard ROM
   constraints after the engineering options are exhausted.

`work/tools/translation_intent_audit.py` helps find the records most likely to
benefit from that renewed review.

## Evidence used

The tool reads the generated per-bank checkpoints in
`work/translation_workbook_banks/*.json`. It uses only fields that the existing
review pipeline already records, including:

- `exact_japanese_source`;
- `literal_english_meaning`;
- `final_natural_english_translation`;
- `patch_safe_english_translation`;
- `speaker_or_narration_identity`;
- `dialect_or_register`;
- `problems_with_current_english`;
- `problem_categories`;
- `nuance_lost_in_patch_safe_version`;
- `requires_technical_expansion`;
- `requires_gameplay_context`;
- `unresolved_ambiguity`.

This is deliberately narrower than pretending that an automated metric can
understand Japanese sentiment or literary intent by itself. The tool surfaces
**existing human/source-grounded evidence**; the editor still evaluates the
Japanese, scene, sentiment, and established character voice.

## What counts as a gap

The audit normalizes presentation controls, typographic variants, review-only
speaker-label aliases, slash separators, ellipsis encoding, and whitespace before
comparing the natural and playable English. Therefore these are *not* ranked
merely because they differ mechanically:

```text
When was the last time I saw a blue sky?
When was the last time{CTRL:0}I saw a blue sky?
```

Likewise, `Protagonist:` versus the ROM's `Me:`, curly quotes, or an ellipsis
glyph versus three periods do not create an intent gap by themselves.

A record enters the repair queue when the project evidence contains a substantive
unresolved signal such as:

- visible natural/playable wording actually differs;
- the workbook explicitly records nuance lost in the patch-safe version;
- the current-English review records an outstanding problem;
- the problem category is not simply `Accurate`;
- technical expansion is marked useful or required;
- gameplay/staging evidence or an unresolved ambiguity still blocks confidence.

A `problems_with_current_english` entry beginning with
`Resolved in the playable text:` is historical resolution evidence, not an
outstanding problem, and does not by itself requeue the record.

Marked register, dialect, voice, or sentiment is **context that increases the
priority of a real gap**. It does not create an intent gap when the reviewed
natural and playable lines already agree and no other unresolved evidence exists.
This distinction prevents faithful but stylistically interesting lines from
crowding out genuinely compressed or semantically damaged ones.

The score is only a deterministic queue-ordering heuristic. **It must never be
used as an automatic accept/reject threshold for prose.**

## Runtime/staging blockers

Some records cannot be resolved from text alone. If
`requires_gameplay_context=yes` or `unresolved_ambiguity` is nonempty, the audit
marks the candidate `runtime_evidence_required` and sorts it behind immediately
actionable records.

That is intentional. A high apparent semantic gap is not permission to invent a
speaker, referent, punctuation reading, or dramatic beat when staging evidence is
missing.

## Usage

From the repository root:

```text
python work/tools/translation_intent_audit.py --project-root .
```

Restrict to TT1B and show the first 25 candidates:

```text
python work/tools/translation_intent_audit.py --project-root . --bank TT1B --limit 25
```

Emit machine-readable JSON:

```text
python work/tools/translation_intent_audit.py --project-root . --json
```

The default Markdown output contains the record ID, heuristic score, whether
runtime evidence is required, the reasons it was ranked, and the natural versus
playable English. The Japanese, literal reading, speaker, register, recorded
problem, and nuance-loss text are retained in the JSON form for deeper tooling.

## How to use the queue

For each actionable record:

1. read the exact Japanese rather than translating from an English paraphrase;
2. review the literal meaning and linguistic/cultural notes;
3. review the bank voice/prose audit and cross-bank character/terminology rules;
4. preserve source sentiment and social effect without inventing color;
5. draft the natural English target without a byte-count objective;
6. determine the minimum safe renderer layout;
7. run whole-bank compression/headroom measurement;
8. use the Rust accelerator for deep search when it materially reduces iteration
   time;
9. accept a slightly larger layout or dictionary result when it materially reads
   better and still leaves safe bank headroom;
10. rebuild/playtest before treating any new presentation-control context as
    proven.

Naturally concise source lines should remain concise. The goal is **not longer
text**; the goal is the least distorted English representation of the Japanese
that the ROM can safely support.

## Relationship to the Python-Rust hybrid

The intent audit decides **where editorial attention is valuable**. It does not
call Rust and it does not pack banks.

After an editor chooses a source-grounded target, the existing editorial layout
and compression tools solve the technical problem. The optional Rust optimizer
makes deep deterministic dictionary search fast enough that compression runtime
is less likely to bias the translator toward telegraphic wording. Python remains
the canonical codec and independently verifies every native result, as described
in [`NATIVE_ACCELERATOR.md`](NATIVE_ACCELERATOR.md).
