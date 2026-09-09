# Production font and typography contract

**Status:** Font-engine work for the production localization branch. The production retranslation itself remains review-only and is not yet imported into `work/translations`.

## Vertical metrics

The dialogue font uses an explicit 8-row cell rather than treating every glyph as an unrelated 5x7 bitmap.

- Capitals `A-Z`: ink rows 0-6.
- Digits `0-9`: ink rows 0-6, matching the capital-height box.
- Ordinary x-height lowercase: baseline at row 6.
- Lowercase ascenders (`b d f h k l t`): cap-height top with the same row-6 baseline.
- True descenders (`g p q y`): x-height body remains aligned with other lowercase and the tail extends into row 7.
- `j`: dot remains at the top while the hook extends into row 7.

This removes the previous visual unevenness where descender letters had to be squeezed upward because the old pattern table never used the eighth tile row.

`work/tests/test_production_font_metrics.py` locks these metrics so later glyph edits cannot silently move letters or numbers up or down.

## Production punctuation glyphs

The patch-facing English map now has dedicated in-game glyphs for:

- `…` ellipsis — extended code 61 / tile `$B4`, restoring the native ellipsis slot.
- `—` em dash — extended code 57 / tile `$FC`, repurposing the Japanese display-slash slot because production English does not use that slash mark.
- `:` colon — extended code 45 / tile `$FA`, a recovered safe font slot that was previously inactive in English.
- `é` — extended code 44 / tile `$F9`, retained for words and names such as `consommé` and `Pépé`.
- Straight apostrophe and quotation-mark glyphs remain the physical 8x8 forms. Curly review typography (`‘ ’ “ ”`) is accepted by the encoder and aliases to those established tiles; at this resolution separate curly quote tiles would consume scarce codes without a meaningful visual gain.
- En dash `–` normalizes to the em-dash tile.

Hyphen and em dash have distinct pixel forms: the hyphen is shorter, while the em dash spans the full five-pixel glyph width.

## Source-ownership safety

Extended code 63 remains inactive. Its native lookup tile is `$AC`, and NOV4 source slot `$AC` overlaps title graphics. The production font therefore does **not** write an English glyph there.

All active extended English glyphs resolve to recovered font-source tiles in `$B0-$FE`. The existing title-background safety rule remains in force.

## Deliberately unsupported characters

A slash `/` is not part of production prose and is intentionally rejected by the English encoder after code 57 became the em dash. This is preferable to rendering an incorrect glyph silently.

The Civil War money puzzle should use forms such as `120 dollars` in the game-safe adaptation rather than consuming the unsafe code-63/title-overlap slot merely to add `$`. If a future approved script genuinely requires another unique symbol, it should receive a separately recovered safe runtime mapping rather than reusing `$AC`.

## Visual review

`work/preview_production_font.py` renders a specimen containing the full uppercase alphabet, full lowercase alphabet, all digits, descenders, `é`, ellipsis, em dash, and quote/apostrophe cases with baseline and descender guides. It should be regenerated whenever a glyph bitmap changes.
