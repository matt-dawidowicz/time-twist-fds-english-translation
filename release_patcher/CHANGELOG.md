# v1.1.1 — public patcher compatibility fix

- Accept the standard 131,000-byte No-Intro Kouhen dump (CRC-32 `A7D51BFA`) in the Windows patcher.
- Keep strict source identity checks: only that exact known retail variant receives the alternate BPS source/target CRC allowances.
- Preserve rejection of unknown or modified dumps.

# v1.1 — confirmed v83 build

The public patches now include the fixes from the intervening playtests,
including the final v82 and v83 corrections. They produce the same confirmed
v83 ROM; this packaging update does not change the game again.

- Retain all intervening menu, dialogue-routing, rendering, and quiz fixes,
  including the twelve-month selection fix and the existing Simon fix.
- Standardize Info cards to Time, Place, Name, and Occupation. Both Kashim
  profiles use Nazareth.
- Standardize empty Use, Take, Hold, and Eat responses while keeping unrelated
  dialogue exclamations intact.
- Standardize item acquisition messages, Amulet wording, spell/name wording,
  Isabel, Glassmaker, Devil, and command capitalization.
- Use consistent Cellar, Jail, Mansion, Shack, and Mare labels where they refer
  to the same location or character.
- Incorporate the approved translation and clarity corrections, including
  speaker labels, quiz wording and fruit choices, POW directions, and the
  distinction between digging in soil and finding a pebble.
- v82: change the France crowd reaction to “They watch with bated breath.”
- v83: give unconscious Belle “She's unconscious.” while keeping George's
  “He's unconscious.” and the existing shared Talk fallback intact.
- Include the corrected full walkthrough: Info availability, France's secret
  passage and mill, chapter quizzes, Meyer alternatives, and the Nazareth,
  desert, stable, and Nativity event prerequisites.

Compared with the previous repository source, 107 existing dialogue records
change and six specific responses are added. The output contains 1,305 dialogue
records and 721 menu labels, all checked against the committed source.

The v82-to-v83 upgrade changes only 22 bytes in TT5, without increasing that
bank's size. It does not include the earlier changes because v82 already has
them. The public v1.1 patches include the entire cumulative update.
