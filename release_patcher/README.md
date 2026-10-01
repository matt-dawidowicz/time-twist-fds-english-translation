# Time Twist English Translation v1.0 — Public Patcher

This folder contains the public Windows patcher and the source assets used to
build it.

The public release is designed for users who own clean Japanese retail FDS
images of both halves of *Time Twist: Rekishi no Katasumi de...*:

- Zenpen (Part 1)
- Kouhen (Part 2)

## Recommended method: Windows executable

Run:

`TimeTwistEnglishPatcher.exe`

The executable contains both required BPS patches internally. You do **not**
need to put BPS files next to the program.

Select the two clean retail FDS images. Their order does not matter; the patcher
identifies Zenpen and Kouhen by SHA-256 before it changes anything.

Choose one or both output layouts:

- two translated two-side FDS files:
  - `Time Twist - English Translation v1.0 - Zenpen.fds`
  - `Time Twist - English Translation v1.0 - Kouhen.fds`
- one combined four-side image:
  - `Time Twist - English Translation v1.0.fds`

The program patches both disks in memory, verifies the translated hashes, then
writes the selected outputs. It never modifies the two source images.

Existing translated output files are not silently overwritten. The GUI asks
before replacement; the CLI requires `--force`.

## Manual BPS patches

For users who prefer another BPS patcher, the release also includes:

- `Time-Twist-English-v1.0-Zenpen.bps`
- `Time-Twist-English-v1.0-Kouhen.bps`

These are the same two BPS payloads embedded inside the Windows executable.

Apply each patch to its matching clean Japanese retail image.

## Required source images

The patcher accepts raw/headerless 131,000-byte FDS images only.

### Zenpen

SHA-256:

`B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916`

### Kouhen

SHA-256:

`F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A`

If either source image differs, the executable stops before creating output.

## Verified translated outputs

### Zenpen

- Size: 131,000 bytes
- SHA-256:
  `1CC094577F05182960258A8AFC264ED804A5589B61D8DA6E945718073C1C073A`

### Kouhen

- Size: 131,000 bytes
- SHA-256:
  `81483F8A76A88BCD069EA87E3D31E8D598F202112E1B39E464FFE0B2B925E3D3`

### Combined four-side image

- Size: 262,000 bytes
- SHA-256:
  `39587318BC6CFD9BE3FE454372E7B483FA3DA81E884324C6D7BD84B8C435B9F5`

The combined image is exactly translated Zenpen followed by translated Kouhen
in the original four-side order.

This corrected release preserves the completed v50 playtest baseline, fixes the
TT1A fortune-teller blood-type menu handoff, and removes the unnecessary extra
dialogue scroll that caused stale gutter text in the Dr. Simon / Time Belt scene.
Kouhen is byte-identical to the v1.0 baseline.

## Command-line use

The same executable can be used from a terminal:

```powershell
TimeTwistEnglishPatcher.exe Zenpen.fds Kouhen.fds -o translated
```

Input order does not matter.

By default it creates both the two-disk layout and the combined four-side image.

Two-disk output only:

```powershell
TimeTwistEnglishPatcher.exe Zenpen.fds Kouhen.fds -o translated --two-disk-only
```

Combined image only:

```powershell
TimeTwistEnglishPatcher.exe Zenpen.fds Kouhen.fds -o translated --four-side-only
```

Replace existing translated output files:

```powershell
TimeTwistEnglishPatcher.exe Zenpen.fds Kouhen.fds -o translated --force
```

## Release package layout

The Windows ZIP contains:

```text
TimeTwistEnglishPatcher.exe
README.md
LICENSE
SHA256SUMS.txt
BPS-Patches/
  Time-Twist-English-v1.0-Zenpen.bps
  Time-Twist-English-v1.0-Kouhen.bps
```

The two BPS files are also published individually beside the ZIP for users who
do not want the executable.

## Integrity model

The release uses several independent checks:

1. each input FDS image must match the exact expected SHA-256;
2. each embedded BPS payload must match its own SHA-256;
3. BPS patch CRC, source CRC, and target CRC are validated;
4. translated Zenpen and Kouhen must match their exact final SHA-256 values;
5. the optional combined four-side image must match the corrected final SHA-256;
6. writes occur only after the requested outputs have already been patched and
   verified in memory;
7. source/output path collisions are rejected.

The executable therefore fails closed on unsupported dumps, damaged embedded
patch data, patching errors, or unexpected final output.

## Building the Windows release

From PowerShell:

```powershell
./release_patcher/build_windows.ps1
```

The build uses PyInstaller `--onefile --windowed` and embeds the patch resource
directory into `TimeTwistEnglishPatcher.exe`.

The build then smoke-tests the frozen executable with `--version`, reconstructs
the standalone BPS files, generates `SHA256SUMS.txt`, and creates:

`dist/Time-Twist-English-v1.0-Windows.zip`

No original or fully patched FDS image is included in the public package.

## Legal notice

This is an unofficial fan translation. The release contains original project
code and binary patch deltas only. Users must provide their own legally obtained
original game images.