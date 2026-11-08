# Census presentation verification — local preview, 2026-11-08

Base: `300eb74`, isolated branch `feature/census-bars`. New component: Decompile 0.6.0-dev;
repository preview 2.3.0. No installation, publication, live-census edits or real target execution.

The new renderer reuses the existing closure validation/report and only formats its declared
counts plus mutually exclusive grade rows. Original `closure.py`, `verimission_adapter.py`,
Renode Bench and Binary Analysis Profile sources have no diff from the base.

Observed source checks:

- All 14 new presentation tests passed. The complete Decompile suite then passed 84 tests.
- Tests cover separate stock/recon and ambiguous grades; source-total parity; no stock-only
  reconstruction; fixed live denominator/G0 exclusions; all-G0 N/A; missing grades/unresolved calls;
  incomplete inventory; width/rounding behavior; no input mutations; read-only CLI/ASCII/JSON;
  rejection of manual denominator override and reuse of the original invalid-grade validator.
- The shipped synthetic graph/grades were rendered successfully with ASCII bars. Their original
  source calculations remained unchanged; visual rounding did not change counts.

Run the standalone tests:

```powershell
python -B -m unittest discover -s skills/decompile/tests -p test_census_bars.py
python -B -m unittest discover -s skills/decompile/tests
```

Final ZIP extraction/regression results and hashes are recorded separately in the new delivery's
`VALIDACAO_FINAL.json`, `RELATORIO_REVISAO_FINAL.md` and `SHA256SUMS.txt`. Previous delivery artifacts
are preserved. The bar-width bound is for display only; it is not a limit on the census or memory.

This is not a new accounting engine, proof gate or reconciler. The renderer does not parse/migrate
a target-specific TSV, infer inventory completeness, authenticate grades, draw hardware conclusions,
send messages or install a periodic reporter. Percentages describe declared live-unit distribution,
not verified semantic coverage. Separate statistical rounding may make displayed rows sum to 99.9
or 100.1 percent. No actual firmware, engine or target-specific census was used to test this feature.
