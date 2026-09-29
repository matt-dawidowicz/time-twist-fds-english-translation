# Time Twist English Patcher v1.0

This directory contains the public patcher for the completed English translation of
*Time Twist: Rekishi no Katasumi de...*.

The patcher does not contain either Japanese retail disk image or any patched FDS
image. Users supply their own clean Zenpen and Kouhen dumps. The program identifies
the disks by SHA-256, applies embedded BPS data, verifies every translated output,
and can create either or both supported layouts.

## Supported source images

Both images are raw/headerless two-side FDS images of exactly 131,000 bytes.

| Disk | SHA-256 |
| --- | --- |
| Zenpen | `B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916` |
| Kouhen | `F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A` |

Filenames and selection order do not matter. The patcher identifies each image from
its hash and rejects modified or unsupported dumps.

## Outputs

By default the patcher creates both layouts:

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| `Time Twist - English Translation v1.0 - Zenpen.fds` | 131,000 | `426AADCE09FDC55EF0B4E3A41EA276B7B3C24EEC4CCBA979E52388F1A456B85F` |
| `Time Twist - English Translation v1.0 - Kouhen.fds` | 131,000 | `81483F8A76A88BCD069EA87E3D31E8D598F202112E1B39E464FFE0B2B925E3D3` |
| `Time Twist - English Translation v1.0.fds` | 262,000 | `820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43` |

The combined image is a raw/headerless four-side FDS image in this order:

1. Zenpen Side A
2. Zenpen Side B
3. Kouhen Side A
4. Kouhen Side B

It is exactly the final v50 behavioral baseline that completed the full playtest.
The public patch release is versioned independently as v1.0.

## Windows

The GitHub Actions workflow builds `TimeTwistEnglishPatcher.exe` with PyInstaller.
Run it, browse to the two clean Japanese FDS images, choose an output folder, select
one or both output layouts, and click **Build Translation**.

The program never writes to the supplied source images.

## Python / command line

Python 3.11 or newer is sufficient; the patcher otherwise uses only the standard
library.

```powershell
python release_patcher/TimeTwistPatcher.py Zenpen.fds Kouhen.fds -o patched
```

Create only the original two-disk layout:

```powershell
python release_patcher/TimeTwistPatcher.py Zenpen.fds Kouhen.fds -o patched --two-disk-only
```

Create only the combined four-side layout:

```powershell
python release_patcher/TimeTwistPatcher.py Zenpen.fds Kouhen.fds -o patched --four-side-only
```

## Advanced BPS files

The release packaging script reconstructs the two standalone BPS files from the
compressed repository resources and places them under `advanced/`. They are intended
for users who prefer a traditional BPS workflow.

Each BPS applies to one clean 131,000-byte retail image. The combined four-side image
is then simply the translated Zenpen output followed by the translated Kouhen output.
This avoids requiring users to manufacture a concatenated source image before applying
a third patch.

## Repository resource format

The BPS payloads are gzip-compressed, Base64-encoded, and split into text chunks so
the public repository remains source-only. `TimeTwistPatcher.py` reconstructs and
hash-checks the payloads before use. The Windows build embeds those same chunks.
