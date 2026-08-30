# Quickstart

This guide is for contributors who want to inspect the project, edit ordinary
translation text, or run the public checks. It does not require ROM files.

## Requirements

- Python 3.11 or newer.
- `pip` associated with that Python installation.
- A checkout of this repository.

The public checkout intentionally excludes game images and extracted game data.
Do not add them to Git. If `python` is not on your path, install a supported
Python version or invoke the interpreter by its local path.

## Install for local development

From the repository root:

```powershell
python -m pip install -r requirements.txt
```

This installs the command-line tool and every public development and test tool
used by the project, including Hypothesis for the public unit suite.

## Public tests

```powershell
python -m tools.maintenance.run_tests unit
```

These tests are fixture-free: they exercise the codec, synthetic FDS behavior,
translation validation, compression, and release-control logic without game
files. A supported suite must have no skips.

## Explore the command-line tool

```powershell
time-twist --help
time-twist scenario-merge --help
```

The complete command reference is in [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).
Most translation contributors do not need to run low-level FDS commands.

## Build a local playtest candidate

You can skip this unless you have legally obtained Japanese FDS inputs and are
working from a checkout whose source lock is already approved. Place the inputs
only in the ignored local locations:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
```

Then verify the inputs and build an unpromoted candidate:

```powershell
time-twist release-lock
time-twist release-build --candidate --output-dir build/candidate
```

If `release-lock` reports a mismatch after an intentional source change, do
not update it casually. Follow the [maintainer release process](docs/MAINTAINER_RELEASE_PROCESS.md)
so the source change, candidate manifest, tests, and playtest evidence stay
connected.

## If private fixtures are unavailable

That is normal for public contributors. Run the public unit suite, do not
create substitute fixtures, and state in your pull request that private
ROM-derived integration tests were not available. A maintainer can run them
later against their legal local overlay.

## Where next?

- Improve the English script: [Contributing translation](CONTRIBUTING_TRANSLATION.md)
- Improve the tools or tests: [Contributing code](CONTRIBUTING_CODE.md)
- Playtest a candidate: [Playtesting guide](PLAYTESTING.md)
- Learn the deeper design: [Technical documentation index](docs/README.md)
