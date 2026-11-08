# Read-only census bars

`scripts/census_bars.py` presents the existing declared grade census as monochrome text. It reuses
`closure.build_report` and `closure.normalize`; it does not change their inputs, totals, denominator,
scheduling, proof gates or grade semantics. It neither runs nor replaces VeriMission's reconciler.
There is no target-specific path, fixed project total, automatic display loop or file output.

```powershell
python -B 'PATH_TO_SKILL/scripts/census_bars.py' --project 'PROJECT_ROOT' --callgraph analysis/callgraph.json --grades analysis/grades.json
python -B 'PATH_TO_SKILL/scripts/census_bars.py' --project 'PROJECT_ROOT' --callgraph analysis/callgraph.json --grades analysis/grades.json --ascii --width 40
python -B 'PATH_TO_SKILL/scripts/census_bars.py' --project 'PROJECT_ROOT' --callgraph analysis/callgraph.json --grades analysis/grades.json --json
```

Input formats remain `decompile-callgraph-v1` and `decompile-grades-v1`. Relative input paths resolve
under the explicit project; explicit absolute input paths are read-only too, as in the existing
closure CLI. TSV exports from a particular project are not parsed or migrated implicitly. Generate
the standard inputs through the existing inventory/export workflow. For target/source binding,
use the existing profile/provenance checks before presenting the frozen snapshots.

## What the rows mean

Rows partition the declared LIVE inventory without overlap:

- G1, G2 and G3.
- G4-stock: observations of the original, not a reconstructed/compiled unit.
- G4-recon: declared reconstruction comparisons, separate from stock.
- G4-ambiguous: unresolved legacy `G4`, never silently interpreted as stock or recon.
- ungraded: live units missing a grade.

G0 exclusions and the original inventoried count are reported separately. The denominator is the
existing closure report's live node count, not a manual override. The summary G3 + G4-recon reuses
`done_g3_plus` and is explicitly a summary, not an additional partition row. G4-stock is not added
to it. Labels describe declarations, not verified correctness or universal behavioral coverage.

An all-G0 census has no live denominator and percentages are N/A. Incomplete inventory, unresolved
dependencies, missing grades and legacy G4 retain the original indeterminate-coverage signal. Unknown
counts are not promoted to completion merely because a bar is drawn.

## Rendering and limits

Default bars use Unicode blocks `█`/`▒`, without ANSI colors. `--ascii` uses `#`/`.` when a terminal
cannot display them. Width is 1..200 characters, default 30; it is a display bound, not a memory or
inventory limit. Only filled cells and one-decimal text percentages are rounded. Original counts
and the structured percentages remain unchanged; independently rounded rows can sum to 99.9 or
100.1 percent. Invalid counts are rejected rather than hidden by clipping an overfull bar.

`--json` emits `ok/result` with format `disasm-census-display-v1`. This is a derived presentation,
not a new ledger. `semantic_truth_verified`, `promotion_authorized`, `evidence_verified` and
`reconciliation_executed` remain false. Exit 0 means the view was produced; exit 2 means invalid
input or options. The command writes only stdout and does not edit the census or host configuration.

Run against the shipped synthetic inputs from the repository root:

```powershell
python -B skills/decompile/scripts/census_bars.py --project . --callgraph skills/decompile/assets/templates/callgraph.example.json --grades skills/decompile/assets/templates/grades.example.json --ascii
python -B -m unittest discover -s skills/decompile/tests -p test_census_bars.py
```

The presentation can be quoted in an authorized report or message; this does not install a hook,
send a message or create a schedule. Keep source identity, scope and evidence limits alongside it.
