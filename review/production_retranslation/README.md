# Production retranslation review index

**Branch:** `retranslation/production-pass-20260908`

**Critical status:** This directory is editorial review material only. It is not imported by `release-build`, and no playable `work/translations/*.json` source has been replaced by these proposals.

## Coverage

All **1,299 scenario records** have now received the production editorial pass.

| Bank | Scenario records | Review artifact | Review form |
| --- | ---: | --- | --- |
| TT1A | 35 | `TT1A_proposal.json`, `TT1A_editorial_notes.md` | Full unconstrained proposal + annotated rationale |
| TT1B | 137 | `TT1B_proposal.json`, `TT1B_editorial_notes.md` | Full unconstrained proposal + annotated rationale |
| TT2 | 169 | `TT2_changes.json` | Full-bank review; listed records change, omitted records are deliberate keeps |
| T22 | 58 | `T22_changes.json` | Full-bank review; change-only |
| TT3A | 152 | `TT3A_changes.json` | Full-bank review; change-only |
| TT3B | 58 | `TT3B_changes.json` | Full-bank review; change-only |
| TT4 | 183 | `TT4_changes.json` | Full-bank review; change-only |
| TT5 | 123 | `TT5_changes.json` | Full-bank review; change-only |
| T25 | 76 | `T25_changes.json` | Full-bank review; change-only |
| TT6A | 100 | `TT6A_changes.json` | Full-bank review; change-only |
| TT6B | 94 | `TT6B_changes.json` | Full-bank review; change-only |
| TT6C | 106 | `TT6C_changes.json` | Full-bank review; change-only |
| TT6D | 8 | `TT6D_proposal.json` | Full unconstrained proposal |
| **Total** | **1,299** | | |

`PRODUCTION_LOCALIZATION_STANDARD.md` defines the accuracy, voice, censorship, punctuation, terminology, and historical-register rules used across the pass.

## Why two artifact forms?

TT1A and TT1B were the most visibly compromised runtime material and establish the production voice, so they receive complete replacement proposals. TT6D is short enough to present completely.

For the larger historical banks, the previous authenticity audit already made many lines semantically correct and naturally usable. Rewriting those lines for the sake of generating churn would make the localization less disciplined. Their `*_changes.json` files therefore list only records whose production English should change. Every record in those banks was reviewed; omission is an explicit editorial decision to retain the current source-audited wording.

## What has not happened yet

- No review proposal has been copied into `work/translations`.
- No control tags have been re-authored around the new prose.
- No 24-column or special-screen wrapping has been imposed on the review English.
- No dictionary/compression search has been run against the new prose.
- No text has been shortened to satisfy the current ROM.
- No candidate FDS has been built from these proposals.

Those are deliberately separate engineering steps. The English should be approved on editorial merit before the game is changed to accommodate it.

## Next editorial gate

Review the proposals for voice, terminology, and tone. Once approved, create a machine-readable approved-English layer and then solve control layout, punctuation glyph coverage, compression, relocation, and renderer requirements without silently degrading the approved prose.
