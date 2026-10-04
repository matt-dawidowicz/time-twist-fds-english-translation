# v61 TT3A control-free dictionary repair

## Root cause

The v59 TT3A overlay still carried an older entropy dictionary that predated the
current compressor rule treating presentation controls as hard dictionary
boundaries. A dictionary expansion could therefore execute `CTRL:0` while the
decoder was inside a nested dictionary expansion. The Old Man quiz repeatedly
hit that condition and could resume from corrupted nested decoder state, which
explains unrelated text such as “An open tunnel…!” appearing after a quiz
question.

The one-record v60 workaround targeted `TT3A/g1/r30` and is intentionally not
part of this branch. This branch starts from v59 source commit
`014478c3bb776280a2aadf967c101a1447bea594`.

## Corrected v59 audit

The compiled v59 TT3A overlay contains **152** scenario records, with group
topology `32 + 32 + 32 + 32 + 24`. The earlier “160” count was incorrect.

The compiled v59 dictionary contains **109** entries. Fully expanding the
dictionary shows presentation controls in exactly three entries:

- D105 — begins `CTRL:0, CTRL:0`
- D106 — begins `CTRL:0`
- D109 — ends in `CTRL:0`

There is no D110 in the compiled v59 TT3A dictionary. The earlier four-entry
audit was therefore off by one/stale. These three unsafe expansions are
referenced by 17 scenario records. The Old Man quiz records
`g4/r2`, `g4/r4`, `g4/r5`, `g4/r6`, and `g4/r7` are in that set.

## Structural rebuild

v61 was rebuilt directly from the v59 four-side image, not from the temporary
v60 workaround.

The migration:

1. decodes all 152 TT3A scenario records to dictionary-expanded semantic tokens;
2. decodes all 95 TT3A fixed-menu records with the same old dictionary;
3. runs the current entropy optimizer, whose candidate search cannot cross a
   presentation-control token;
4. evaluates the production pruning variants and repacks both the menu and the
   scenario streams against the fresh dictionary;
5. preserves the frozen TT3A suffix and the NOV3 boundary;
6. re-decodes the result and proves semantic identity.

Selected v61 layout:

- dictionary entries: 106
- unsafe expanded dictionary entries: 0
- semantic TT3A payload end: 13,633 bytes
- FDS TT3A file size: 13,737 bytes (padded to retain all later file offsets)
- NOV3 headroom: 116 bytes
- split stream: group 0 after record 30
- changed FDS payloads: TT3A only

All 152 scenario records and all 95 fixed-menu records decode semantically
identical to v59. The five Old Man quiz questions now begin with literal
top-level `CTRL:0, CTRL:0` tokens.

## Candidate hash

`Time-Twist-v61-TT3A-control-free-dictionary-candidate.fds`

SHA-256:

`9588EAF5E3CE151C97DB9C1CA5ADC3135D5611067E618CC344EAE46C96C50D48`

The Kouhen half is byte-identical to v59.
