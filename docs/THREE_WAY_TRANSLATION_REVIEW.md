# Three-way translation review

This workflow aligns the Japanese source, this project's playable English,
and a separately supplied competitor patch by stable scenario coordinates. It
is an editorial diagnostic, not a patch-merging path. Japanese remains the
source of truth, and no competitor wording enters the playable maps without an
independent source-based review.

## 2026-08-29 input audit

The audit that established this workflow used these exact local inputs:

| Role | Bytes | SHA-256 |
|---|---:|---|
| Japanese Zenpen | 131,000 | `B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916` |
| Japanese Kouhen | 131,000 | `F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A` |
| Current English Zenpen | 131,000 | `3E82BCD2FDF1E4AFF67FF90D97A03554CCF06A794A8F854C482DD86470F52E89` |
| Current English Kouhen | 131,000 | `CB66E4FD8C64CF4E1E9C68E34A4D4DDBEB263F8414A9D86D2E77325A82E266C5` |
| Competitor-labeled Zenpen output | 250,706 | `027CA6A4945C0BCB3C934750947F3A95B6B2A3188CA7FCE348BA0F4F5E05CE78` |
| Competitor-labeled Kouhen output | 250,706 | `DF9BD6D6C8FC4FB1B12531DD0CE628126215D0091DF980A12C183F10B644A9F2` |
| Competitor IPS | 166,492 | `DD0B73CE16B8C1749CF238F8D728F91729FF00A9A0D7299131E4F7C1D247E62B` |

The two Japanese inputs are the locked project baselines. The two current
English inputs matched the candidate Zenpen and Kouhen outputs byte for byte.
Both competitor-labeled `.fds` files are malformed standalone images:

- each is 250,706 bytes, not a multiple of the 65,500-byte FDS side size;
- each contains ordinary side headers only at offsets 0 and 65,500;
- their 119,706-byte appended suffixes are identical;
- 79,599 changed offsets occur in both prefixes, and both outputs contain the
  same byte at every one of those offsets.

Those facts identify the same four-side IPS being applied separately to each
two-side half. Do not parse either oversized output as an independent game.

The IPS README expects a four-side source with SHA-1
`FF01B76C8BA84C6222FA043EFCBF82F1501B903B`; the supplied locked Japanese
concatenation is `5577D5B6183F3C59FCADCD8F5CC7998473C83D2D`. The generator therefore tracks
which reconstructed bytes came explicitly from IPS records. It accepts the
comparison only because every byte consumed by all 1,299 competitor scenario
records and their reachable dictionaries was explicitly written by that IPS.
Two banks (`TT3A` and `TT5`) retain one source-derived pointer byte; that byte
helps locate an already fully patch-written stream and is reported separately.

## Generate the private corpus

Run from the repository root, substituting paths to legally obtained inputs:

```powershell
python work/generate_three_way_comparison.py `
  --japanese-zenpen <clean-zenpen.fds> `
  --japanese-kouhen <clean-kouhen.fds> `
  --current-zenpen <current-english-zenpen.fds> `
  --current-kouhen <current-english-kouhen.fds> `
  --competitor-zenpen <competitor-zenpen-output.fds> `
  --competitor-kouhen <competitor-kouhen-output.fds> `
  --competitor-ips <competitor-four-side.ips>
```

The default JSON and TSV outputs are written under
`work/runtime_capture/three_way_review/`. That directory is ignored because
the files contain decoded retail-source and competitor-translation text. Do
not commit, publish, or attach those generated files to a public release.

The generator fails closed unless:

- all four Japanese/current images parse as ordinary two-side FDS images;
- every expected scenario file exists on its recovered half and side;
- Japanese, current English, and competitor English all decode to the same
  1,299 `(bank, group, record)` coordinates;
- Japanese ROM text equals the public recovered Japanese evidence;
- current ROM text equals every authoritative `work/translations/*.json` map;
- the current control sequence equals Japanese at every coordinate;
- every decoded competitor text/dictionary byte is explicitly IPS-written.

## Initial queue, not a quality verdict

The audited pre-revision images produced:

- 1,299 structurally aligned scenario records;
- 52 exact current/competitor wording matches and 1,247 wording differences;
- 0 current/Japanese control-sequence mismatches;
- 644 competitor/Japanese control-sequence differences, consistent with the
  competitor's different page geometry;
- 255 high-priority mechanical leads and 992 plain wording comparisons.

The 255-record queue is deliberately conservative. It flags a current line
only for a large length gap that could indicate omitted meaning, a likely
fragment, or missing terminal punctuation. A longer competitor line is not
automatically more faithful, and its altered control layout must never be
copied into this project's fixed overlay without independent runtime proof.

## Review and revision procedure

Review one bank at a time. For each coordinate:

1. translate the exact Japanese independently, checking surrounding records;
2. compare the current and competitor English only after forming that reading;
3. record whether the issue is meaning, nuance, voice, grammar, consistency,
   naturalness, control sensitivity, or merely different style;
4. prefer dictionary/order optimization before shortening good English;
5. preserve the Japanese control values and 24-column renderer rules;
6. rebuild and run the full unit and private integration gates;
7. playtest the exact newly hashed candidate in context.

Automated alignment, compression fit, and source guards do not prove scene
progression, page timing, line clearing, disk transitions, or translation
quality. Keep runtime status separate from static review completion.
