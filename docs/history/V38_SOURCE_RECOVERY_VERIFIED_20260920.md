# v38 source recovery verification — 2026-09-20

The archived build package `Time-Twist-v38-Gypsy-Amulet.zip` was recovered from the prior ChatGPT project and inspected directly.

## Recovered build contents

The archive contains the actual deterministic source/build state used for v38, including:

- `source/build_v34.py`
- `source/build_v35.py`
- `source/build_v36.py`
- `source/build_v37.py`
- `source/build_v38.py`
- `source/codec.py`
- `source/cpu6502.py`
- `source/support.py`
- `source/verify_v34.py` through `verify_v37.py`
- native-render tests and regression suites
- `source/data/determinate_english.json`
- `source/data/layouts.json`
- versioned dictionary JSON files
- menu override JSON files
- region/input-probe metadata
- the exact v25 safe-encoding baseline FDS
- v38 build and verification reports
- the approved v38 FDS image

## Deterministic reproduction

The recovered builder was executed against the baseline included in the package:

```
python build_v38.py \
  --baseline ../baseline/Time-Twist-v25-DETERMINISTIC-ENGLISH-SAFE-ENCODING-CANDIDATE.fds \
  --output-dir <clean-output-dir>
```

The builder reported:

```
PASS 1299 62c5dbc2de33c484de9f8c1318fc903642eb08e2b4d5fa8e28384dc699c4c400
```

The rebuilt image:

- size: 262000 bytes
- SHA-256: `62c5dbc2de33c484de9f8c1318fc903642eb08e2b4d5fa8e28384dc699c4c400`
- byte-for-byte comparison with the archived approved v38 image: **IDENTICAL**

This proves that v38 is reproducible from the recovered source/build package.

## Recovery status

The previous concern that v38 might only survive as an opaque binary is resolved. The complete build lineage and source data survive in the recovered archive. No reverse-engineering or approximate reconstruction is required.

The next repository-maintenance step is to migrate or preserve the recovered source package in the canonical GitHub source structure without changing its behavior, with this exact binary hash as the regression gate.
