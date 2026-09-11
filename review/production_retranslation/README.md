# Production retranslation review index

**Current status:** The canonical `release-build` locks and imports the registered JSON in this directory as the reviewed production-English layer. `work/translations/*.json` remains the certified base/control-topology layer; it is not overwritten by these review files.

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

## Integration status

The editorial pass is integrated without copying proposals into the base
translation maps. `production_translation.py` starts from the base maps, applies
these registered review records, then applies any intentionally present
`work/production_overrides/*.json` as the final layer. It regenerates
renderer-safe English row/scroll geometry, and the canonical entropy release
builder encodes that materialized result.

## Editorial gate

Future wording changes still require editorial review before the source lock is intentionally refreshed. Engineering changes must preserve the approved words and the recovered semantic-control topology unless a new runtime behavior is explicitly reviewed.
