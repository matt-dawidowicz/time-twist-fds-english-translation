# Confirmed v83 checkpoint

This checkpoint preserves the user's confirmed v83 build, including the
translation, consistency, action-response, and pronoun fixes developed after
the Simon-corrected public release. The current walkthrough is
[`docs/WALKTHROUGH.txt`](../../docs/WALKTHROUGH.txt).

The normal candidate builder now finishes with the v83 delta. The historical
v38 compiler and earlier deltas remain immutable. All 1,305 dialogue records
are decoded from the result and compared with `work/translations/*.json`;
all 721 menu labels are compared with `menus.json`. A later source edit must
be rebuilt and reviewed before this checkpoint can accept it. There is no
silent second English source.

## Reproduce from an existing public release

Install the project, then run:

```sh
python work/tools/rebuild_v83_checkpoint.py public-four-side.fds build/v83.fds
```

The input must be the exact headerless, four-side, Simon-corrected release.
Unknown inputs are rejected. The delta stores source-copy commands and changed
literals, not a complete ROM. No ROMs, extracted banks, or save states are
included in this repository.

| Artifact | SHA-256 |
| --- | --- |
| Input release | `39587318BC6CFD9BE3FE454372E7B483FA3DA81E884324C6D7BD84B8C435B9F5` |
| Decoded TTD1 delta | `833FABDD349A7064FE984A7C5F228DB719F41785A0CB75FAA3220EB75ECEDBFF` |
| v83 output | `4BBCCB13033B39570B3FE3EB64FBEBA4A9BD4C5C73248852F22665E4A3A9E17A` |

Both images are 262,000 bytes. The source lock retains the unchanged private
v25 seed identity; only public inputs were refreshed during this integration.
No release target is promoted here. The downloadable v1.0 Windows patcher and
BPS assets remain the previously published release, pending a separate release
refresh.

## Changes recovered

- Standardized Info fields: Time, Place, Name, Occupation; both Kashim entries
  use Nazareth. France's heading and character-specific continuation preserve
  native row ownership.
- Separated empty Use, Take, Hold, and Eat responses without globally replacing
  dialogue exclamations. Added five action records and one Belle record.
- Standardized item acquisition, Amulet terminology, spell/name wording,
  Glassmaker, Isabel, Devil, command capitalization, Cellar, Jail, Mansion,
  Shack, and Mare where appropriate to the scene.
- Preserved approved clarity changes, quiz wording and fruit choices,
  the POW escape directions, the soil/pebble distinction, and speaker labels.
- Changed the France crowd response to plural and gave unconscious Belle a
  female response while preserving George's male response.
- Updated the complete walkthrough, including Info availability, the France
  passage and mill, chapter quizzes, Meyer alternatives, and the Nazareth,
  desert, stable, and Nativity event prerequisites.

There are 107 changed existing dialogue records and six added records relative
to the previous canonical maps. The Git diff is the exact record-level audit.
`history/` contains inherited review notes, not active translation inputs.
Bank sizes/layouts also include earlier confirmed post-v50 changes; the
checkpoint preserves those bytes rather than repacking them with the old
compiler. The source-locked manifest supplies exact dictionary counts instead
of inferring them from padding, which is unsafe for the current TT1B layout.
The older incremental builder retains runtime guards and is not certified
for arbitrary editing of v83; use this exact checkpoint reproduction path.

## Belle routing evidence

**VERIFIED:** TT5 loads at `$A200`. The existing `TT5/g0/r9` response,
"He's unconscious.", is shared by George's Look prompt at `$A349`, Belle's
Look prompt at `$A350`, and the Talk fallback at `$A387`. Only Belle's operand
at `$A351` changes from `$0A` to `$81`, selecting new record `TT5/g4/r0`.

The group-pointer table moves from `$BC5D` to verified zero-filled space at
`$BAFD`; the added text starts at `$BB05`. Existing group pointers are copied
unchanged, and a fourth pointer is appended. This v82-to-v83 change alters
22 TT5 bytes, with no bank expansion or menu/dictionary/graphics changes.
The native branch at `$A33E` reaches Belle's path at `$A34B`; native lookup
and rendering return "She's unconscious." for Belle and retain "He's
unconscious." at George's Look and the Talk fallback.

`belle-verification.json` records that native 6502 check, repeated during integration. It is not a
claim of full emulator or PPU testing. The user confirmed the issues fixed
before requesting this repository update. All 315 public unit tests pass with zero skips; quick checks, lint, typing,
docstrings, and package builds pass. A fresh byte-exact reconstruction
and complete source decode were performed during integration; the full
private fixture suite and v25-to-v83 build still require the private overlay.

## Layout policy

The confirmed ROM is preserved without editorial reflow. Nine exact text
hashes retain reviewed compact/structural wrapping, and Joan's speech retains
its existing comma pause. These narrow exceptions do not disable width,
buffer, row ownership, or strict wrapping checks for subsequent edits.
