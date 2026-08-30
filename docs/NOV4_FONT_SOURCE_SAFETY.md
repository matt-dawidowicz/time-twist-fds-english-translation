# NOV4 font-source safety

This note records the source-ownership rule exposed by the post-title repeating-background regression and the current fixed disk-prompt behavior.

## Recovered source ownership

NOV4's apparent eight-byte font-source geometry is not uniformly writable font data. The post-title graphics loader reads a normal 2bpp block from NOV4 file `$203D-$20FC`. Relative to `NOV4_FONT_BASE_OFFSET = $1B7D`, that range aliases eight-byte slots `$98-$AF`. The actual English 1bpp font-source range begins at file `$20FD` / slot `$B0` and ends after slot `$FE` at file `$2375`.

Therefore an active English glyph may use only runtime source slots `$B0-$FE`. Native lookup metadata may still describe other engine values, but those values must not become active English font writes without first recovering and redesigning the overlapping graphics ownership.

The historical failure used extended code 63, whose native lookup tile is `$AC`, as a compact `Side A` suffix. Slot `$AC` lies inside the direct 2bpp source range. The post-title Start-screen nametable fills the background with a runtime tile whose first bitplane comes from that source location, so installing the compact `A` glyph produced the repeated A-shaped background.

The current source intentionally leaves extended codes 45 and 63 inactive. The disk-change labels use ordinary-glyph `Part2` and `SideA`; they do not install private prompt ligatures.

`tests/unit/test_nov4_font_source_safety.py` generalizes the regression guard from one protected tile to the complete recovered source ranges.

## Distribution provenance hazard

A corrected source tree does not guarantee that a GUI patcher is using the corrected BPS files. The Windows patcher historically persisted an advanced `ManifestPath` in `%LOCALAPPDATA%` and auto-loaded that saved manifest on the next startup. If a user upgraded by extracting a new package while an older manifest still existed elsewhere, the new GUI could silently select the older BPS set. That older set contains the retired `$AC` compact-A bytes and reproduces the exact repeated-A Start-screen failure even though the bundled current manifest is correct.

The broken Zenpen signature is NOV4 file `$20DD-$20E4` = `F1 EE EE E0 EE EE EE FF`. A corrected output has NOV4 file `$20DD-$20EC` = sixteen bytes of `FF`.

A follow-up audit found two additional ways old build material could influence packaging even after saved-manifest loading was removed: default BPS lookup could fall back to a `patches` directory under the process working directory, and the public ZIP builder copied every file present in the maintainer `patches/` directory instead of only the patches named by the current manifest.

The `current-main-sync3` distribution therefore treats default mode as a package-identity boundary. Its patcher resolves package data only from its own script/EXE directory, never from the working directory; uses a new settings epoch that ignores pre-isolation settings; never persists manifest or patch paths; keeps the advanced patch-directory hint session-only; rejects legacy manifest schema/API values and legacy role inference; and snaps back to the bundled set whenever Advanced patch options are closed.

Before every default-mode run, the patcher revalidates the exact package generation, source-reference commit, three versioned BPS filenames, each bundled patch SHA-256, each clean Japanese source SHA-256, and each translated target SHA-256. It still checks NOV4 `$20DD-$20EC` before writing Zenpen or four-side output. A mixed, incomplete, stale, or tampered package therefore fails closed rather than silently selecting another build.

Release creation is also whitelist-based: a clean staging directory receives only the three BPS filenames explicitly listed by the current manifest. Release/source-kit validation rejects extra `.bps` files, stale schema/API/generation metadata, restored patch-location persistence, working-directory patch fallback, and checksum mismatches.

Advanced manifests or individual BPS files may still be selected explicitly for the current session, but no external patch state is restored automatically on the next launch.

### Native standalone successor

The `current-main-sync4-native1` public patcher moves the default package-identity boundary entirely inside one native Windows x64 executable. The three approved BPS payloads are linked into `TimeTwistPatcher.exe`; the runtime default path does not load a manifest, adjacent patch directory, current-working-directory patch files, PowerShell state, or settings from an earlier patcher. The native patch core verifies each embedded BPS SHA-256 and BPS CRC before use, verifies the clean Zenpen/Kouhen SHA-256 identities, and rejects any translated result whose complete target SHA-256 differs from the approved current-main target. The public EXE also exposes a checked-by-default `Open output folder after patching finishes` option; this is a UI preference only and cannot redirect patch selection.

## Current disk-retry records

The short disk-set status at NOV2 file `$269A` is byte-aligned. Runtime save-state evidence superseded an earlier bit-3 interpretation. Its complete eight-byte record renders ordinary-glyph `Bad side.`.

The alternate eight-byte side heading at `$26CC` also renders `Bad side.`. The adjacent ten-byte `$26D4` record has room for ordinary `Wrong side.`, followed by `$26DE` `Try again.`. None of these records needs or uses the retired compact `de.` glyph.

These are size-neutral text changes only; they do not alter disk-state branches, requested-side variables, polling loops, or FDS BIOS calls.
