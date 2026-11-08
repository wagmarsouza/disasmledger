# VeriMission 8.2 adapter — local additive development

Base: `0ca818a`; its three suites previously ran 100 tests (99 passed, one existing Windows
symlink skip). Keep all existing interfaces, toolchain refinements and independent skill operation.
No installation, publication, live mission changes or real target execution.

## Contract and boundaries

- Export existing declared DisasmLedger grade snapshots into the native 8.2 observation schema.
  Do not copy, fork, replace or embed its reconciliation/digest/review logic.
- Freeze target identity, unit IDs, scope, G0 exclusions and an explicit cycle anchor in a small
  adapter contract. Reuse closure normalization and existing identity/evidence path helpers.
- Project reconstruction maturity only. G4-stock and ambiguous legacy G4 do not establish it;
  project them as ungraded and preserve the original values and uncertainty in the receipt.
- The native fixed denominator uses the declared epoch's non-G0 units. New units or changed G0
  exclusions require an explicit epoch/mission revision, never silent denominator edits.
- Preserve live and closed differences, unmarked changes and caller-declared transition kinds so
  the native reconciler can reject inconsistencies. Do not manufacture evidence, grades or progress.
- Generate new observation/receipt bundles only. Verify them against physical current sources;
  configure that verifier as an explicit mission check with frozen per-cycle artifacts.
- Facts-recorded/used labels and optional claim links pass through without semantic interpretation.
  No model, scheduling, mission revision, reread declaration or claim promotion is automatic.

## Verification

Write failing adapter tests first. Test projection, lossless receipts, source drift, exact output,
legacy ambiguity, fixed exclusions, invalid inputs and read-only verification. Exercise the real
local VeriMission 8.2 in an explicit integration pilot with synthetic fixtures: normal closure,
missing promotion receipt, justified/unexplained regression, live/close mismatch and source drift.
Use the unmodified native engine and inspect its actual refusal/results. Run all repository suites
and prior pilots. Tests establish declared consistency, not grade-gate truth or firmware correctness.
