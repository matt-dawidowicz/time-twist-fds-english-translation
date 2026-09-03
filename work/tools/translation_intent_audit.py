#!/usr/bin/env python3
"""Rank scenario records for source-grounded intent-preservation review.

This audit is deliberately conservative. It does not claim to score Japanese
translation quality automatically and it never rewrites playable text. Instead,
it surfaces records where the project's own review layers already indicate that
additional human/editorial attention may recover meaning, sentiment, register,
voice, subtext, or dramatic rhythm.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

BANK_ORDER = (
    "TT1A",
    "TT1B",
    "TT2",
    "T22",
    "TT3A",
    "TT3B",
    "TT4",
    "TT5",
    "T25",
    "TT6A",
    "TT6B",
    "TT6C",
    "TT6D",
)
CONTROL_RE = re.compile(r"\{CTRL:\d+\}")
NEUTRAL_REGISTER_LABELS = {
    "",
    "Unmarked / neutral or context-dependent",
    "Unmarked / neutral",
}
ACCURATE_LABELS = {"", "Accurate", "None", "none"}
TYPOGRAPHY_TRANSLATION = str.maketrans(
    {
        "…": "...",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "‐": "-",
        "‑": "-",
        "–": "-",
        "—": "-",
        "　": " ",
    }
)


@dataclass(frozen=True)
class IntentGap:
    """Describe one scenario record that merits editorial re-review."""

    bank: str
    record_id: str
    score: int
    wording_similarity: float
    runtime_evidence_required: bool
    reasons: tuple[str, ...]
    japanese: str
    literal: str
    natural: str
    playable: str
    speaker: str
    register: str
    problems: str
    nuance_lost: str
    unresolved_ambiguity: str


def visible_text(text: str) -> str:
    """Return visible text with control tags replaced by ordinary spaces."""
    return CONTROL_RE.sub(" ", text)


def normalize_visible_text(text: str) -> str:
    """Normalize visible English for wording-divergence comparison.

    The comparison intentionally ignores presentation controls, Unicode-versus-
    ASCII typography, and repeated whitespace. It does not remove lexical words
    or punctuation wholesale, because those can carry tone and dramatic force.
    """
    text = unicodedata.normalize("NFKC", visible_text(text))
    text = text.translate(TYPOGRAPHY_TRANSLATION)
    return " ".join(text.split()).strip()


def wording_similarity(natural: str, playable: str) -> float:
    """Return a stable 0..1 similarity score for normalized visible English."""
    natural_norm = normalize_visible_text(natural)
    playable_norm = normalize_visible_text(playable)
    if not natural_norm and not playable_norm:
        return 1.0
    return SequenceMatcher(None, natural_norm, playable_norm).ratio()


def _yes(value: object) -> bool:
    """Return whether a workbook flag is explicitly affirmative."""
    return str(value).strip().casefold() in {"yes", "true", "1"}


def _nontrivial(value: object, *, neutral: set[str]) -> str:
    """Return cleaned metadata text unless it is a known neutral label."""
    cleaned = str(value or "").strip()
    if cleaned in neutral:
        return ""
    return cleaned


def score_row(row: dict[str, object]) -> IntentGap | None:
    """Convert one workbook scenario row into a ranked review candidate.

    The score is a triage heuristic, not a translation-quality grade. Higher
    values mean that more of the project's existing evidence points toward a
    possible gap between the reviewed natural reading and the playable line.
    Lines requiring gameplay/staging evidence stay visible but are explicitly
    flagged so an automated prose pass does not guess through ambiguity.
    """
    if row.get("record_type") != "scenario":
        return None

    record_id = str(row.get("original_record_id", ""))
    bank = str(row.get("bank", ""))
    natural = str(row.get("final_natural_english_translation", ""))
    playable = str(row.get("patch_safe_english_translation", ""))
    natural_norm = normalize_visible_text(natural)
    playable_norm = normalize_visible_text(playable)
    similarity = wording_similarity(natural, playable)

    reasons: list[str] = []
    score = 0

    if natural_norm != playable_norm:
        # A lexical/punctuation divergence is evidence that the preservation
        # layer contains wording not currently shown in game. Weight the actual
        # magnitude without treating length itself as a quality objective.
        divergence_points = max(10, round((1.0 - similarity) * 60))
        score += divergence_points
        reasons.append(
            f"natural/playable wording diverges ({similarity:.3f} similarity)"
        )

    nuance_lost = _nontrivial(
        row.get("nuance_lost_in_patch_safe_version"),
        neutral={"", "None", "none"},
    )
    if nuance_lost:
        score += 80
        reasons.append("workbook explicitly records lost nuance")

    problems = _nontrivial(
        row.get("problems_with_current_english"), neutral=ACCURATE_LABELS
    )
    if problems:
        score += 55
        reasons.append("current-English review records a problem")

    categories = _nontrivial(
        row.get("problem_categories"), neutral=ACCURATE_LABELS
    )
    if categories:
        score += 25
        reasons.append("problem category is not marked accurate")

    if _yes(row.get("requires_technical_expansion")):
        score += 55
        reasons.append("review marks technical expansion as useful/required")

    register = _nontrivial(
        row.get("dialect_or_register"), neutral=NEUTRAL_REGISTER_LABELS
    )
    if register:
        score += 15
        reasons.append("source has marked register/dialect/voice evidence")

    speaker = str(row.get("speaker_or_narration_identity", "")).strip()
    unresolved = _nontrivial(
        row.get("unresolved_ambiguity"), neutral={"", "None", "none"}
    )
    runtime_required = _yes(row.get("requires_gameplay_context")) or bool(
        unresolved
    )
    if runtime_required:
        reasons.append("runtime/staging evidence required before rewriting")

    # If the only difference is an audited presentation control or typography,
    # and the workbook records no other concern, there is no intent gap to rank.
    if not reasons or (
        natural_norm == playable_norm
        and not nuance_lost
        and not problems
        and not categories
        and not _yes(row.get("requires_technical_expansion"))
        and not register
        and not runtime_required
    ):
        return None

    return IntentGap(
        bank=bank,
        record_id=record_id,
        score=score,
        wording_similarity=round(similarity, 6),
        runtime_evidence_required=runtime_required,
        reasons=tuple(reasons),
        japanese=str(row.get("exact_japanese_source", "")),
        literal=str(row.get("literal_english_meaning", "")),
        natural=natural,
        playable=playable,
        speaker=speaker,
        register=register,
        problems=problems,
        nuance_lost=nuance_lost,
        unresolved_ambiguity=unresolved,
    )


def load_workbook_rows(
    project_root: Path, banks: Iterable[str]
) -> list[dict[str, object]]:
    """Load generated per-bank workbook rows for the requested scenario banks."""
    rows: list[dict[str, object]] = []
    for bank in banks:
        path = (
            project_root
            / "work"
            / "translation_workbook_banks"
            / f"{bank}.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        bank_rows = payload.get("rows")
        if not isinstance(bank_rows, list):
            raise ValueError(f"{path}: workbook checkpoint has no row list")
        rows.extend(row for row in bank_rows if isinstance(row, dict))
    return rows


def rank_intent_gaps(rows: Iterable[dict[str, object]]) -> list[IntentGap]:
    """Return review candidates in deterministic editorial-priority order."""
    gaps = [gap for row in rows if (gap := score_row(row)) is not None]
    return sorted(
        gaps,
        key=lambda gap: (
            gap.runtime_evidence_required,
            -gap.score,
            (
                BANK_ORDER.index(gap.bank)
                if gap.bank in BANK_ORDER
                else len(BANK_ORDER)
            ),
            gap.record_id,
        ),
    )


def render_markdown(
    gaps: Iterable[IntentGap], *, limit: int | None = None
) -> str:
    """Render a compact source-grounded Markdown review queue."""
    selected = list(gaps)
    if limit is not None:
        selected = selected[:limit]

    lines = [
        "# Translation intent-gap audit",
        "",
        "This is a triage report, not an automatic translation grade. Records are",
        "ranked from the project's existing Japanese/linguistic/voice/workbook evidence.",
        "Runtime-blocked records are retained but sorted after immediately actionable",
        "records so staging ambiguity is not guessed away.",
        "",
        "| Score | Record | Runtime evidence | Reasons | Natural | Playable |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for gap in selected:
        reasons = "; ".join(gap.reasons).replace("|", "\\|")
        natural = gap.natural.replace("|", "\\|").replace("\n", " ")
        playable = gap.playable.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {gap.score} | `{gap.record_id}` | "
            f"{'yes' if gap.runtime_evidence_required else 'no'} | {reasons} | "
            f"{natural} | {playable} |"
        )
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the intent-gap audit."""
    parser = argparse.ArgumentParser(
        description="Rank scenario records for source-grounded intent-preservation review."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--bank",
        action="append",
        choices=BANK_ORDER,
        help="Restrict to one bank; repeat for multiple banks.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Show only the first N ranked records.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of Markdown.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the intent-gap audit CLI."""
    args = _parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be positive")
    banks = tuple(args.bank) if args.bank else BANK_ORDER
    rows = load_workbook_rows(args.project_root.resolve(), banks)
    gaps = rank_intent_gaps(rows)
    if args.limit is not None:
        gaps = gaps[: args.limit]

    if args.json:
        print(
            json.dumps(
                [asdict(gap) for gap in gaps], ensure_ascii=False, indent=2
            )
        )
    else:
        print(render_markdown(gaps), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
