"""Rank natural-English line layouts by exact whole-bank compression cost.

The tool preserves the supplied prose verbatim and varies only presentation
row breaks. Each legal layout is written into a temporary translation map and
rebuilt through the canonical scenario-bank path with maximize-headroom
compression enabled. This measures the real interaction between wrapping,
record alignment, dictionary selection, fixed UI requirements, and the bank's
unchanged capacity.

It is intentionally an audit tool rather than an automatic source editor. A
maintainer can review the ranked variants and then choose the natural layout to
promote into the translation map.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

from time_twist import release as release_module
from time_twist.editorial_layout import presentation_break_variants
from time_twist.fds import FdsImage
from time_twist.release_compression import (
    compress_release_groups as compression_policy,
)
from time_twist.release_metadata import SCENARIO_LOCATIONS, ReleasePaths
from time_twist.scenario_validation import PRESENTATION_BREAK_RECORD_IDS


@dataclass(frozen=True)
class LayoutAuditResult:
    """Exact compressed-bank measurement for one presentation layout."""

    layout: str
    packed_bytes: int
    capacity_bytes: int
    headroom_bytes: int
    dictionary_entries: int
    seconds: float


@contextmanager
def _maximize_headroom_policy() -> Iterator[None]:
    """Temporarily force the release facade to use editorial compression."""
    original = release_module.compress_release_groups

    def deep_policy(*args: object, **kwargs: object) -> object:
        """Forward one compression call with the fast-accept shortcut disabled."""
        kwargs["maximize_headroom"] = True
        return compression_policy(*args, **kwargs)

    release_module.compress_release_groups = deep_policy  # type: ignore[assignment]
    try:
        yield
    finally:
        release_module.compress_release_groups = original


def _source_bank(bank_name: str, *, paths: ReleasePaths) -> bytes:
    """Load one scenario component from its canonical Japanese FDS baseline."""
    image_name, side = SCENARIO_LOCATIONS[bank_name]
    baseline = (
        paths.zenpen_baseline if image_name == "zenpen" else paths.kouhen_baseline
    )
    image = FdsImage.from_bytes(baseline.read_bytes())
    return image.sides[side].find_file(bank_name).data


def _translation_map(paths: ReleasePaths, bank_name: str) -> dict[str, str]:
    """Load one reviewed bank translation map with string-only validation."""
    path = paths.translations / f"{bank_name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in payload.items()
    ):
        raise ValueError(f"{path} must map string record IDs to strings")
    return payload


def audit_layouts(
    project_root: Path,
    *,
    bank_name: str,
    record_id: str,
    natural_text: str,
) -> tuple[LayoutAuditResult, ...]:
    """Deep-compress every legal layout of one reviewed natural sentence."""
    if bank_name not in SCENARIO_LOCATIONS:
        raise ValueError(f"unknown scenario bank {bank_name}")
    if not record_id.startswith(f"{bank_name}/"):
        raise ValueError(f"record {record_id} does not belong to {bank_name}")
    if record_id not in PRESENTATION_BREAK_RECORD_IDS:
        raise ValueError(
            f"{record_id} is not allowlisted for English presentation breaks"
        )

    paths = ReleasePaths.from_project_root(project_root)
    source = _source_bank(bank_name, paths=paths)
    translations = _translation_map(paths, bank_name)
    if record_id not in translations:
        raise ValueError(f"{record_id} is absent from {bank_name} translations")
    layouts = presentation_break_variants(natural_text)

    results: list[LayoutAuditResult] = []
    with tempfile.TemporaryDirectory(
        prefix="time-twist-layout-audit-"
    ) as directory:
        root = Path(directory)
        translation_directory = root / "translations"
        translation_directory.mkdir()
        build_directory = root / "build"
        build_directory.mkdir()

        for index, layout in enumerate(layouts):
            candidate = dict(translations)
            candidate[record_id] = layout
            (translation_directory / f"{bank_name}.json").write_text(
                json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            started = perf_counter()
            with _maximize_headroom_policy():
                built = release_module.build_scenario_bank(
                    source,
                    bank_name,
                    temporary_directory=build_directory / f"variant-{index}",
                    translations_directory=translation_directory,
                )
            seconds = perf_counter() - started
            results.append(
                LayoutAuditResult(
                    layout=layout,
                    packed_bytes=built.packed_bytes,
                    capacity_bytes=built.capacity_bytes,
                    headroom_bytes=built.capacity_bytes - built.packed_bytes,
                    dictionary_entries=built.dictionary_entries,
                    seconds=seconds,
                )
            )

    return tuple(
        sorted(
            results,
            key=lambda result: (
                result.packed_bytes,
                result.layout.count("{CTRL:0}"),
                result.layout,
            ),
        )
    )


def _print_results(results: tuple[LayoutAuditResult, ...]) -> None:
    """Print ranked layouts with visible row separators and exact byte costs."""
    print("Rank  Packed  Free  Dict  Seconds  Layout")
    print("----  ------  ----  ----  -------  ------")
    for rank, result in enumerate(results, start=1):
        visible = result.layout.replace("{CTRL:0}", " / ")
        print(
            f"{rank:>4}  {result.packed_bytes:>6}  "
            f"{result.headroom_bytes:>4}  {result.dictionary_entries:>4}  "
            f"{result.seconds:>7.3f}  {visible}"
        )


def build_parser() -> argparse.ArgumentParser:
    """Return command-line arguments for one record-level layout audit."""
    parser = argparse.ArgumentParser(
        description="Rank legal English row breaks by whole-bank packed size.",
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--bank", required=True, choices=tuple(SCENARIO_LOCATIONS))
    parser.add_argument("--record", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run one compression-aware layout audit without modifying source files."""
    args = build_parser().parse_args(argv)
    results = audit_layouts(
        args.project_root,
        bank_name=args.bank,
        record_id=args.record,
        natural_text=args.text,
    )
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        _print_results(results)


if __name__ == "__main__":
    main()
