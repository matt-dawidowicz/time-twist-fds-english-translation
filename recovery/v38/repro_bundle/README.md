# Recovered v38 reproducibility bundle

This directory preserves the **minimal exact dependency set** observed while executing the recovered `build_v38.py` from `Time-Twist-v38-Gypsy-Amulet.zip`.

No FDS/ROM image is stored here. The private v25 baseline must be supplied locally.

The payload files are gzip-compressed and base64-encoded only because the GitHub connector used for recovery accepts text content. `restore.py` reconstructs the original files and verifies every recovered file against `manifest.json`.

To verify the recovered checkpoint:

```bash
python recovery/v38/repro_bundle/verify_v38.py \
  --baseline /path/to/Time-Twist-v25-DETERMINISTIC-ENGLISH-SAFE-ENCODING-CANDIDATE.fds
```

For the recovered approved candidate, the required output is:

```
62c5dbc2de33c484de9f8c1318fc903642eb08e2b4d5fa8e28384dc699c4c400
```

The recovery session independently executed the original recovered builder and obtained a **262000-byte, byte-for-byte identical** v38 image with that hash.
