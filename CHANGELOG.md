# Changelog

## Unreleased

- Added a third skill, `decompile`: an orchestrator that composes `binary-analysis-profile` and `renode-bench` into a staged, grade-gated reconstruction workflow (G0 bogus → G1 raw → G2 semantics → G3 compiles → G4 bench-confirmed), with references for methodology, toolchain routing per stage, and differential testing.
- Added `closure.py`, a read-only scheduler that reports differentially-testable-now units and undone-helper leverage from a declared call graph and grade map; it never disassembles, executes, grades, or promotes, and keeps `semantic_truth_verified` and `promotion_authorized` false.
- Added synthetic templates, a pilot, and ten unit tests for the new skill; preserved the existing binary-analysis and Renode helpers unchanged.

## v1.0.1 — 2026-11-03

- Standardised the README, both skill descriptions, and all operator references in neutral international English.
- Preserved the binary-analysis and Renode helper behaviour.
- Verified 25 binary-profile tests, four trace-analyser tests, and the synthetic pilot.
