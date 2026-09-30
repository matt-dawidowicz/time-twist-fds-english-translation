from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import hashlib
import os
from pathlib import Path
import sys

VERSION = "1.0"
ZENPEN_SOURCE_SHA256 = "B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916"
KOUHEN_SOURCE_SHA256 = "F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A"
ZENPEN_TARGET_SHA256 = "426AADCE09FDC55EF0B4E3A41EA276B7B3C24EEC4CCBA979E52388F1A456B85F"
KOUHEN_TARGET_SHA256 = "81483F8A76A88BCD069EA87E3D31E8D598F202112E1B39E464FFE0B2B925E3D3"
FOUR_SIDE_TARGET_SHA256 = "820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43"
ZENPEN_PATCH_SHA256 = "a42ec859f7b28fa61356d6ea2fe650a29c1172129738f1136572ef427df9e255"
KOUHEN_PATCH_SHA256 = "9af9ad6e479c8024427766a1f4c1396ed76d8b33baf919bfa430507ef6f21879"
SOURCE_BYTES = 131_000
FOUR_SIDE_BYTES = 262_000

class PatcherError(RuntimeError):
    pass

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def _resource_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "patches"

def _patch_bytes(kind: str) -> bytes:
    expected = {"zenpen": ZENPEN_PATCH_SHA256, "kouhen": KOUHEN_PATCH_SHA256}[kind]
    parts = sorted(_resource_dir().glob(f"{kind}.bps.gz.b64.part*"))
    if not parts:
        raise PatcherError(f"Missing embedded {kind} patch resources.")
    encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
    try:
        payload = gzip.decompress(base64.b64decode(encoded, validate=True))
    except Exception as exc:
        raise PatcherError(f"Could not decode embedded {kind} patch: {exc}") from exc
    if hashlib.sha256(payload).hexdigest() != expected:
        raise PatcherError(f"Embedded {kind} patch failed SHA-256 verification.")
    return payload

def _bps_number(data: bytes, position: int) -> tuple[int, int]:
    value = 0
    shift = 1
    while True:
        if position >= len(data):
            raise PatcherError("Truncated BPS variable-length integer.")
        byte = data[position]
        position += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, position
        shift <<= 7
        value += shift

def _bps_signed(value: int) -> int:
    return -(value >> 1) if value & 1 else value >> 1

def apply_bps(source: bytes, patch: bytes) -> bytes:
    if patch[:4] != b"BPS1" or len(patch) < 16:
        raise PatcherError("Invalid BPS patch header.")
    if binascii.crc32(patch[:-4]) != int.from_bytes(patch[-4:], "little"):
        raise PatcherError("BPS patch CRC is invalid.")
    position = 4
    source_size, position = _bps_number(patch, position)
    target_size, position = _bps_number(patch, position)
    metadata_size, position = _bps_number(patch, position)
    if source_size != len(source):
        raise PatcherError(
            f"BPS source size mismatch: patch expects {source_size:,} bytes, "
            f"input has {len(source):,}."
        )
    position += metadata_size
    action_end = len(patch) - 12
    output = bytearray()
    source_relative = 0
    target_relative = 0
    while len(output) < target_size:
        if position >= action_end:
            raise PatcherError("BPS action stream ended early.")
        action, position = _bps_number(patch, position)
        mode = action & 3
        length = (action >> 2) + 1
        if mode == 0:
            start = len(output)
            output.extend(source[start:start + length])
        elif mode == 1:
            end = position + length
            if end > action_end:
                raise PatcherError("BPS TargetRead exceeds patch payload.")
            output.extend(patch[position:end])
            position = end
        elif mode == 2:
            delta, position = _bps_number(patch, position)
            source_relative += _bps_signed(delta)
            end = source_relative + length
            if source_relative < 0 or end > len(source):
                raise PatcherError("BPS SourceCopy is out of range.")
            output.extend(source[source_relative:end])
            source_relative = end
        else:
            delta, position = _bps_number(patch, position)
            target_relative += _bps_signed(delta)
            if target_relative < 0:
                raise PatcherError("BPS TargetCopy is out of range.")
            for _ in range(length):
                if target_relative >= len(output):
                    raise PatcherError("BPS TargetCopy references future output.")
                output.append(output[target_relative])
                target_relative += 1
    if len(output) != target_size or position != action_end:
        raise PatcherError("BPS output/action length verification failed.")
    if binascii.crc32(source) != int.from_bytes(patch[-12:-8], "little"):
        raise PatcherError("BPS source CRC does not match this disk image.")
    if binascii.crc32(output) != int.from_bytes(patch[-8:-4], "little"):
        raise PatcherError("Patched output failed the BPS target CRC check.")
    return bytes(output)

def _identify(path: Path) -> tuple[str, bytes]:
    data = path.read_bytes()
    digest = _sha256(data)
    if len(data) != SOURCE_BYTES:
        raise PatcherError(
            f"{path.name}: expected a {SOURCE_BYTES:,}-byte raw two-side FDS image; "
            f"got {len(data):,} bytes."
        )
    if digest == ZENPEN_SOURCE_SHA256:
        return "zenpen", data
    if digest == KOUHEN_SOURCE_SHA256:
        return "kouhen", data
    raise PatcherError(
        f"{path.name}: unsupported source image. SHA-256 is {digest}. "
        "Use clean Japanese retail Zenpen/Kouhen dumps."
    )

def _same_file_or_path(left: Path, right: Path) -> bool:
    """Return True when two paths identify the same file or normalized location."""
    try:
        if left.exists() and right.exists() and os.path.samefile(left, right):
            return True
    except OSError:
        pass
    try:
        left = left.resolve(strict=False)
        right = right.resolve(strict=False)
    except OSError:
        pass
    return os.path.normcase(os.path.abspath(os.fspath(left))) == os.path.normcase(
        os.path.abspath(os.fspath(right))
    )


def _assert_destinations_safe(sources: tuple[Path, ...], destinations: tuple[Path, ...]) -> None:
    """Refuse any output path that aliases one of the selected source images."""
    for destination in destinations:
        for source in sources:
            if _same_file_or_path(destination, source):
                raise PatcherError(
                    f"Refusing to overwrite source image {source}. "
                    f"Choose a different output folder."
                )


def build_outputs(first: Path, second: Path, output_dir: Path, *, two_disk: bool, four_side: bool) -> list[Path]:
    if not two_disk and not four_side:
        raise PatcherError("Select at least one output layout.")
    identified: dict[str, bytes] = {}
    for path in (first, second):
        kind, data = _identify(path)
        if kind in identified:
            raise PatcherError(f"Both selected files identify as {kind.title()}.")
        identified[kind] = data
    if {"zenpen", "kouhen"} - identified.keys():
        raise PatcherError("Both Zenpen and Kouhen retail images are required.")

    z = output_dir / f"Time Twist - English Translation v{VERSION} - Zenpen.fds"
    k = output_dir / f"Time Twist - English Translation v{VERSION} - Kouhen.fds"
    f = output_dir / f"Time Twist - English Translation v{VERSION}.fds"
    destinations = tuple(([z, k] if two_disk else []) + ([f] if four_side else []))
    _assert_destinations_safe((first, second), destinations)

    zenpen = apply_bps(identified["zenpen"], _patch_bytes("zenpen"))
    kouhen = apply_bps(identified["kouhen"], _patch_bytes("kouhen"))
    if _sha256(zenpen) != ZENPEN_TARGET_SHA256:
        raise PatcherError("Translated Zenpen failed final SHA-256 verification.")
    if _sha256(kouhen) != KOUHEN_TARGET_SHA256:
        raise PatcherError("Translated Kouhen failed final SHA-256 verification.")
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if two_disk:
        z.write_bytes(zenpen)
        k.write_bytes(kouhen)
        written.extend([z, k])
    if four_side:
        combined = zenpen + kouhen
        if len(combined) != FOUR_SIDE_BYTES or _sha256(combined) != FOUR_SIDE_TARGET_SHA256:
            raise PatcherError("Combined four-side output failed final verification.")
        f.write_bytes(combined)
        written.append(f)
    return written

def _run_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build Time Twist English Translation v1.0 from clean Japanese retail FDS images.")
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("-o", "--output-dir", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--two-disk-only", action="store_true")
    mode.add_argument("--four-side-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        written = build_outputs(
            args.first, args.second, args.output_dir,
            two_disk=not args.four_side_only,
            four_side=not args.two_disk_only,
        )
    except (OSError, PatcherError) as exc:
        parser.exit(2, f"error: {exc}\n")
    for path in written:
        print(f"Created: {path}")
    print("All outputs verified.")
    return 0

def _run_gui() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    root = tk.Tk()
    root.title(f"Time Twist English Patcher v{VERSION}")
    root.resizable(False, False)
    first = tk.StringVar()
    second = tk.StringVar()
    output = tk.StringVar(value=str(Path.home() / "Desktop"))
    two_disk = tk.BooleanVar(value=True)
    four_side = tk.BooleanVar(value=True)
    status = tk.StringVar(value="Select the clean Japanese Zenpen and Kouhen FDS images.")
    frame = ttk.Frame(root, padding=16)
    frame.grid()
    ttk.Label(frame, text="Time Twist English Translation v1.0", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
    def browse_file(var: tk.StringVar) -> None:
        value = filedialog.askopenfilename(filetypes=[("Famicom Disk System images", "*.fds"), ("All files", "*.*")])
        if value:
            var.set(value)
    def browse_dir() -> None:
        value = filedialog.askdirectory()
        if value:
            output.set(value)
    for row, (label, var) in enumerate((("Retail disk 1", first), ("Retail disk 2", second)), start=1):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(frame, textvariable=var, width=62).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(frame, text="Browse...", command=lambda v=var: browse_file(v)).grid(row=row, column=2, padx=(8, 0), pady=4)
    ttk.Label(frame, text="Output folder").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
    ttk.Entry(frame, textvariable=output, width=62).grid(row=3, column=1, sticky="ew", pady=4)
    ttk.Button(frame, text="Browse...", command=browse_dir).grid(row=3, column=2, padx=(8, 0), pady=4)
    ttk.Checkbutton(frame, text="Create original two-disk layout (Zenpen + Kouhen)", variable=two_disk).grid(row=4, column=1, sticky="w", pady=(10, 2))
    ttk.Checkbutton(frame, text="Create combined four-side FDS image", variable=four_side).grid(row=5, column=1, sticky="w", pady=2)
    progress = ttk.Progressbar(frame, mode="indeterminate", length=300)
    progress.grid(row=6, column=1, sticky="w", pady=(12, 4))
    ttk.Label(frame, textvariable=status, wraplength=500).grid(row=7, column=0, columnspan=3, sticky="w", pady=(4, 10))
    def build() -> None:
        if not first.get() or not second.get() or not output.get():
            messagebox.showerror("Missing input", "Select both retail FDS images and an output folder.")
            return
        progress.start(8)
        status.set("Validating retail images and building translation...")
        root.update_idletasks()
        try:
            written = build_outputs(Path(first.get()), Path(second.get()), Path(output.get()), two_disk=two_disk.get(), four_side=four_side.get())
        except (OSError, PatcherError) as exc:
            progress.stop()
            status.set("Build failed.")
            messagebox.showerror("Time Twist patcher", str(exc))
            return
        progress.stop()
        status.set("Complete. All outputs passed SHA-256 verification.")
        messagebox.showinfo("Time Twist patcher", "Translation complete.\n\n" + "\n".join(path.name for path in written) + "\n\nAll outputs verified.")
    ttk.Button(frame, text="Build Translation", command=build).grid(row=8, column=1, sticky="w", pady=(4, 0))
    root.mainloop()
    return 0

def main() -> int:
    if len(sys.argv) > 1:
        return _run_cli(sys.argv[1:])
    return _run_gui()

if __name__ == "__main__":
    raise SystemExit(main())
