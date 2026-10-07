# Time Twist English Translation v1.1 — v83 update

This release includes all confirmed fixes through the v83 playtest build.
The Windows patcher and the manual patches produce exactly the same ROM.
No game images or save states are included.

## Starting from the original Japanese disks

Run `TimeTwistEnglishPatcher.exe`, select the clean Japanese Zenpen and Kouhen
FDS images in either order, and choose an output folder. The two patches are
built into the executable. It verifies both inputs and every output and never
modifies the original images. Existing output files require confirmation.

You can create the original two-disk layout, one combined four-side image, or
both. Output filenames include `English Translation v1.1`.

For another BPS patcher, use:

- `Time-Twist-English-v1.1-Zenpen.bps` on clean Japanese Zenpen.
- `Time-Twist-English-v1.1-Kouhen.bps` on clean Japanese Kouhen.

Both inputs must be raw/headerless, 131,000-byte images. The Kouhen path also
accepts the standard No-Intro raw retail dump (CRC-32 `A7D51BFA`, MD5
`134F65BD93A5E5C0ABAB3E560FF146A8`, SHA-1
`E0747E6BA6111FAD733C832E6CA7C0172F4C056E`). This is a known byte-compatible
retail variant whose FDS metadata/padding differs from the release-locked Kouhen
source. The patcher verifies that exact dump identity before permitting its
variant BPS CRCs; it does not broadly disable checksum protection. Do not apply
these full translation patches to an already translated image.

## Updating an existing translated image

The optional upgrade patches in `BPS-Patches` require these specific inputs:

| Patch | Required input |
| --- | --- |
| `Time-Twist-v1.0-Simon-to-v1.1-four-side.bps` | The Simon-corrected v1.0 combined four-side image |
| `Time-Twist-v82-to-v83-four-side.bps` | The last v82 combined four-side playtest image |
| `Time-Twist-v82-to-v83-Kouhen.bps` | The last v82 two-side Kouhen playtest image |

For the two-disk v82 layout, only Kouhen changes: Zenpen is already identical
to v83. A v83 image already contains this update and needs no upgrade patch.
Apply one matching upgrade with a BPS patcher; do not apply them in sequence.
If your translated image differs from the supported input, use the full
translation patches with your clean Japanese originals instead.

These patches update ROM files, not emulator save states. An old save state
can restore earlier code/text; use a matching migrated state or restart from
the updated image. Preserve your existing saves and original disks.

## Changes and walkthrough

`CHANGELOG.md` lists the cumulative translation and bug fixes.
`WALKTHROUGH.txt` includes the corrected routes, quizzes, alternatives, and
Nativity prerequisites. `PATCH-INPUTS.json` gives the exact source, target,
and patch identities for all five patches. `SHA256SUMS.txt` covers the package.

## Image SHA-256 values

| Image | SHA-256 |
| --- | --- |
| Japanese Zenpen input | `B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916` |
| Japanese Kouhen input | `F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A` |
| v1.1 Zenpen output | `0784FE632DB3DB424E963CCA840982942F689A4385EFE9BDE3E7940F325599F7` |
| v1.1 Kouhen output | `8327F1130563C3C6E87CBE67DA227429BAAC59E596B49D67BE1018FD3A2E398F` |
| v1.1 combined output | `4BBCCB13033B39570B3FE3EB64FBEBA4A9BD4C5C73248852F22665E4A3A9E17A` |

Each translated part is 131,000 bytes; the combined image is 262,000 bytes,
exactly Zenpen followed by Kouhen.

## Command line

```powershell
TimeTwistEnglishPatcher.exe Zenpen.fds Kouhen.fds -o translated
```

Use `--two-disk-only` or `--four-side-only` to select one layout. `--force`
allows replacement of existing outputs. `--version` reports 1.1.

## Building the Windows package

```powershell
./release_patcher/build_windows.ps1
```

The build verifies embedded resources in the frozen executable, creates all
five standalone BPS patches, includes the changelog and walkthrough, and writes
`dist/Time-Twist-English-v1.1-Windows.zip`. The source-only patch checks run with
`python release_patcher/test_public_patcher.py`.

This unofficial fan translation distributes project code and patch deltas only.
Users must supply their own legally obtained game images.
