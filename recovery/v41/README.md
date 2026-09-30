# Validated release checkpoint bridges

The recovered v38 compiler is intentionally frozen. It reproduces exact v38,
but it cannot directly pack several text/layout revisions introduced during
later playtesting. The maintained release build therefore follows the actual
validated binary lineage with compact source-copy deltas.

The `TTD1` format stores only literal bytes that changed plus copy references
back into the verified source image. Each delta embeds the source and target
SHA-256; the build additionally locks the delta file SHA-256.

## v38 -> late v41

- source SHA-256: `62C5DBC2DE33C484DE9F8C1318FC903642EB08E2B4D5FA8E28384DC699C4C400`
- target SHA-256: `13D4E21D1D4393E5B24A1FAEEBE3FF99CE28E5887B2CC7B54BA1AD664EBC91D1`
- delta SHA-256: `05231C06BE2033E97A922E2D9265E5E8A501DEBB3AC4E79866D198B34F4900A0`

## late v41 -> final v50

- source SHA-256: `13D4E21D1D4393E5B24A1FAEEBE3FF99CE28E5887B2CC7B54BA1AD664EBC91D1`
- target SHA-256: `820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43`
- delta SHA-256: `07F8ED88371DD5E2FC63427490A9BA73DBDC3FA1BFA4037B4D374626E5F689B9`

No complete ROM image is stored here.
