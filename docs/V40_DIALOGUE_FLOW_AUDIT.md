# v40 dialogue-flow audit

The gate overwrite was part of a broader continuation problem. A text record
can reset the renderer cursor while retaining rows from the previous record.
English often occupies more rows than Japanese, so both missing entry controls
and mechanically copied source controls can overwrite readable text.

## Scope and results

| Check | Result |
| --- | --- |
| Scenario records across 13 banks | 1,299 decoded and rendered |
| Source-marked continuation records | 63 registered and paired with reviewed predecessors |
| Retained-buffer overlaps in v39 paired native tests | 54 of 63 |
| Retained-buffer overlaps in v40 paired native tests | 0 of 63 |
| Layout revisions beyond v39 | 76 records; 77 relative to v38 |
| Visible English wording changes | None after control/whitespace normalization |
| Independent fixed-menu decoding | 721 labels match expected text |

Final four-side image SHA-256:
`18baaecda65e2cf2406672da3c803669c3e5bafbe43af1c5b06216c93dfd2f03`.

## Corrections

Continuation entry rows now account for the predecessor's English footprint.
One retained row needs one advance; two need two advances; fuller boxes scroll
before appending. Once the lower rows fill, continuations use native scrolling
instead of writing over earlier text. Ordinary prose is greedily word-wrapped.
Identity-card fields receive separate rows, and the instruction record's source
trailing scrolls are restored.

Two semantic pause layouts were repaired explicitly: TT6C/g0/r16 preserves the
Joseph, Caspar and Me turns without interrupting "The Devil possessed the baby!";
T22/g1/r20 preserves Joan's source-aligned turn boundaries without a wait after
"Put". Their dramatic timing still needs real-scene playtesting.

The old row validator incorrectly treated consecutive leading advances as
idempotent. Native zero-page $72 line state means two leading CTRL:0 controls
enter byte 96, not byte 48. The canonical validator and a retained-buffer tracer
now model this state. Regressions cover repeated advances, scroll ownership,
lost continuation controls, and unsafe dictionary wait controls.

## Evidence and limits

The native 6502 harness executes the ROM's actual NOV2 decoder and renderer for
all 1,299 records. It resumes wait states and substitutes PPU upload behavior.
For the final compressed ROM, TT1B, TT3A and TT3B were rerun; the remaining ten
banks reused successful results only after byte-for-byte equality checks of
their payloads, headers and NOV2. All 63 pairs were rerun on the final image with
buffer ownership retained across record calls. An independent decoder checked
all records and fixed menus.

A Mesen CE 2.2.1 controlled museum fixture visibly confirms the sky description
and "No time for that now!" coexist without overlap. Cross-bank quiz/card
fixtures did not reproduce valid scene graphics and are excluded from visual
pass claims. Native text-buffer checks cover those records, but do not establish
that every answer menu or scene-specific display is correct.

Predecessors were reviewed using script call sites, source structure and context,
including conditional/shared subroutine cases. The registry covers every record
whose source starts with a control; it is not an exhaustive control-flow proof
of every possible game route or every unmarked record boundary. The 54 failures
are reproducible paired renderer failures, not 54 individually played scenes.

This audit is not a complete playthrough. Full scene state, answer-selection UI,
branch-specific predecessors and pause timing remain runtime review work. The
build stays a playtest candidate. The converted museum save changes only the
loaded scenario bank and is separately reloaded and input-tested with v40.
