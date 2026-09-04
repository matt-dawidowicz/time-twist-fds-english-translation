# Time Twist bilingual script comparison

This package is designed for a second-pass localization review, not merely a proof that English fits in the ROM.

## Files

- `Time Twist Japanese-English script comparison.html` — searchable human review interface.
- `Time Twist Japanese-English script comparison.tsv` — Excel/LibreOffice-ready UTF-8 worksheet with blank `proposed_retranslation` and `reviewer_notes` columns.
- `Time Twist Japanese-English script comparison.json` — structured corpus for scripts, LLM analysis, or version-controlled edits.

## Coverage

- 1,299 scenario records across all 13 banks: TT1A 35, TT1B 137, TT2 169, T22 58, TT3A 152, TT3B 58, TT4 183, TT5 123, T25 76, TT6A 100, TT6B 94, TT6C 106, TT6D 8.
- 756 fixed-address command, object, quiz, personality-menu, and engine-interface records.
- 3 recovered graphics-text entries for the title and Kouhen direct-boot warning.
- 416 entries carry at least one detected voice, dialect, honorific, or register marker.
- Review queue: 50 high, 1,779 medium, 229 low.
- Control-sequence mismatches: 1 (NOV2/wait).

## How to interpret the Japanese

The game intentionally renders nearly all story text in hiragana. That erases distinctions normally carried by kanji and katakana. For example, `かみ` can mean 神 (god), 紙 (paper), or 髪 (hair), while foreign names such as `しもん` would normally be written シモン. The `normalized_japanese_aid` and `orthography_kanji_katakana` columns expose such candidates without rewriting the source.

Dialect tags are conservative. Forms such as `じゃ`, `のう`, and `わし` often create a fictional elderly voice rather than proving a geographic dialect. `やで` is a much stronger Kansai signal; sentence-final `ばい` may suggest Kyushu/Hakata speech. Pronouns and honorifics are called out because English frequently drops status, age, gender presentation, intimacy, or hostility that Japanese encodes directly.

## Recommended review order

1. Filter `review_priority` to `high` and review in scene order, with screenshots or a live playthrough for speaker identity.
2. Decide voice rules per recurring speaker before rewriting isolated lines.
3. Treat every slash-separated kanji candidate as unresolved until context selects it.
4. Keep `{CTRL:n}` sequences in the same order unless the renderer behavior is deliberately changed.
5. Draft natural English first, then fit it into the bank and fixed-record constraints. Do not allow a tiny menu slot to dictate the unconstrained literary translation.
6. Store the unconstrained preferred translation in `proposed_retranslation`; derive a separate ROM-safe rendering afterward.

## Known boundary

The staff roll is graphics/program data rather than part of the decoded packed-text corpus. Personal names in the credits have not been optically transcribed into this worksheet. The title and direct-boot warning are included because their source wording is already recovered and verified.
