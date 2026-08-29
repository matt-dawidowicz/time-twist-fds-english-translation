# Runtime Validation

Status: **in progress / not yet runtime-certified**

This branch begins the post-PR-18 runtime certification pass from `main` merge commit `ad5ebe9fced6807c6398691db1b36c58e9b1d095`.

PR #18 established the reviewed English source, 68-entry dictionary/capacity architecture, regenerated review artifacts, and green public CI. This validation pass deliberately happens afterward so runtime findings and any resulting fixes are isolated from the completed source/audit merge.

## Validation contract

A successful public/source build is necessary but not sufficient for release promotion. Runtime certification must exercise the exact candidate produced from the locked legal baseline images and prove that the rebuilt overlays behave correctly in the emulator across the complete game.

Do not mark this pass complete merely because the game boots or because automated recompression fits. Record the exact candidate hashes used for the playthrough and keep fixes on this branch until the corresponding candidate is rebuilt and rechecked.

## Candidate preparation

- [ ] Confirm this branch is based on `ad5ebe9fced6807c6398691db1b36c58e9b1d095` or a documented descendant containing only validation fixes.
- [ ] Re-lock the approved non-code release sources for the post-PR-18 translation authority.
- [ ] Build a fresh candidate from the legally obtained Zenpen and Kouhen baseline images.
- [ ] Record candidate SHA-256 hashes here before runtime testing begins.
- [ ] Run the private ROM-derived integration suite against the exact candidate revision.
- [ ] Confirm all 13 scenario banks still fit and all fixed/menu audits pass.

### Candidate identity

- Zenpen SHA-256: **pending**
- Kouhen SHA-256: **pending**
- Source commit: **pending final candidate commit**
- Emulator/version: **pending**

## Runtime checklist

### Global / interface

- [ ] English title/opening sequence displays correctly from a cold boot.
- [ ] New Game / Continue / save-load paths work normally.
- [ ] Disk prompts and side changes display correct full-word English text.
- [ ] Command, object, topic, answer, and quiz menus render without clipping, stale text, bad pointers, or abbreviations.
- [ ] Exercise menu records around the 32-, 64-, and 96-entry boundaries in affected overlays.
- [ ] Move the cursor across those boundaries and select entries on both sides.
- [ ] Exercise Back/Cancel paths after boundary crossings.
- [ ] Save, reload, and resume from multiple story positions.

### Zenpen

- [ ] Complete the opening/personality sequence.
- [ ] Complete the museum / Devil opening material.
- [ ] Complete the France / Jeanne material.
- [ ] Complete the Nazi Germany / resistance material.
- [ ] Complete the ancient Greece material.
- [ ] Complete the American Civil War material.
- [ ] Verify the intended Zenpen-to-Kouhen transition and disk handling.

### Kouhen

- [ ] Enter Kouhen through the normal transition rather than relying only on direct boot.
- [ ] Complete the Joseph / Mary material.
- [ ] Complete the Magi / quiz material.
- [ ] Complete the Jesus / Devil finale material.
- [ ] Verify the final girl scene and ending sequence.
- [ ] Confirm the game reaches its intended final state without hangs, corrupt text, pointer failures, or save-state-only workarounds.

## Findings

Record every runtime problem with:

1. exact source commit and candidate hash,
2. emulator/version,
3. story/bank and stable record ID when applicable,
4. reproduction steps,
5. screenshot/save-state evidence when useful,
6. whether the defect is translation, renderer/layout, compression, pointer/relocation, menu paging, disk flow, save/load, or unrelated game behavior.

No runtime findings recorded yet.

## Fix policy

If testing uncovers a defect:

- fix the authoritative source rather than patching a generated FDS image,
- add or strengthen an automated regression test where feasible,
- regenerate tracked review artifacts if authoritative translation/UI text changes,
- rerun public CI and the relevant private integration checks,
- rebuild a new candidate and replace the hashes above,
- re-test the affected path before continuing certification.

## Completion gate

This validation pass is complete only when the exact final candidate has passed the relevant automated/private checks and a complete Zenpen-to-Kouhen runtime playthrough without unresolved release-blocking defects.

Release promotion (`release_target.json` and any public release packaging) should occur only after those boxes are satisfied.
