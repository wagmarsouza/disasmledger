# Changelog

## Unreleased

- Added a third skill, `decompile`: an orchestrator that composes `binary-analysis-profile` and `renode-bench` into a staged, grade-gated reconstruction workflow (G0 bogus → G1 raw → G2 semantics → G3 compiles → G4 bench-confirmed), with references for methodology, toolchain routing per stage, and differential testing.
- Added `closure.py`, a read-only scheduler that reports differentially-testable-now units and undone-helper leverage from a declared call graph and grade map; it never disassembles, executes, grades, or promotes, and keeps `semantic_truth_verified` and `promotion_authorized` false.
- Added synthetic templates, a pilot, and ten unit tests for the `decompile` skill.
- Extended the `renode-bench` skill (now 1.1.0) with `scripts/differential.py`, a recompile-and-bench executor that proves a reconstruction reproduces the stock under the two-witness discipline. It is emulator-agnostic through a pluggable `invoke` (Renode forced-invoke or Unicorn), owns only the generic compile/lay-in-RAM/compare parts, and ships ten synthetic tests plus an offline self-check that needs no cross-toolchain. It pairs with the decompile scheduler: `closure.py` schedules, `differential.py` proves.
- Split the `decompile` grade ladder's G4 into G4-stock (characterise the original) and G4-recon (prove our reconstruction), and documented the executor loop, its position-independence limit, and the indirect-edge caveat on closure scheduling (`decompile` now 0.2.0).
- Left the binary-analysis helper unchanged.

## v1.0.1 — 2026-11-03

- Standardised the README, both skill descriptions, and all operator references in neutral international English.
- Preserved the binary-analysis and Renode helper behaviour.
- Verified 25 binary-profile tests, four trace-analyser tests, and the synthetic pilot.
