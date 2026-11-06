# DisasmLedger v2.0.0 — Correct reconstruction scheduling

Decompile 0.3.0 corrects the scheduler's distinction between original observations and reconstructed-code comparisons, dependency completeness, and inventory counts.

- G4-stock and G4-recon are distinct. Only G3/G4-recon satisfy reconstruction dependencies; legacy G4 is ambiguous and blocks closure.
- G0 candidates are excluded from live counts and queues; references to them still block callers.
- Grades outside the graph are rejected. Missing/null adjacency and unresolved indirect calls block dependent readiness.
- Inventory completeness must be explicitly declared; unknown grades, dependencies, and legacy G4 retain indeterminate coverage.
- Deep call graphs use iterative closure. Relative paths resolve under --project.
- Added 19 regression tests, including a 2,500-function chain, while retaining existing workflows and the read-only contract.

## Migration

Output is now `decompile-closure-report-v2`. Input markers remain v1. Review legacy G4 evidence before choosing G4-stock/G4-recon; declare unknown calls and inventory completeness; update report consumers and relative CLI paths. See the [migration guide](https://github.com/wagmarsouza/disasmledger/blob/v2.0.0/docs/decompile.md#migration-from-020-to-030).

## Install

```sh
npx skills add wagmarsouza/disasmledger --skill binary-analysis-profile
npx skills add wagmarsouza/disasmledger --skill renode-bench
npx skills add wagmarsouza/disasmledger --skill decompile
```

The ZIP contains all three skills and documentation. `evidence_verified`, `semantic_truth_verified`, and `promotion_authorized` remain false: the scheduler reasons over declared grades and graph structure, not authenticated evidence. Synthetic tests do not establish real firmware, emulator, compiler, or hardware correctness.
