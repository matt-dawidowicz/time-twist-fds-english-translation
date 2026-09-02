# TT3B voice and prose pilot

This pass continues the source-first voice/prose revision through the second half of the July 1944 Germany chapter.

## Editorial direction

- Preserve exact Japanese meaning and control-code order.
- Keep the protagonist's contemporary internal voice distinct from Cougar.
- Keep Schmidt terse, controlled, and professional rather than turning him into a flamboyant resistance hero.
- Keep Simon educated and precise, with stronger emotion only where the Japanese breaks his composure.
- Keep German military/Gestapo dialogue clipped and direct, with no phonetic German accents.
- Keep Hitler theatrical and authoritarian, then visibly frightened when the situation turns against him.
- Keep the Devil sardonic and authoritative.
- Do not euphemize source-explicit wartime or supernatural violence; do not invent harsher material absent from the Japanese.

## Source-grounded restorations and corrections

- `TT3B/g0/r2`: restores the officer's formal arrest report and replaces Schmidt's game-like `My turn` with a clipped handoff meaning that he is taking responsibility from here.
- `TT3B/g0/r3`: restores the uncertainty in `you da` with `Looks unused now.`
- `TT3B/g0/r5`: restores the source's specific trigger detail rather than merely saying the woman grips a gun.
- `TT3B/g0/r7`: restores the causal force of `dakara koso`; Simon's moral conclusion now follows explicitly from his praise of Einstein.
- `TT3B/g0/r13`: restores `ki no sei ka`; the charm only seems to make the protagonist feel braver.
- `TT3B/g0/r14`: restores the protagonist's uncertainty about the charm inscription while keeping the rust-obscured text concrete.
- `TT3B/g0/r28`: restores the source's description of a traitor's fate as wretched.
- `TT3B/g1/r7`: removes the unsupported implication that the flash burns Hitler's eyes; the source says the light strikes/pierces his eyes.
- `TT3B/g1/r10`: restores the protagonist's written stammer.
- `TT3B/g1/r15`: restores Schmidt's in-progress physical sensation rather than implying the tearing is already complete.
- `TT3B/g1/r21`: restores Simon's certainty that the supernatural event was real.
- `TT3B/g1/r23`: restores that the pact ends next year, making Hitler's `Next year?!` reaction causally intelligible.
- `TT3B/g1/r24`: returns the closing internal narration to the protagonist's contemporary, panicked voice.

## Deliberate constraint choice

`TT3B/g0/r22` remains `Drop dead, Hitler!` without an English `Schmidt:` prefix. The Japanese explicitly identifies Schmidt, but the full speaker label plus the established passphrase cannot fit safely. Preserving the exact recurring password/reveal phrase is more important than adding a redundant label that the scene context already supplies.

## Exact-width boundary correction

Runtime/visual review exposed a weakness in the original validation assumption: although the renderer is documented as 24 tiles wide, wording that occupies all 24 cells can look clipped or force punctuation to be omitted. The first TT3B candidate therefore passed the mechanical width check while still producing visibly poor boundary cases such as `Simon: No... It was real`.

The TT3B pass now uses a stricter practical rule: no control-delimited segment may exceed 23 visible characters. All 26 exact-24-character segments in the first TT3B candidate were rewritten with one cell of headroom. Examples include:

- `Simon: No... It was real` -> `Simon: No. It was real.`
- `Schmidt: You're safe now` -> `Schmidt: You're safe.`
- `All three are badly hurt` -> `They're all badly hurt.`
- `Me: Guide those who roam` -> `Me: Guide wanderers...`
- `the rift between worlds.` -> `a dimensional rift.`

This is a TT3B runtime-safety correction, not yet a claim that every bank in the project must globally use 23 columns. The broader renderer rule should be changed only after equivalent runtime evidence is checked in other banks.

## Validation

The final TT3B candidate contains 58 scenario records and changes 33 of them relative to the pre-pass branch version.

Local structural validation found:

- exact control-event sequence preserved for every changed record;
- no control-delimited English segment longer than 23 visible characters;
- maximum segment width: 23 characters;
- no non-ASCII characters introduced;
- revised TT3B visible text is 67 characters shorter overall than the pre-pass branch version.

The raw-character reduction is useful headroom but is not proof of packed fit. TT3B is a tight dictionary-compressed bank, so the canonical compression/release-build fit gate remains required before release approval.
