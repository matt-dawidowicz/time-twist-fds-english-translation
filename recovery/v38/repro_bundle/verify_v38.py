#!/usr/bin/env python3
"""Restore and reproduce the canonical v38 Time Twist candidate."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", required=True, type=Path)
    p.add_argument("--candidate", type=Path)
    args = p.parse_args()

    if not args.baseline.is_file():
        raise SystemExit(f"missing private baseline: {args.baseline}")

    with tempfile.TemporaryDirectory(prefix="time-twist-v38-repro-") as td:
        root = Path(td)
        source = root / "source"
        subprocess.run([sys.executable, str(HERE / "restore.py"), str(source)], check=True)
        baseline_dir = root / "baseline"
        baseline_dir.mkdir()
        baseline_copy = baseline_dir / MANIFEST["baseline_filename"]
        shutil.copyfile(args.baseline, baseline_copy)
        output = root / "output"
        subprocess.run(
            [sys.executable, str(source / "build_v38.py"),
             "--baseline", str(baseline_copy),
             "--output-dir", str(output)],
            cwd=source,
            check=True,
        )
        built = output / "Time-Twist-v38-PROTECTIVE-AMULET-CANDIDATE.fds"
        if not built.is_file():
            candidates = sorted(output.glob("*.fds"))
            if len(candidates) != 1:
                raise SystemExit(f"could not identify v38 output in {output}")
            built = candidates[0]
        got_size = built.stat().st_size
        got_hash = sha256(built)
        if got_size != MANIFEST["expected_rom_size"]:
            raise SystemExit(f"ROM size mismatch: {got_size}")
        if got_hash != MANIFEST["expected_rom_sha256"]:
            raise SystemExit(f"ROM SHA-256 mismatch: {got_hash}")
        if args.candidate:
            if built.read_bytes() != args.candidate.read_bytes():
                raise SystemExit("rebuilt ROM is not byte-identical to candidate")
        print(f"PASS v38 {got_hash}")

if __name__ == "__main__":
    main()
