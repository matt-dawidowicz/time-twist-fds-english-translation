# Time Twist English Translation v1.0

This release patches the Japanese Famicom Disk System version of
*Time Twist: Rekishi no Katasumi de...* into English.

No Japanese or translated FDS image is distributed. You must provide clean copies
of both original Japanese disks.

## Choose your patching method

There are two supported ways to install the translation.

### Option 1: Windows patcher

Run `TimeTwistEnglishPatcher.exe`.

Select your two clean Japanese FDS images. Their filenames and selection order do
not matter because the patcher identifies Zenpen and Kouhen by SHA-256.

You can then choose either or both output layouts:

- **Original two-disk layout**
  - `Time Twist - English Translation v1.0 - Zenpen.fds`
  - `Time Twist - English Translation v1.0 - Kouhen.fds`
- **Combined four-side layout**
  - `Time Twist - English Translation v1.0.fds`

The patcher verifies the source images, applies the translation, verifies the
finished output hashes, and refuses any output path that would overwrite or alias
one of the selected source images.

### Option 2: Manual BPS patches

If you prefer to use your own BPS patching program, use the two standalone patches
included with the release:

- `Time-Twist-English-v1.0-Zenpen.bps`
- `Time-Twist-English-v1.0-Kouhen.bps`

Apply them separately:

1. Apply `Time-Twist-English-v1.0-Zenpen.bps` to the clean Japanese Zenpen image.
2. Apply `Time-Twist-English-v1.0-Kouhen.bps` to the clean Japanese Kouhen image.

This produces the translated original two-disk layout.

The Windows patcher is the easiest way to create the combined four-side image. If
you create it manually, concatenate the complete translated Zenpen image first and
the complete translated Kouhen image second. Do not insert an additional header
between them.

The two BPS files are available both as standalone release files and inside the
Windows ZIP under `BPS-Patches/`.

## Supported source images

Both source files are raw/headerless two-side FDS images of exactly 131,000 bytes.

| Disk | SHA-256 |
| --- | --- |
| Zenpen | `B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916` |
| Kouhen | `F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A` |

Modified dumps and unsupported variants are rejected by the Windows patcher.

## Certified translated outputs

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| `Time Twist - English Translation v1.0 - Zenpen.fds` | 131,000 | `426AADCE09FDC55EF0B4E3A41EA276B7B3C24EEC4CCBA979E52388F1A456B85F` |
| `Time Twist - English Translation v1.0 - Kouhen.fds` | 131,000 | `81483F8A76A88BCD069EA87E3D31E8D598F202112E1B39E464FFE0B2B925E3D3` |
| `Time Twist - English Translation v1.0.fds` | 262,000 | `820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43` |

The four-side image contains:

1. Zenpen Side A
2. Zenpen Side B
3. Kouhen Side A
4. Kouhen Side B

The combined output is byte-identical to the final v50 playtest baseline. Public
release numbering starts at v1.0.

## Manual BPS checksums

| Patch | SHA-256 |
| --- | --- |
| `Time-Twist-English-v1.0-Zenpen.bps` | `A42EC859F7B28FA61356D6EA2FE650A29C1172129738F1136572EF427DF9E255` |
| `Time-Twist-English-v1.0-Kouhen.bps` | `9AF9AD6E479C8024427766A1F4C1396ED76D8B33BAF919BFA430507EF6F21879` |

The Windows ZIP also includes `SHA256SUMS.txt`.

## Repository-only Python / command-line workflow

The Python commands below are for developers using a full checkout of this GitHub
repository. The Windows release ZIP does not include the Python source tree or its
embedded patch-resource chunks.

Python 3.11 or newer is sufficient.

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

## Repository resource format

The repository stores the BPS payloads as gzip-compressed, Base64-encoded text
chunks. `TimeTwistPatcher.py` reconstructs and SHA-256 verifies those payloads
before use. The Windows executable embeds the same verified patch data.

## License

The patcher software is distributed under the MIT License. See `LICENSE` in the
release ZIP and repository.
