# DisasmLedger Decompile

Decompile 2.0 orchestrates an evidence-bound reconstruction workflow with Binary Analysis Profile and Renode Bench. It routes identity, inventory, type modelling, transcription, compilation, matching, and differential testing to appropriate external tools. Legacy closure/presentation executables remain read-only. The optional completion verifier now
invokes approved compiler/executor tools and emits neutral evidence for Control8.4; read
[the new pipeline guide](verified-completion.md) and [release notes](release-decompile-v2.0.0.md).

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

- Python3.11+ and the standard library run legacy helpers. The optional verified-completion
  AST gate and its tests additionally require pycparser (requirements-verified.txt).
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

Exit 0 means the scheduling report was produced; exit 2 means input was rejected. `passed` concerns scheduling input processing. It does not certify a reconstruction. Relative graph/grade input paths are resolved under `--project`; explicit absolute paths are also supported.

## Migration from 0.2.0 to 0.3.0

The input format markers remain `decompile-callgraph-v1` and `decompile-grades-v1`. Output changes to `decompile-closure-report-v2` because the interpretation of counts and G4 changes. Update consumers of report-v1 explicitly.

- Replace legacy `G4` only after reviewing evidence: choose `G4-stock` for original observations and `G4-recon` for reconstruction comparisons. Do not bulk-convert ambiguous labels to G4-recon. Generic G4 remains readable, is listed in `legacy_g4_ambiguous`, and blocks reconstruction closure.
- Only G3 and G4-recon satisfy the reconstruction dependency gate. G4-stock does not imply reconstructed source exists. `totals.stock_g4` and `totals.recon_g4` replace the old ambiguous `proven_g4` count.
- G0 stays in `inventoried_nodes` and `excluded_g0`, but is removed from live `nodes`, `graded`, pending counts, and queues. A caller still referencing G0 remains blocked until the graph inconsistency is reviewed. An all-G0 inventory has `coverage_applicable: false` (N/A).
- Remove or reconcile grade entries not represented in the graph; they now cause a structured GRADES error rather than inflating totals.
- Supply explicit adjacency for every reviewed function. An absent entry or `null` means unknown; `[]` declares a leaf. List unresolved indirect callers in `unknown_calls`. These nodes and their dependent closures are blocked.
- Add the boolean `inventory_complete: true` only when the inventoried universe has been reviewed. Omission defaults to false. Coverage remains indeterminate with incomplete inventory, ungraded nodes, unknown adjacency/calls, or ambiguous legacy G4. This flag records a declaration, not an automated proof of graph completeness.
- Update invocations that relied on the current working directory: relative inputs now resolve under `--project`.

The iterative closure calculation supports large call chains without Python recursion. Cycles remain conservatively unresolved. Duplicate graph edges do not multiply caller leverage. A downgraded callee blocks dependent closure when the report is regenerated.

## Remaining evidence boundaries

Grades are declarations: `grades_are_declared: true` and `evidence_verified: false`. The scheduler does not inspect compile logs, witness hashes, controls, timestamps, or retractions in external records. Re-run it after updating grades; review the underlying evidence independently.

`done_g3_plus` counts declared G3/G4-recon units and is not a mission completion measure. `ft_g3_closed` and `ft_g4_closed` count units with matching declared callee closure, excluding each unit's own grade. An ungraded leaf has empty callee closure but is not verified. Treat `testable_now` as a reconstruction candidate queue, not an executable certification decision; witness selection still requires review.

A G3 closure does not establish linking, ABI compatibility, or execution. G4-recon closure does not isolate every fault to the current function: shared state, memory layout, dependency applicability, and bench setup also matter. No report promotes a grade or establishes universal equivalence.

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
