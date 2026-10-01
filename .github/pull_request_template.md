## What does this change?

Describe the proposed change and why it belongs in the canonical project.

## Area affected

- [ ] Translation / wording
- [ ] Scenario text layout or controls
- [ ] Rendering
- [ ] Graphics / CHR / nametables / metasprites
- [ ] Gameplay script / event VM
- [ ] FDS layout / disk behavior
- [ ] Runtime 6502 code
- [ ] Build / release tooling
- [ ] Tests / validation
- [ ] Documentation / reverse engineering
- [ ] Other

## Reverse-engineering evidence

If this changes or extends the technical model, include the relevant component,
file offsets, CPU/PPU addresses, callers or pointer chain, and evidence status
(VERIFIED / OBSERVED / DERIVED / INFERRED / UNKNOWN).

If this is a narrow bug fix using an already documented model, link the relevant
documentation instead.

## Reproduction and testing

Describe exactly how you tested the change.

- Public unit tests:
- Integration tests, if available:
- Emulator and version:
- Disk side / story location:
- Reproduction steps:
- Save state or clean-state route, if useful:
- Before/after screenshots, if visual:

## Release impact

- [ ] No release binary impact
- [ ] Changes generated ROM bytes
- [ ] Changes release hashes / provenance
- [ ] Changes patcher or BPS output
- [ ] May affect existing save states or disk-write state
- [ ] Requires broader playtesting

If generated ROM bytes change, identify the intended region(s) and explain why
the binary difference is expected.

## Canonical-main request

By opening this pull request against `main`, I am proposing this change for the
maintainer-controlled canonical release. Experimental work that is not ready for
that standard is welcome to remain in a fork or feature branch.
