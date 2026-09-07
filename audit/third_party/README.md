# Third-party comparison records

These files preserve the results and provenance of the completed comparison
against a removed third-party English patch. The comparison was diagnostic only;
third-party wording was never a translation authority.

The one-off decoder/comparison programs and their dedicated tests were removed
from the maintained tool surface after the audit was completed. Their exact code
remains available in Git history. Current English is defined only by the project
translation sources and fixed-UI code.

- [Scenario comparison](external_translation_baseline.md): reviewed input
  hashes, alignment counts, and Japanese-source findings.
- [Fixed-UI comparison](external_fixed_ui_baseline.md): recovered menu pages
  and system-text coverage.

These are completed audit records. Current compression usage is regenerated in
the [translation progress report](../../outputs/Time_Twist_translation_progress.md),
and runtime checks are tracked in the [playtest matrix](../../docs/PLAYTEST_MATRIX.md).
