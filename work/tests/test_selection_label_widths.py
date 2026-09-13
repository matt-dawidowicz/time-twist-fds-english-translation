"""Regression coverage for NOV2 dynamic selection-label width inputs."""

from __future__ import annotations

from time_twist import ui


def test_nov2_selection_labels_have_no_semantic_edge_whitespace() -> None:
    """Keep invisible slot padding out of dynamic selection-width measurements."""
    labels = [
        (bank_name, index, text)
        for bank_name, spec in ui.FIXED_RECORD_TABLE_SPECS.items()
        for index, text in enumerate(spec.records)
    ]
    labels.extend(
        ("TT1A", index, patch[2])
        for index, patch in enumerate(
            (
                *ui.TT1A_BLOOD_TYPE_PATCHES,
                *ui.TT1A_MONTH_PATCHES,
                *ui.TT1A_CONFIRMATION_PATCHES,
            )
        )
    )
    assert len(labels) == 740
    offenders = [
        (bank_name, index, repr(text))
        for bank_name, index, text in labels
        if text != text.strip()
    ]
    assert offenders == []
