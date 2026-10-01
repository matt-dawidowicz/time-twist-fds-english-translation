# Open reverse-engineering and experimental work

The English translation is released, but the technical project does not have to
stop here.

This repository already contains a broad recovered model of *Time Twist*:
dialogue packing and rendering, control-code behavior, scenario-bank layout,
menus, gameplay script/event structures, graphics and CHR ownership, FDS scene
transitions, title behavior, release lineage, and multiple one-off runtime
systems. Start with [REVERSE_ENGINEERING_STATUS.md](REVERSE_ENGINEERING_STATUS.md)
and [REVERSE_ENGINEERING_GUIDE.md](REVERSE_ENGINEERING_GUIDE.md).

The goal of this page is to give future ROM hackers useful places to contribute
without asking them to rediscover solved systems.

## Good contribution targets

### 1. Name the remaining narrow unknowns

Several structures are already mechanically understood but still have
story-facing or semantic names that should only be assigned when evidence proves
them. Examples include residual gameplay command meanings and palette-effect
names.

A good contribution connects a value to a specific scene, trace, caller, or
visible result and upgrades the evidence status without guessing.

### 2. Expand runtime coverage

Many structures are statically verified, while some call sites still benefit
from broader manual runtime coverage.

Useful work includes:

- exercise all full-word menu call sites;
- exercise dynamic cursor and Back/Cancel behavior in nested and root menus;
- verify scene-specific graphics composition after targeted edits;
- document emulator-visible state around narrow regressions;
- add deterministic regression coverage when runtime behavior can be modeled
  statically.

### 3. Improve reverse-engineering ergonomics

The project has extensive knowledge in code and documentation. Tools that make
that knowledge easier to inspect are welcome.

Examples:

- address/bank cross-reference reports;
- annotated disassembly helpers;
- scenario/VM/graphics structure visualizers;
- trace-to-symbol correlation;
- pointer ownership reports;
- automated checks that detect contradictions between documentation, source
  guards, and recovered structures.

### 4. Investigate new bugs as narrow regressions first

The major engine families are no longer blank unknowns. When a visual, text,
menu, sound, transition, or gameplay defect appears, first locate the owning
subsystem and test the existing model.

A new symptom is not evidence that the whole engine model is wrong.

### 5. Prototype ambitious changes in a fork or feature branch

You are free to experiment beyond the canonical release:

- alternative renderers;
- different text packing;
- tooling rewrites;
- engine refactors;
- expanded debugging instrumentation;
- emulator-focused experiments;
- new asset workflows.

These experiments do not need prior approval. If an experiment matures into
something appropriate for the canonical project, open a pull request against
`main` with evidence and testing.

## How to propose canonical changes

1. Fork the repository or create a feature branch.
2. Make and test the change there.
3. Update documentation when the recovered technical model changes.
4. Open a pull request targeting `main`.
5. Complete the pull-request template with reproduction and validation details.
6. The repository CODEOWNERS file requests review from `@matt-dawidowicz`.
7. The maintainer decides whether and when the change becomes part of the
   canonical release.

The point is to keep experimentation open while keeping the official release
deliberate and reproducible.

## Current maintained status

For the authoritative list of solved versus unresolved subsystems, do not
duplicate it here. Use:

- [Reverse-engineering status](REVERSE_ENGINEERING_STATUS.md)
- [Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md)
- [Engine change history](ENGINE_CHANGELOG.md)
- [ROM modification inventory](ROM_MODIFICATION_INVENTORY.md)

When a discovery changes the status of a subsystem, update
`REVERSE_ENGINEERING_STATUS.md` as part of the same pull request.
