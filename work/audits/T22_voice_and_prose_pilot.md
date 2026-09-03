# T22 voice and prose pilot

> **Editorial-compression supersession — 2026-09-03.** The exact-Japanese,
> semantic, speaker, register, dialect, sentiment, characterization, and voice
> findings in this pilot remain review evidence. Any statement below that uses
> visible-character reduction as a reason to shorten otherwise better English,
> or treats source-exact controls as an absolute prohibition on an explicitly
> audited English-only `CTRL:0` presentation break, reflects the earlier fit
> strategy and is superseded by `docs/ENGLISH_LAYOUT.md`,
> `docs/COMPRESSION_OPTIMIZER.md`, and `docs/NATIVE_ACCELERATOR.md`. Natural
> source-faithful English is now chosen first; layout and verified compression
> are used to fit it into the unchanged ROM footprint.

This pass continues the source-first voice/prose revision through T22: the prison confrontation, the Bishop's pact, the hidden passage, Jeanne's execution scene, the Baron's intervention, and Jeanne's first revelation.

## Editorial rules

- Exact Japanese remains authoritative; external fan-translation wording is never copied.
- Preserve the exact source control-event sequence.
- Keep every control-delimited English segment at or below 24 visible columns.
- The protagonist keeps his 1995 internal voice even inside Pierre's body.
- The Baron is educated and decisive in public, but markedly tender with Isabelle.
- The jailer remains restrained and institutional rather than being given generic medieval slang.
- The Bishop is ceremonially self-important, smug, and increasingly panicked; no faux Shakespeare is added to his ordinary dialogue.
- The written pact may remain more elevated than ordinary dialogue because the Japanese itself uses deliberately archaic `ware/nanji` diction.
- Jeanne is still a frightened sixteen-year-old in ordinary speech. Her register rises only in the source's explicit divine revelation.
- Crowd speech should turn clipped and explosive when the Bishop is exposed.

## Notable source-grounded changes

- `T22/g0/r13`: restores the Baron's omitted `kawaisou ni` as `Poor Isabelle...`; `I swear I'll save you.` keeps his tenderness direct rather than ceremonially ornate.
- `T22/g0/r6`: `I shun clergy.` becomes `I shun churchmen.` to sound less like an abstract policy statement while retaining the Baron's refusal to speak with church people.
- `T22/g0/r11`: `It's his hand!` becomes `His own hand!`, making the handwriting sense clearer in period-appropriate English; the Baron answers `Right!` rather than the flatter `Yes!`.
- `T22/g0/r14`: `You can't leave.` becomes `You must remain.` to preserve the jailer's controlled institutional register.
- `T22/g1/r6`: the Bishop's execution planning becomes `Best to make an example.` This restores the public-warning function of `miseshime` and suits his smug cadence.
- `T22/g1/r10`: `You deceived us!` becomes `How dare you...!`, closer to `yokumo ima made...` and more natural as the crowd turns on the Bishop.
- `T22/g1/r14`: `Slowly tormenting her...` becomes `Torture her bit by bit?`, restoring the interrogative force of `...tsumori ka` in the protagonist's modern internal voice.
- `T22/g1/r16`: `He watches the scaffold.` becomes `Breath held, he watches.`, restoring `iki o nonde` rather than dropping the onlooker's physical reaction.
- `T22/g1/r20`: Jeanne's prophetic close changes `a new road will open...` to `a new road shall open...`; the elevated `shall` is limited to the explicit revelation rather than spread across ordinary medieval dialogue.

## Cross-section consistency changes

Several repeated or closely parallel observations now follow the TT2 prose decisions:

- `Everyone looks worn out.` -> `They all look exhausted.`
- `Woman: I am no witch!` -> `Woman: I'm not a witch!`
- `Too risky to do here.` -> `Not here. Too risky.`
- `Unconscious.` -> `He's out cold.`
- `Nobody here.` -> `No one here.`
- `It is too heavy to lift.` -> `Too heavy to lift.`

Other interaction text is tightened only when that improves the continuing protagonist voice: `A secret passage opened!`, `I've seen this before...`, `The fire isn't lit yet.`, and similar compact observations.

## Lines deliberately left alone

- The pact itself remains substantially unchanged. Its existing `O Devil`, `I kneel`, and `I pledge` language already distinguishes a deliberately archaic written document from spoken dialogue without overusing pseudo-Shakespearean English.
- The Baron's public accusations (`Is that not so?!`, `That girl is no witch!`) already fit his educated, decisive register.
- The Bishop's `Devil-baptized, depraved` proclamation is compressed but source-faithful and already at the 24-column limit.
- Jeanne's ordinary rescue dialogue remains plain; only the actual revelation receives a more elevated cadence.

## Validation

T22 contains 58 scenario records. This pass changes 27 of them.

Static validation of the final candidate found:

- exact control-event sequence preserved for every record;
- no changed control-delimited segment exceeds 24 visible columns;
- maximum changed-segment width: 24 columns;
- no unsupported English-font characters introduced;
- revised visible text is 7 characters shorter overall than the prior T22 branch version.

T22 previously had limited packed-bank headroom. The visible-character reduction is useful but does not prove dictionary-compressed fit. The canonical compressor/release-build test remains a release gate.
