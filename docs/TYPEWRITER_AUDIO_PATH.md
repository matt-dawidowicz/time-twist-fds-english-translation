# Typewriter and POW-scene audio path

This note records the September 22, 2026 recovery of the dialogue typewriter SFX
path and the separate TT3A POW-camp scene-local SFX path. It exists to prevent future
work from conflating two different audio sources.

Evidence labels follow the repository convention:

- **VERIFIED** - exact bytes/control flow establish the behavior.
- **OBSERVED** - repeatable emulator/video behavior not yet fully correlated to every
  underlying runtime state.
- **INFERRED** - useful interpretation not yet safe as a generic patch rule.

## 1. Native typewriter SFX is tied to glyph upload

The previous issue-level explanation that the typewriter SFX begins at text-state entry
is obsolete.

The staged text uploader begins at NOV2 `$83D9`. It prepares one visible cell at a
time in `$63-$68`. Transparent dialogue-tail cells (`$AC`) are skipped before the
PPU-upload phase.

The NMI-side uploader begins at NOV2 `$8469`. For a visible staged cell it performs:

```text
$846D  STA $2006   ; PPU address high
$8472  STA $2006   ; PPU address low
$8477  STA $2007   ; first glyph tile
$847E  JSR $85C5   ; typewriter SFX command
...
$8490  STA $2007   ; paired glyph tile when present
```

NOV2 `$85C5` is:

```text
A9 04       LDA #$04
8D E0 07    STA $07E0
60          RTS
```

Therefore the native typewriter command is issued from the glyph PPU-upload path, not
from entry into the text renderer.

### NMI ordering

The main NMI path calls the text PPU uploader before the resident audio tick:

```text
$647D  JSR $8469   ; upload staged text cell / issue typewriter command
$6480  JSR $84AE   ; scroll worker
...
$64D8  JSR $D7B5   ; resident NOV3 audio tick
```

Thus command `$04` written by `$85C5` is available to the audio driver later in
the same NMI in which the text tile is written.

This rules out a generic "SFX starts when the text state begins" explanation for
first-glyph timing.

## 2. Resident meaning of `$07E0=$04`

NOV3 `$D804` consumes `$07E0` as the resident APU/noise-SFX command latch.
Bit `$04` reaches the branch beginning at `$D82A`.

The command initializes a short noise-channel effect and reaches the common noise
register writer with:

```text
$400E = $13
$400C = $1D
$400F = $18
```

It also initializes the local effect/countdown state with command value `$04`.
This is the native dialogue typewriter click path.

## 3. TT3A has a separate POW-camp noise effect

The POW-camp sequence around display record 26 contains this verified script:

```text
$A3BD  20 08
$A3BF  61 0B
$A3C1  91 10
$A3C3  A1 78
$A3C5  91 20
$A3C7  A1 78
$A3C9  18 1A
```

`91 value` is a VM audio-latch command. It writes the supplied value to
`$07E1`, not to the typewriter latch `$07E0`.

The final `18 1A` displays scenario record 26. In the current English map that is
`TT3A/g0/r26`.

### TT3A `$07E1=$20` consumer

TT3A contains its own `$07E1` audio consumer around `$D003`. The latch is shifted
as a bitfield. Value `$20` selects the bit-5 path and reaches the effect setup at
`$D0B0`.

That path initializes a distinct scene-local noise effect, including state at
`$07E6/$07D8/$07DA/$07D9`, and drives the NES noise registers through the TT3A
overlay routine. It is not the typewriter routine at `$85C5`.

Value `$10` immediately earlier in the same script selects another neighboring
scene-local noise effect.

Therefore this POW interaction intentionally schedules two scene SFX, separated by
`A1 $78` delays, before the text record is dispatched.

## 4. Consequence for the reported POW timing symptom

The v44 capture showed a residual sound before the first visible glyph after the broad
blank-space SFX problem had been reduced. Static recovery now establishes two
independent candidate sources in this scene:

1. the true typewriter click, `$07E0=$04`, issued at glyph upload;
2. the scripted POW interaction effect, `$07E1=$20`, issued before record 26.

The recovered v45 diagnostic already isolates the second source by changing only:

```text
TT3A $A3C5: 91 20 -> 91 00
```

No NOV2 renderer, scheduler, text, menu, graphics, or typewriter bytes are changed in
that diagnostic.

**Runtime comparison of that diagnostic remains the decisive test** for whether the
residual pre-text sound in the POW interaction is the scripted `$07E1=$20` effect.

Do not introduce a global typewriter delay unless a clean runtime trace proves that a
remaining mismatch is actually produced by `$85C5`.

## 5. Debugger watchpoints

For future Mesen tracing:

```text
write $07E0  -> resident/typewriter noise command
write $07E1  -> scene-overlay SFX command
PC $847E     -> typewriter call site after first tile write
PC $85C5     -> typewriter command helper
PC $D7B5     -> resident audio tick
PC $D003...  -> TT3A scene-audio dispatcher
PC $A3C1     -> POW $07E1=$10 command
PC $A3C5     -> POW $07E1=$20 command
PC $A3C9     -> record-26 text dispatch
```

Capture the PC, `$07E0/$07E1`, `$69`, `$63-$68`, `$2006/$2007` writes,
and the first noise-register writes. That is sufficient to distinguish scripted scene
audio from dialogue typing without modifying the global scheduler.
