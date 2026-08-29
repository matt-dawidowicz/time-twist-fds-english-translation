"""Remove legacy TT2 dictionary-pointer constants after the deep cleanup."""

from __future__ import annotations

import ast
from pathlib import Path

PATH = Path("work/time_twist/ui_fixed_tables.py")
TARGETS = {
    "TT2_DICTIONARY_POINTER_OFFSET",
    "TT2_LOAD_ADDRESS",
    "TT2_DICTIONARY_ENTRIES",
}
source = PATH.read_text(encoding="utf-8")
tree = ast.parse(source)
lines = source.splitlines(keepends=True)
spans: list[tuple[int, int, str]] = []
found: set[str] = set()
for node in tree.body:
    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
        continue
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names = {
        target.id
        for target in targets
        if isinstance(target, ast.Name) and target.id in TARGETS
    }
    if not names:
        continue
    if len(names) != 1 or node.end_lineno is None:
        raise SystemExit("unexpected TT2 legacy assignment shape")
    name = next(iter(names))
    spans.append((node.lineno - 1, node.end_lineno, name))
    found.add(name)
if found != TARGETS:
    raise SystemExit(f"TT2 legacy constants mismatch: {sorted(TARGETS - found)}")
for start, end, _ in sorted(spans, reverse=True):
    del lines[start:end]
PATH.write_text("".join(lines), encoding="utf-8")
