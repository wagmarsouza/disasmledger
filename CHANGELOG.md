# Changelog

## v2.3.0 development preview — not installed or published

- Decompile 0.6.0-dev adds read-only monochrome census bars over existing closure validation/totals.
- Live denominator/G0 exclusions, G3 + G4-recon summary, uncertainty and legacy behavior are preserved.
  G4-stock, G4-recon, ambiguous legacy G4 and ungraded units remain separate; an all-G0 census is N/A.
- Added Unicode/ASCII display, bounded visual width, structured view output and 14 behavioral tests.
  No reconciler, scheduler, sender, project-specific constants or implicit migration is added.

## v2.2.0 development preview — not installed or published

- Decompile 0.5.0-dev adds an optional adapter from declared DisasmLedger snapshots to native
  VeriMission 8.2 observations, with frozen epoch units/G0 exclusions and explicit reconstruction projection.
- Raw stock-only/legacy grades and unprojected changes remain in source-bound receipts. Export never
  creates transition evidence, reconciles, promotes grades, revises missions or edits a harness store.
- Existing closure normalization/provenance are reused. New-bundle export and read-only verification
  bind current input/helper hashes; native reconciliation/reread remain in the original 8.2 engine.
- Added an explicit native-engine integration pilot and adapter tests. Existing APIs and separate
  skill operation are preserved. No external engine, live target, schedule or runtime deployment added.

## v2.1.0 development preview — not installed or published

- Decompile 0.4.0-dev adds optional graph/grade provenance receipts, producer-context binding and
  inferred/resolved/observed edge-origin summaries without changing legacy report-v2 behavior.
- Renode Bench 1.2.0-dev adds a read-only version/configuration-specific capability assessment and
  opt-in differential preflight. Unknown/unsupported features refuse invocation; changed context
  invalidates contextual comparison. No automatic fallback or dispatch is introduced.
- Added targeted angr guidance and calibrated Capstone, VFP and differential claim ceilings.
  Existing binary-profile identity/invalidation controls and all legacy helpers are preserved.
- Synthetic tests/pilot validate consistency, gating and compatibility only. No external engine,
  native ARM toolchain or real target is installed or exercised by this preview.

## v2.0.0 — 2026-11-06

- Decompile 0.3.0 distinguishes G4-stock from G4-recon; ambiguous legacy G4 blocks reconstruction closure rather than proving equivalence.
- Report format changes to decompile-closure-report-v2: live counts exclude G0 and separate stock/reconstruction grades; out-of-graph grade identifiers are rejected.
- Missing/null adjacency and declared unknown indirect calls block closure; coverage requires an explicit inventory-completeness declaration and reports uncertainty.
- Iterative closure supports deep graphs and conservatively unresolved cycles; malformed grade values and library limits receive structured errors.
- Relative graph/grade inputs now resolve under --project. Updated templates, pilot, migration guide, and 19 regression tests.
- Grades and evidence verification remain explicitly distinct. No automatic promotion, provenance verification, or universal equivalence is claimed.

## v1.1.0 — 2026-11-06

- Added a third skill, `decompile`: an orchestrator that composes `binary-analysis-profile` and `renode-bench` into a staged, grade-gated reconstruction workflow (G0 bogus → G1 raw → G2 semantics → G3 compiles → G4 bench-confirmed), with references for methodology, toolchain routing per stage, and differential testing.
- Added `closure.py`, a read-only scheduler that reports differentially-testable-now units and undone-helper leverage from a declared call graph and grade map; it never disassembles, executes, grades, or promotes, and keeps `semantic_truth_verified` and `promotion_authorized` false.
- Added synthetic templates, a pilot, and ten unit tests for the `decompile` skill.
- Extended the `renode-bench` skill (now 1.1.0) with `scripts/differential.py`, a recompile-and-bench executor that proves a reconstruction reproduces the stock under the two-witness discipline. It is emulator-agnostic through a pluggable `invoke` (Renode forced-invoke or Unicorn), owns only the generic compile/lay-in-RAM/compare parts, and ships ten synthetic tests plus an offline self-check that needs no cross-toolchain. It pairs with the decompile scheduler: `closure.py` schedules, `differential.py` proves.
- Split the `decompile` grade ladder's G4 into G4-stock (characterise the original) and G4-recon (prove our reconstruction), and documented the executor loop, its position-independence limit, and the indirect-edge caveat on closure scheduling (`decompile` now 0.2.0).
- Left the binary-analysis helper unchanged.
- Published installation guidance and explicit limitations for the decompile 0.2.0 scheduler, including its single G4 input label, G0 handling, missing adjacency, and declared-grade provenance.

## v1.0.1 — 2026-11-03

- Standardised the README, both skill descriptions, and all operator references in neutral international English.
- Preserved the binary-analysis and Renode helper behaviour.
- Verified 25 binary-profile tests, four trace-analyser tests, and the synthetic pilot.
