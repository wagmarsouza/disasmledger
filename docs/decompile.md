# DisasmLedger Decompile

Decompile 0.2.0 orchestrates an evidence-bound reconstruction workflow with Binary Analysis Profile and Renode Bench. It routes identity, inventory, type modelling, transcription, compilation, matching, and differential testing to appropriate external tools. The bundled executable is a read-only scheduling helper.

## Install and invoke

```powershell
npx skills add wagmarsouza/disasmledger --skill binary-analysis-profile
npx skills add wagmarsouza/disasmledger --skill renode-bench
npx skills add wagmarsouza/disasmledger --skill decompile
```

Keep the sibling directories together when copying manually so relative links resolve. Installation does not activate an autonomous job. Ask your agent:

```text
Use decompile with binary-analysis-profile for this authorised binary. Establish its identity, inventory the analysis units, and plan reconstruction using the grade ladder. Use renode-bench where an emulated witness is appropriate. Preserve contradictory results and bound every conclusion to the evidence.
```

VeriMission is an optional mission coordinator. If used, its installed version owns canonical mission state; this skill does not create another mission ledger.

## Tools and requirements

- Python 3.11+ and the standard library run the packaged helpers, tests, and pilots.
- Supply a call-graph export and a grade map in the bundled JSON formats.
- Install only the external tools needed for the task: examples include Capstone, Ghidra/pyghidra, an appropriate cross-compiler, instruction-diff tooling, and Unicorn or Renode.
- The differential helper currently extracts ARM Thumb `.text` with Cortex-M4 compiler defaults. It requires a target-specific `invoke` callable and review of ABI, memory placement, relocations, external references, state, and toolchain flags. It does not include a ready-to-run board or emulator backend.
- Compile flags alone do not establish position independence. The operator must verify relocations and dependencies before executing a relocated blob.

## Evidence levels

| Level | Meaning |
| --- | --- |
| G0 | Discarded or invalid candidate |
| G1 | Decoded instructions and control flow |
| G2 | Described semantic hypothesis |
| G3 | Reconstructed source compiles under the declared toolchain |
| M | Optional instruction/byte match within the compared scope |
| G4-stock | Original observed on declared witnesses |
| G4-recon | Reconstruction compared against original observations on declared witnesses |

Compiling is not a behavioural test. Agreement on witnesses establishes only the comparison exercised. Two witnesses are a minimum structural rule; input sufficiency, positive controls, branch discrimination, and provenance require review.

## Scheduler command

Clone the repository, copy the synthetic templates to your analysis project, and replace them with the actual graph and grades:

```powershell
$scheduler = 'PATH_TO_DISASMLEDGER/skills/decompile/scripts/closure.py'
$project = 'PATH_TO_ANALYSIS_PROJECT'
python -B $scheduler --project $project report --callgraph "$project/analysis/callgraph.json" --grades "$project/analysis/grades.json" --limit 50
```

Exit 0 means the scheduling report was produced; exit 2 means input was rejected. `passed` in this report concerns scheduling input processing. It does not certify a reconstruction. Explicit absolute input paths avoid ambiguity: relative graph/grade paths are resolved against the process working directory in this version.

## Known limitations in decompile 0.2.0

This release publishes the supplied implementation. The following limitations were identified by inspection and targeted checks:

- The methodology distinguishes G4-stock and G4-recon, but the scheduler accepts only G0, G1, G2, G3, and G4. It cannot express that distinction. Keep both evidence types in the project records and do not interpret generic G4 as proof of reconstructed behaviour.
- G0 units remain in scheduler node and pending counts and can appear as testable. Its counts therefore do not implement the methodology's exclusion of discarded candidates from the live denominator.
- Grade-map identifiers absent from the graph still increase `graded`. Reconcile identifiers before interpreting totals; this count can exceed the graph node count.
- A callee without its own adjacency entry is treated as having no recorded callees. Unknown or indirect dependencies can make readiness optimistic. Review graph completeness separately; `coverage_indeterminate: false` only indicates all represented nodes have grades.
- Grades are supplied declarations. The helper does not inspect compile logs, witness provenance, hashes, retractions, or freshness. It does not automatically propagate retractions through external records.
- A G3 closure does not prove linkability, ABI compatibility, or successful execution. Even a G4 closure does not isolate every mismatch to the current function: integration, shared state, memory layout, and bench configuration also matter.

Treat `testable_now` as a candidate queue for review. These limitations are not fixed by the current synthetic test results.

## Package verification

```powershell
python -B -m unittest discover -s skills/decompile/tests -v
python -B skills/decompile/examples/run_pilot.py
python -B -m unittest discover -s skills/renode-bench/tests -v
python -B skills/renode-bench/scripts/differential.py --selftest
python -B -m unittest discover -s skills/binary-analysis-profile/tests -v
python -B skills/binary-analysis-profile/examples/run_pilot.py
```

These tests use synthetic data and fake execution. They do not validate actual firmware, the ARM cross-toolchain, an emulator backend, or hardware.
