# Audio command map

This document completes the low-level correlation of the source-used gameplay VM
audio commands. It deliberately separates **driver identity** from **story-facing
sound names**. A command is given a narrative label only when call-site evidence makes
that label unambiguous.

The machine-readable form is
`work/time_twist/audio_commands.py`.

## Command latches

NOV2 has two audio-write handlers:

- `83 value` writes `$07E3=value` and mirrors the value into zero-page `$D1`;
- `90-93 value` write `$07E0-$07E3` respectively without the mirror.

The recovered roles are:

| Opcode | Latch | Role |
| --- | --- | --- |
| `90` | `$07E0` | resident APU/noise/triangle SFX |
| `91` | `$07E1` | active scene-overlay SFX |
| `92` | `$07E2` | resident pulse-channel SFX sequencer |
| `83/93` | `$07E3` | resident music/FDS-audio selector |

NOV3 `$D7B5` consumes the resident latches every audio tick. If an active scene
overlay has installed a `$DC/$DD` audio callback, that overlay consumes `$07E1`
before NOV3 processes the resident latches.

## `90`: resident latch-0 effects

Reachable retail source uses only `02` and `80`.

| Value | Verified meaning | Native path |
| --- | --- | --- |
| `02` | ten-step **noise sweep** | `$D843`; countdown `$07D5=$0A`, period data from `$D83A`, writes `$400E/$400C/$400F` |
| `80` | **stop/reset resident SFX** | `$D86C`; writes `$4015=$07`, clears `$07E5` |

A third value matters outside the gameplay VM:

| Direct value | Verified meaning | Native path |
| --- | --- | --- |
| `04` | native **typewriter noise click** | NOV2 `$85C5` writes `$07E0=$04`; NOV3 `$D82A` emits a four-tick burst with `$400E=$13`, `$400C=$1D`, `$400F=$18` |

This proves that the typewriter sound and opcode `90` share a resident SFX
latch, but the source-reachable `90` commands do not request the typewriter
effect.

## `92`: resident paired-pulse sequences

NOV3 `$D87E` treats the command as a bit selector. The first set bit chooses an
entry from the selector table at `$D945`; that entry supplies two offsets into
the sequence stream at `$D958`, one for each pulse channel.

All source-used values are now correlated:

| Value | Sequence offsets | Sequence CPU addresses | Verified identity |
| --- | --- | --- | --- |
| `01` | `00 / 0A` | `$D958 / $D962` | resident paired-pulse sequence 1 |
| `02` | `13 / 2E` | `$D96B / $D986` | resident paired-pulse sequence 2 |
| `04` | `49 / 4E` | `$D9A1 / $D9A6` | resident paired-pulse sequence 3 |
| `08` | `52 / 58` | `$D9AA / $D9B0` | resident paired-pulse sequence 4 |
| `80` | `09 / 00` | `$D961 / $D958` | resident alternate/termination pulse sequence |

The names stay mechanical because the exact game-world interpretation depends on
the script call site; the binary identity itself is no longer unknown.

## `83/93`: music/FDS-audio selector

NOV3 `$DA3C` is the music selector. `83` and `93` feed the same `$07E3`
latch; `83` additionally mirrors the command in `$D1` so scene loading can
preserve it.

The selector behavior is global:

| Value | Verified selector behavior |
| --- | --- |
| `01` | group A: play table slot 8 once, then cycle slots 9-12 |
| `02` | group B: cycle slots 13-17 |
| `04` | group C: cycle slots 18-21 |
| `08` | select fixed table slot 3 |
| `10` | select fixed table slot 4 |
| `20` | select fixed table slot 5 |
| `40` | select fixed table slot 6 |
| `80` | stop/clear active music and FDS-audio state |

After selecting a slot, `$DAAC` dereferences the active scene's byte-offset
music table through `$D8/$D9`. The resulting record supplies the sequence
pointer and channel/FDS parameters; `$D9B5` initializes the FDS wavetable.

Therefore a value such as `40` is **not one global song ID**. It means “music
table slot 6,” and the actual composition is defined by the active scene overlay.

Recovered full-overlay music-table bases are:

| Audio owner | Table base |
| --- | ---: |
| TT1B | `$C20C` |
| TT2 | `$C0C4` |
| TT3A | `$C25D` |
| TT4 | `$C126` |
| TT5 | `$C0E8` |
| TT6B | `$C123` |
| TT6C | `$C168` |
| TT6D | `$C11B` |

Partial same-address overlays intentionally inherit high-tail audio data:
TT1A inherits TT1B, T22 inherits TT2, TT3B inherits TT3A, T25 inherits TT5,
and TT6A inherits TT6B.

That scene-specific indirection is why assigning one global title such as
“battle music” to `93 40` would be incorrect.

## `91`: scene-overlay effects

`91` writes `$07E1`. Unlike `90` and `92`, this latch is decoded by the
currently loaded gameplay program, so its bit meanings are deliberately reused.
The recovered fresh-command entry points are:

| Overlay | `01` | `02` | `04` | `08` | `10` | `20` | `40` | stop `80` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TT1B | `$CF23` | `$CED9` | `$CEA6` | `$CF64` | `$CF60` | `$CF91` | `$CF93` | `$CF54` |
| TT2 | `$D0F3` | `$D162` | `$D176` | `$D176` | - | - | - | `$D156` |
| TT3A | `$D079` | `$CFFD` | `$CFD6` | `$D0AC` | `$D07B` | `$D0B0` | `$CFDA` | `$D058` |
| TT4 | `$D310` | `$D2E2` | `$D35F` | - | - | - | - | `$D350` |
| TT5 | `$CC8E` | `$CC24` | `$CC3D` | `$CCCB` | - | - | - | `$CCBF` |
| TT6B | `$BF2A` | `$BE78` | `$BF5A` | - | - | - | - | `$BF1B` |
| TT6C | `$CE12` | `$CD75` | `$CDC5` | `$CE46` | `$CE42` | - | - | `$CE06` |
| TT6D | `$ABC0` | `$AB5D` | `$AC0F` | - | - | - | - | `$ABF6` |

TT3A additionally recognizes `03` as a combined/special command before the
ordinary bit dispatcher and enters `$D071`.

These paths are now fully bound to code addresses and APU state machines.
Many are noise-channel envelopes/sweeps; some overlays also drive both pulse
channels. Story-facing labels should be attached at the individual script call
site rather than to the numeric bit globally.

### POW-camp example

TT3A contains:

```text
$A3C1  91 10
$A3C3  A1 78
$A3C5  91 20
$A3C7  A1 78
$A3C9  18 1A
```

Both `91 10` and `91 20` are therefore scene-overlay effects, distinct from
the native typewriter's `$07E0=$04` path. Runtime A/B testing showed that
removing the `91 20` command does **not** eliminate the reported early typing
sound, so that symptom must not be “fixed” by deleting this scene command.

## Evidence boundary

This pass completes the **selector/driver identity** of all source-used
`$07E0-$07E3` values.

What it does not do is invent soundtrack titles or Foley names that are absent
from the binary. A future clean replay can annotate individual call sites with
human descriptions (“door,” “impact,” etc.) when audiovisual context proves
them. Those annotations would sit on top of this map rather than changing it.
