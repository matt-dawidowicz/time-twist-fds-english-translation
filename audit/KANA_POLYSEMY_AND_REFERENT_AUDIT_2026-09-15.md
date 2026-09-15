# Kana Polysemy and Referent Audit — 2026-09-15

## Scope

This targeted pass follows the full 1,299-record adversarial semantic audit. It
focuses on short kana strings whose kanji spelling is suppressed by the source
script and therefore can conceal materially different readings, plus omitted
subjects/referents that can remain grammatical in English while assigning an
action to the wrong participant.

The pass uses the ROM-derived kana as authority. It distinguishes a lexical
possibility from an actual in-game use: a dictionary reading is not promoted to
a menu label or translation unless the surrounding record and gameplay function
support it.

The project’s existing ambiguity inventory was used as the starting set:

- `きく` — 聞く / 聴く / 訊く, and contextually 効く;
- `みる` — 見る / 診る;
- `あう` — 会う / 遭う / 合う, including compounds such as 似合う;
- `かえる` — 帰る / 変える / 替える;
- `とる` — 取る / 撮る / 採る;
- `なおす` — 直す / 治す;
- `かみ` — 神 / 紙 / 髪;
- `はし` — 橋 / 端 / 箸;
- `こえ` — 声, while rejecting substring hits inside unrelated forms; and
- `いえす` — the source-script collision between the loanword/name Jesus and
  English `yes`, which the game deliberately exploits.

Inflected forms and longer compounds were also checked so an exact-token search
would not miss the relevant use.

## Results

### `きく`: fixed gameplay command is **Listen**, not Ask

The kana verb is lexically broad, but the audited fixed-address gameplay command
has no verified use that requires the English menu label **Ask**. The fixed menu
already has `Talk` as a separate interaction, and the observed `きく` targets are
listening/hearing functions (for example, listening to a sermon).

Scenario uses independently confirm that the broader lexeme must remain
context-sensitive:

- `TT6A/g0/r11` — Joseph asks Kashim to hear him out: **listen**;
- `TT6A/g1/r22` — Mary asks Kashim to listen to her: **listen**;
- `T22/g1/r20` — Jeanne heard God’s message: **hear**;
- `TT6A/g1/r23` — Mary heard an angel’s message: **hear**;
- `TT6D/g0/r5` — the girl heard a fortune: **hear**; and
- `TT6C/g2/r22` — `せきにきく やくそう` means a herb **effective** against a
  cough (効く), not ask/listen at all.

No scenario record located by this pass supplies positive evidence for
`訊く` = **ask/inquire**. That sense remains linguistically possible Japanese,
but it is not evidence for an alternate Time Twist menu label.

**Action:** generated terminology should describe `Listen` as the audited fixed
command while retaining a note that the kana lexeme can have other senses in
ordinary/scenario Japanese.

### `みる`: Look/see uses; no medical `診る` command found

The fixed command `みる` is correctly **Look**. Contextual scenario uses found in
this pass are ordinary seeing, looking, watching, or recognizing, including the
previously corrected `TT3B/g1/r22` “we saw something terrible.” The ancient
Greece medical chapter does not provide evidence that the fixed `みる` command
means medical `診る`; treatment is represented separately by the `ちりょう`
(**Treat**) command.

No high-confidence `見る`/`診る` mistranslation was found.

### `あう`: multiple real senses, currently distinguished correctly

This is a genuine in-script polysemy case:

- `TT6A/g1/r19` `よく にあう` is 似合う — **fits / looks good**;
- `TT6A/g0/r18` and the corresponding Mary-side reconciliation use
  `…にあうのがはずかしくて` in the sense of **meet/face someone**.

The reviewed English already distinguishes these senses (“looks good” versus
“too ashamed to face me”). No change is required.

### `かえる`: change sense verified; no return/change collision found

The material use found is `TT6C/g1/r17`, where the Devil says stones could be
changed into bread. The reviewed English **turn these stones into bread** is
correct. Other search hits were longer unrelated forms such as `おかえり`,
`くりかえす`, or `しずまりかえる`, not evidence of a mistaken bare `かえる`.

No correction is required.

### `とる`: Take remains correct

The fixed command is correctly **Take**. Contextual forms include physically
picking up paper and `のみをとる` (pick off fleas). Searches did not reveal a
scenario where the relevant verb should instead be `撮る` (photograph) or `採る`
(gather/select). Substring hits such as `メートル` and grammatical `にとって`
were rejected as false positives.

No correction is required.

### `なおす`: no source-script use found

The form remains in the linguistic ambiguity inventory because `直す` and `治す`
are genuinely distinct Japanese verbs, but this pass found no playable source
record containing the relevant `なおす` token. There is therefore no Time Twist
translation decision to change.

### `かみ`: God, paper, and hair all occur and are contextually correct

The game actually uses the kana ambiguity in several ordinary contexts:

- 神 — God / divine language in the religious and Nativity material;
- 紙 — paper, including the torn-note/prison material; and
- 髪 — hair, e.g. `TT6B/g1/r16`, where Joseph gently strokes Mary’s hair.

The reviewed English preserves those distinctions. The fixed-address label whose
actual gameplay object is paper remains **Paper**; generic workbook linguistic
notes may still mention the other dictionary readings, but must not imply that
the menu object itself is ambiguous at runtime.

No playable-text correction is required.

### `はし`: no standalone homograph case found

Search hits were overwhelmingly substrings of longer unambiguous words, such as
`はしら` (post/pillar), `はしゃいでいる`, and `はしりぬける`. No standalone
playable `はし` was found requiring a bridge/edge/chopsticks choice.

No correction is required.

### `こえ`: voice use correct; substring hits rejected

The clear lexical occurrence `T25/g0/r21` means that nervousness prevents a
voice from coming out, naturally rendered as **too nervous to speak**. Other hits
inside `こえる` / `きこえる` are separate verbs and were not treated as instances
of 声.

No correction is required.

### `いえす`: intentional Yes/Jesus collision is preserved

The prologue fixed choice `いえす` means **Yes**. In the Nativity climax the same
kana sequence represents **Jesus**. The finale deliberately exploits that
collision in the “Yes—Jesus Christ!” reveal. The current reviewed English keeps
the wordplay rather than normalizing the two uses into one reading.

No correction is required.

## Omitted-subject and referent recheck

The targeted pass rechecked the areas that had already produced genuine
subject/object/referent errors in the full semantic audit, including:

- `TT5/g0/r7` — Belle’s son / attacker subject relations;
- `T25/g1/r20` — the men who attacked George and Belle;
- `TT6A/g0/r18` — recognized `あいつ` (“that guy”), not unknown “someone”;
- `TT6A/g2/r26` — waiting for **someone**, not something; and
- `TT6C/g2/r12` — the Devil’s stated sense of kinship.

No additional high-confidence omitted-subject, object-category, or cross-record
referent error was found in this narrower ambiguity sweep.

## Runtime-only boundary

This pass does not resolve visual/speaker ambiguities that the text cannot settle.
The same four runtime-evidence items remain:

- `TT3A/g2/r7` — exact speaker of the off-screen “Wait, Cougar…” voice;
- `TT3A/g2/r30` — spatial reconstruction of the torn note;
- `TT3B/g0/r24` — Hitler versus the Devil speaking through Hitler; and
- `TT4/g4/r14` — identity of the unlabeled “Wait” voice.

No new runtime-only ambiguity was added by the kana/polysemy sweep.

## Conclusion

The targeted ambiguity pass found **no new high-confidence playable-text
mistranslation**. The substantive cleanup is documentary/tooling consistency:
`きく` should no longer be presented as **ASK / LISTEN** as though those were
interchangeable fixed menu labels. The release menu evidence supports **Listen**.
The broader lexical senses of `きく` remain relevant only when translating an
individual scenario sentence in context.
