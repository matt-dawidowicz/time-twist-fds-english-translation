# Codebase baseline: 13 October 2026

**Status:** permanent historical engineering record. The original source code
must remain recoverable even when its current module is optimized, renamed,
split, or deprecated. This document describes the **pre-cleanup** tree, not
the current implementation. For active recommendations, use
[Code health and performance](../CODE_HEALTH_AND_PERFORMANCE.md).

## Immutable Git reference

- Repository: `matt-dawidowicz/time-twist-fds-english-translation`
- Audited branch: `main`
- Pre-cleanup commit: **`27b67b82e08f90046ad4cf9df595f0800de3cd6f`**
- Git tree: `27b67b82e08f90046ad4cf9df595f0800de3cd6f`
- Snapshot: 359 tracked blobs, 33,123,952 bytes of Git blob content.
- Binary artifacts are counted here but are **not** original game ROMs.

All original modules, exact byte contents, docstrings, and algorithms are
recoverable from that Git commit. For example:

```sh
git show 27b67b82e08f90046ad4cf9df595f0800de3cd6f:work/time_twist/incremental_build.py
git show 27b67b82e08f90046ad4cf9df595f0800de3cd6f:work/time_twist/compression.py
git diff 27b67b82e08f90046ad4cf9df595f0800de3cd6f..HEAD -- work/time_twist
```

Do not replace Git history with a duplicated snapshot of source code inside
`docs/`. Such duplication would create a second stale implementation.
Instead, record the immutable commit, exact file/blob identities, behavior
invariants, and preserved pre-change reference algorithms in tests.

## What is in the snapshot?

| Directory | Tracked files | Blob bytes |
| --- | ---: | ---: |
| `release/` | 6 | 22,284,498 |
| `work/title_assets/` | 8 | 4,389,292 |
| `work/source_records/` | 13 | 3,607,171 |
| `work/time_twist/` | 53 | 691,468 |
| `docs/` | 44 | 426,734 |
| `work/tests/` | 50 | 306,195 |
| `work/tools/` | 16 | 124,111 |
| `work/integration_tests/` | 6 | 58,310 |
| `work/translations/` | 13 | 113,449 |

The largest artifacts are the intentional public `release/` EXE/ZIP and
standalone patches (22+ MB together). This is separate from core Python source
and should not be mistaken for dead code. The historical recovery bundles,
source records, and translation maps are provenance evidence, not expendable
build debris.

### Baseline active Python package: exact Git blob identities

The complete `work/time_twist` Python source tree contained 53
modules (including the package initializer), totaling
691,468 UTF-8 bytes.
Each Git blob SHA identifies the **pre-cleanup** content precisely.

| Module | Blob bytes | Git blob SHA |
| --- | ---: | --- |
| `__init__.py` | 149 | `391aee1c6c05f891557fca930db76bed7b90735f` |
| `audio_commands.py` | 4,975 | `667a703887d2693306e9ae424bfb1f954a3e0207` |
| `capacity.py` | 2,235 | `810bbfca12d888ad9eaa39d66831d8aa6ddd226b` |
| `charmap.py` | 3,319 | `926df3059028e91efead3e29b52ee5a7dddf1dfe` |
| `checkpoint_delta.py` | 2,398 | `290bbab7b6c4e343c5eddf5e1ec267e8da4ea302` |
| `cli_commands.py` | 22,379 | `45a95ab3db2bf809b71202d24139a5c1408d17e6` |
| `cli_parser.py` | 14,416 | `b35f9a25eff6612614f5bc996f7527a5fcfc8549` |
| `cli.py` | 806 | `fcfc64aa3231e9190ce00b9898eadbf3da4dd66a` |
| `compression.py` | 28,504 | `ff8469efbde0ef8c26a18d7afd3d1f5e27f8f494` |
| `continuation_contracts.py` | 2,349 | `bbdc65993f6b1f7da20ef07fef63016faf4e3f5b` |
| `dialogue_flow.py` | 3,362 | `fb4cab453910c9daf88ff9eee755042e6127dba8` |
| `english.py` | 9,921 | `4cadb3ba6cbb1807de952614dd90d637b0539476` |
| `entropy_codec.py` | 11,883 | `42700a945c7c0fb68168c3325559ac85ec2c41d6` |
| `entropy_compression.py` | 18,574 | `b56e5d3520152d1c5317f2c839fbc9fec5a3bb2b` |
| `entropy_fixed_ui.py` | 17,859 | `4298caf7b18bb62a4128e1193bdd226f7890e54a` |
| `entropy_runtime.py` | 30,157 | `d674c56a49708f7a8bb97f47862510d426c837fc` |
| `entropy_scenario.py` | 17,563 | `1a4202179c5c5e97c2e9613f1feed386ec64653b` |
| `entropy_title.py` | 7,622 | `078125eb52a66be021ef46be9ce3ea50d1483b11` |
| `exact_ips_title.py` | 15,409 | `5d8602e3e292564bdb8c86eefaca1b6a5f09381e` |
| `fds.py` | 18,303 | `a0acdabce4f0144413b22e304f3abda45b206e91` |
| `font.py` | 13,979 | `21d4868ceffb588d6a9dee240f732927385a90c0` |
| `gameplay_graphics.py` | 14,648 | `bd02c5f7f8e5dccdb41db65fc8c2797cbdb34151` |
| `incremental_build.py` | 40,746 | `0166eefa6b89a11570bb624a53d677a307f8f750` |
| `menu_cancel.py` | 2,463 | `6edeae84a83f380ab41776011c5efe17754cb78a` |
| `menu_geometry.py` | 7,015 | `5726b3a584fea1e6b25a37b1072a9076a60aaea8` |
| `mesen_state.py` | 7,058 | `fac46bc4867fab4ed659489cd7501ab94e14505c` |
| `pagination_ctrl1_policy.py` | 7,390 | `56057ef4f7df38c5b7f6265eddf2208018ec674a` |
| `palette_animation.py` | 6,803 | `7e381ade181a8d1243e252ad964eb6a561d74845` |
| `part_handoff.py` | 1,411 | `b2f61495b612f172b61b041af5e80aad055f7612` |
| `production_translation_core.py` | 35,721 | `4c2da2be619693001cddbed25c2e4e069d5ad35a` |
| `production_translation.py` | 18,198 | `c13b2618febc0e75cfe167eba692be1ec62b24e8` |
| `production_validation.py` | 1,713 | `9c6aaa5900df78761c96663dd98fbbc341b20bac` |
| `project.py` | 5,182 | `9b824cdb07e4277be0650ea561ae2e8555e2b608` |
| `release_build.py` | 18,864 | `2a3f6cf799d82f3bff79992e92b4264af505fdfb` |
| `release_metadata.py` | 42,983 | `9c67db7827bfe5c5999dff47831511c77cdfad59` |
| `release.py` | 19,782 | `c79c6e1f5cd3e62af97e284691d910696d37836a` |
| `retail_vm.py` | 12,198 | `495b7916169860328449d191f24916ee78571959` |
| `runtime_lab.py` | 9,129 | `35c746d72d333259df4081f662aa7b93ef5d3316` |
| `scenario_validation.py` | 1,942 | `343ba4ca6e25b7a50eb0a8d50065633f3f12b7ff` |
| `scenario.py` | 20,929 | `15465a98729d732b6c5717eb512e92dbf2bf3ead` |
| `scene_transitions.py` | 1,319 | `1b2d29e92d20377feab5e3ff7057fdfede2ae9b7` |
| `textcodec.py` | 14,900 | `5f63ee63a595ddc84d48ea0cdd3c30ac13c18434` |
| `title_assets.py` | 27,727 | `6e042574bbb641e042eee46ab43ebf2d9c99814c` |
| `title_layout.py` | 8,841 | `64f7dbc219b33aaf2482991aac651465d8b77b42` |
| `title_patch.py` | 21,503 | `2819956d5c67fafcc5af41591212cfca62fd7076` |
| `title.py` | 4,831 | `5735163acb67f85355d9c390b2f49485ab8dce26` |
| `tt4_quiz.py` | 1,601 | `a3a5adcfbd83c9679bce89f2e1a6c5edc445ed71` |
| `ui_fixed_tables.py` | 16,822 | `3385afe4aaecee0691933f096cb7326f71381897` |
| `ui.py` | 49,399 | `250b0cc7d35e31d55c0811f0c6397a868a6057da` |
| `v38_build.py` | 9,919 | `60efcd7117788d05255589db370d5ad5dd74b500` |
| `v41_checkpoint.py` | 2,278 | `ef30e3f53cccf7e862ba99a35240dddc47d4eb64` |
| `v50_finalizer.py` | 6,329 | `6a0d8c3e061c796b73bb2bcfac2d5149e388bf51` |
| `v83_checkpoint.py` | 5,662 | `ba4a3cf2812956891450f258636f6cdc0ab03a22` |

### Public patcher and workflows

These components have separately managed distribution requirements and should
be checked against the published EXE/ZIP after each patcher change.

| File | Blob bytes | Git blob SHA |
| --- | ---: | --- |
| `.github/workflows/build-public-patcher.yml` | 1,308 | `48c67778a88fa75b9324391b64348cf160873119` |
| `.github/workflows/publish-v1.1.yml` | 5,076 | `4518c02d908c1e56bd9d91a182d93e0f02b30ee2` |
| `.github/workflows/tests.yml` | 2,350 | `d4b00e1e9ab26f391d90792485351e58086c0c36` |
| `release_patcher/build_patches.py` | 2,671 | `2cde8f55cccb1997abe38a0504acb778201dc57c` |
| `release_patcher/package_release.py` | 2,258 | `8b7500cebe4c9229c7e6025978367a3111c9d3bf` |
| `release_patcher/test_public_patcher.py` | 10,024 | `c9dedec003b06525f7912a48f617e86b037edf78` |
| `release_patcher/TimeTwistPatcher.py` | 28,759 | `642d852a5cc3247dc25c8eefebe50f875da46192` |

## Original behavior that must survive cleanup

1. Source-only distribution: do not commit Japanese/translated FDS images,
   FDS BIOS, emulator saves, extracted retail banks, or private fixtures.
2. Exact release authority: v83 is the confirmed English game baseline; the
   public version remains v1.1 unless an explicit release migration is approved.
3. Preserve canonical translation record identities, 13 bank maps, 1,305
   scenario records, 721 fixed menu labels, and the frozen entropy grammar.
4. Preserve byte-exact packed encodings, dictionary selection tie-breaks,
   record/page boundaries, FDS side ordering and sector integrity.
5. Preserve binary hash guards for private checkpoint lineage and for public
   patcher source and output identities.
6. Keep historical `recovery/`, `audit/`, and `docs/history/` as evidence.
   "Unreferenced by a current import" does **not** prove such data obsolete.
7. Keep `release/` downloads stable until a separately verified release
   migration provides a supported replacement.
8. Preserve the part 1 to part 2 continuation, disk-side checks, save/reload,
   UI, font, title animation, and audio timing; unit tests alone cannot
   certify these runtime properties.

## Recorded implementation comparison

The pre-cleanup allocator in `incremental_build.py` enumerated every
nonempty resident bitmask, recomputed resident and spilled sizes for each
possible split group and first-record boundary, collected all acceptable
plans in an options list, and selected the lowest priority tuple. Its
exhaustive implementation is deliberately preserved in
`work/tests/test_incremental_build.py` as `_reference_allocate_groups` for
differential testing.

The pre-cleanup native dictionary scanner in `compression.py` counted
leftmost, non-overlapping occurrences by repeated `bytes.find` calls and
advanced by the needle length. That algorithm is preserved as
`_legacy_occurrences` in `work/tests/test_native_compression_scan.py`.

The entropy prefix writer invoked `write_bits(..., 1)` for each character
in a frozen binary prefix. The original loop is preserved in the optional
`work/tools/benchmark_hotpaths.py` as `_OriginalPrefixWriter`. Byte parity
is separately locked in `work/tests/test_entropy_production.py`.

## Preservation policy

This baseline document is immutable historical evidence. Amend the active
maintenance guide, add dated follow-up history notes, and rely on Git object
identities to preserve exact old code. Do not silently edit this baseline
to reflect later refactors. The current public API and active module map are
maintained separately in `docs/CODE_TOUR.md` and `docs/MODULE_MAP.md`.
