# DisasmLedger 2.3.0 — public preview 1

## Result

- **Decompile 0.6.0-dev:** read-only census bars reuse existing closure validation/totals. G4-stock,
  G4-recon, ambiguous legacy G4 and ungraded units have separate rows. G0 is excluded from the live
  denominator; an empty live census is N/A. The G3 + G4-recon summary never counts stock as reconstructed.
  Unicode/ASCII and JSON output do not change source calculations or grade files.
- **Optional VeriMission 8.2 adapter:** source-bound declared snapshot bundles reuse existing
  normalization and project to the native generic observation contract. Stock/legacy grades stay in
  receipts and do not become reconstruction. The native VeriMission engine owns reconciliation;
  export grants no promotion, mission-revision authority or implicit migration.
- **Provenance and bench refinements:** optional producer/source binding, conservative tool routing
  and Renode Bench 1.2.0-dev version/configuration capability assessment gate opt-in execution.
  Unknown/unsupported capability refuses invocation; no automatic fallback is introduced.
- **Binary Analysis Profile 1.0.1:** existing behavior is preserved.

## Contents and use

- `DisasmLedger-2.3.0-preview.zip`: all three independent skills, scripts, examples and tests.
- `decompile-0.6.0-preview.zip`, `renode-bench-1.2.0-preview.zip` and
  `binary-analysis-profile-1.0.1.zip`: standalone skills.

Python 3.11+ is required for helpers. Engines and compilers remain separate dependencies for a real
authorized bench. Native reconciliation additionally requires the separate VeriMission 8.2 engine
and its PyYAML dependency. Nothing installs sibling skills or tools automatically.

From a checkout at this tag, with your existing declared graph/grade JSON:

```powershell
$p = 'C:\your-project'
python -B skills/decompile/scripts/census_bars.py --project $p --callgraph analysis/callgraph.json --grades analysis/grades.json
python -B skills/decompile/scripts/census_bars.py --project $p --callgraph analysis/callgraph.json --grades analysis/grades.json --ascii --width 40
python -B skills/decompile/scripts/census_bars.py --project $p --callgraph analysis/callgraph.json --grades analysis/grades.json --json
python -B skills/decompile/scripts/verimission_adapter.py --help
python -B skills/renode-bench/scripts/executor_capabilities.py --help
```

See [census presentation](../skills/decompile/references/census-presentation.md),
[the adapter guide](../skills/decompile/references/verimission-adapter.md) and
[executor capabilities](../skills/renode-bench/references/executor-capabilities.md).
No project-specific TSV or private denominator was copied into the generic presenter.

Decompile passed **84 tests** (including **14 new bar tests**); Renode Bench passed **33**; Binary
Analysis Profile passed **24**, with **one pre-existing Windows symlink skip**. Pilots, the differential
self-test and seven integration scenarios against the native VeriMission 8.2 engine passed.
Percentages describe declared grade distribution, not independently verified semantic coverage.

## Release verification and limits

The pre-publication extracted-package run executed 339 primary tests: 338 passed and one existing
Windows symlink test was skipped in Binary Analysis Profile. Repeated standalone runs are not
counted as additional independent tests. Five targeted control-inversion experiments were caught
by their focused tests; this is not a global mutation score or an independent audit.

Only publication documentation and package metadata changed after that run. Release packaging
checks every previously tested runtime/resource file against the reviewed snapshot and verifies
ZIP paths, manifests, byte counts and SHA-256 hashes. The release receipt distinguishes the tested
commit from the publication commit; no fresh runtime test run is claimed for documentation edits.

Validation used synthetic fixtures on Windows. No Linux/macOS matrix, real firmware, ARM compiler,
Renode/Unicorn/Ghidra/angr engine or live mission/memory was exercised. Hashes and consistency checks
do not authenticate authorship, cognition or semantic truth. Extraction does not install a skill,
start a scheduler or grant new permissions. Existing releases remain available.

Earlier verification documents are historical reports about the development stage and its older
archives. Use this release's per-project `SHA256SUMS.txt`, `RELEASE_RECEIPT.json` and ZIP manifests
for the published artifacts. The previously reviewed local delivery remains preserved.
