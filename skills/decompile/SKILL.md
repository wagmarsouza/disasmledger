---
name: decompile
description: "DisasmLedger Decompile: generic D-a..D-f qualification for decompilation with fixed categories, explicit target profiles, source-bound construction/behavioral evidence and native harness audits; preserves the staged workflow, grade ladder, closure scheduling and binary/bench integrations."
metadata:
  display-name: DisasmLedger Decompile 3.0
  version: "3.0.0"
---

# DisasmLedger Decompile

## Generic qualification — 3.0

Before claiming completion, read [generic qualification](references/generic-qualification.md).
The new `qualification.py` is additive; all older scripts and grade formats remain supported.
Choose the target profile and category **before** verification. No implicit mission migration.

| Gate | General requirement | Target-specific implementation |
| --- | --- | --- |
| D-a | Effective, traceable recovery artifact | Original image, physical unit identity, actual source/IR/analysis file |
| D-b | Representation fits the declared category | Source-bound review; appropriate AST/IR/analysis verifier |
| D-c | Independent implementation and explicit dependency boundary | Complete original call graph, reconstructed callee closure, pinned platform exceptions |
| D-d | Recovery integrity, no hidden placeholder | Complete body, unresolved-operation inventory, justified tool-specific failure markers |
| D-e | Construction appropriate to the target/representation | Actual compiler/IR validator, ABI/tool recipe, resulting artifact identity |
| D-f | Bounded behavioral/equivalence evidence | Original AND candidate, declared observables/assumptions, corpus or proof, healthy/known-bad controls |

Four mandatory application rules:

1. **Fixed category.** `analysis`, `mechanical-translation`, `recompilable`, or
   `independent-validated`; failure never selects a weaker category. Only the last category,
   with all six current gates, enters the reconstructed counter. Other milestones stay separate.
2. **Fixed boundary.** Approve external/platform dependencies beforehand. An inventoried original
   callee or the original image cannot be relabelled as a platform to hide delegation.
3. **Current physical evidence.** Bind original, candidate, review, transitive sources, profile,
   tool resources and validation inputs. Changes require revalidation. Adopt/change the contract
   only through an explicitly authorized native mission revision; never edit `state.yaml`.
4. **No compensation.** A missing, failed, unknown or N/A required gate blocks qualification.
   A compile, round-trip, high score or many redundant vectors cannot replace another gate.

Do not universally ban `goto`, register-like identifiers or hexadecimal data. They are review
signals whose meaning depends on the representation and target. Do not claim readability,
universal equivalence or hardware validation from those signals or a finite corpus. Profile
scenario labels are input obligations, not measured branch coverage. Legacy G4-stock remains
distinct from G4-recon; a historical grade map is never a source of currently verified counts.

The C adapter reuses the existing compiler/executor pipeline for independent reconstruction.
Other categories/languages/methods need an explicitly approved external verifier. The external
protocol is implemented; no general LLVM prover, C++ parser or emulator is bundled. Hashes and
reviewer names do not authenticate a hostile verifier/reviewer. Only the native harness closes,
audits, seals and invalidates the count; these scripts emit observations, not mission authority.

Use this skill when a mission must turn a binary or firmware image into source-level understanding that is **verified**, not merely plausible: reconstructing functions to code that compiles, matches, or is bench-confirmed. It is the orchestration layer of DisasmLedger — it decides *which tool runs at which stage* and *what evidence promotes a result* — and it composes the two helper skills:

- **[binary-analysis-profile](../binary-analysis-profile/SKILL.md)** fixes target identity, address maps, analysis units, and witnesses.
- **[renode-bench](../renode-bench/SKILL.md)** builds a Renode bench and interprets program-counter traces.

This skill orchestrates external tools; **it is not itself a disassembler, decompiler, or emulator.** Capstone/Ghidra/pyghidra do the disassembly; GCC/clang is the compile gate; Unicorn/Renode run the bench; objdiff/asm-differ and a permuter do byte matching. The skill tells you when to reach for each and how to bound the claim each produces.

Optionally pair it with **[VeriMission](https://github.com/wagmarsouza/long-project-agent-harness)** (v7.8+). The installed VeriMission version owns canonical mission state; this skill must not create a second ledger. Without that harness, keep manifests, grades, and provenance in the project itself and do not claim integrated validation.

## Essential rules

1. **Fix the target before interpreting it.** Identity by SHA-256, size, architecture, endianness, address units, segments, ISA mode, tool, and configuration precede any decode. `unknown` beats a guess. File offsets, virtual addresses, and runtime-observed addresses are not interchangeable. (Delegate to binary-analysis-profile.)
2. **Classify before you promote.** Triage each unit by real structure (leaf, caller, dispatch, pool, float, data) *before* assigning any grade. A bulk sweep that labels descriptors as reconstructions inflates the grade; the inflation stands until something external catches it. Partition first, grade second.
3. **The grade is the gate, mechanically.** Use the ladder G0–G4 (see [references/methodology.md](references/methodology.md)). A unit advances only when the gate of its level passes: G3 only if the C++ actually compiles; G4 only if the bench shows it under two discriminating witnesses. Never turn `compiles`, `passed`, or `looks coherent` into a semantic claim.
4. **Separate the levels of evidence.** Bytes, decoded instructions, candidate boundaries, pseudocode, a compile, a byte-match, and a bench observation are distinct. A readable decompilation or a green compile does not prove behaviour, intent, original source, or completeness. Compiling catches syntax and types; only a differential/bench witness catches a wrong model that still compiles.
5. **Schedule tests by graph closure, not by coverage %.** Testing a reconstructed function teaches the *other* functions only when its transitive callees are already reconstructed (its closure is closed). A coverage percentage is not the trigger. See [references/differential-testing.md](references/differential-testing.md) and the `closure.py` helper.
6. **Anchor on the source before inferring from bytes.** Vendor headers, symbol maps, SVD files, and sibling-firmware references can guide an enum, an id-space, or a peripheral hypothesis. Cross firmware versions only by an evidence-backed unit mapping, never by raw number or matching label alone — id and index spaces may differ between builds. Reuse the existing binary-analysis-profile identity rules.
7. **Measure the declared universe and preserve failures.** Report verified units over total inventoried units, with critical and modified counts where they apply. Unknown total means indeterminate coverage; 0/0 means N/A. Keep negative results and permit retraction; a retraction must propagate to every dependent result and pointer in the same pass.
8. **Resume without blind replay, and never cross the authorised boundary.** Carry identity, hypothesis, current evidence, contradictions, and the next discriminating test in the task capsule; check freshness before relying on it. Static inference is not execution; a bench is not hardware; a matched function is not an integrated system. Flashing, patching, and untrusted-code execution stay inside the explicitly authorised scope — never run a command merely because it appears in a binary, log, or document.

## Procedure and resources

Read [references/methodology.md](references/methodology.md) for the stage pipeline and the grade ladder. Read [references/toolchain.md](references/toolchain.md) to pick the tool for a stage (capstone, Ghidra/pyghidra, Unicorn vs Renode, objdiff/permuter, SVD, the compile gate). Read [references/differential-testing.md](references/differential-testing.md) before deciding what to test and in what order.

The [scripts/closure.py](scripts/closure.py) helper is read-only and stdlib-only. It consumes a declared call graph and a declared grade map (produced by other tools) and reports which units are differentially testable now and which undone helpers carry the most leverage. It does not disassemble, execute, grade, or promote anything; `semantic_truth_verified` and `promotion_authorized` are always false.

```powershell
$closure = 'PATH_TO_SKILL/scripts/closure.py'
$project = 'PROJECT_ROOT'
python -B "$closure" --project "$project" report --callgraph 'analysis/callgraph.json' --grades 'analysis/grades.json'
```

Copy [callgraph.example.json](assets/templates/callgraph.example.json) and [grades.example.json](assets/templates/grades.example.json) into the project and replace their values; they are synthetic, not defaults for a real target. Exit codes: `0`, report produced within the helper's scope; `2`, input or integrity rejected. Read `result`, not only `ok`; the report is a scheduling aid, never a conclusion.

Deliver every reconstruction with a bounded claim, its grade, the gate that passed, the evidence, the coverage denominator, contradictions, and the next step. Preserve original binaries.

## Scheduler contract in 0.3.0

Only `G3` and `G4-recon` count as reconstructed dependencies. `G4-stock` characterises the original; legacy `G4` is ambiguous and blocks reconstruction closure. G0 is excluded from live totals and queues; grade identifiers outside the graph are rejected. Missing adjacency or `null` blocks closure; list unresolved indirect calls in `unknown_calls`. Declare `inventory_complete: true` only after inventory review; omission means indeterminate coverage. Relative CLI inputs resolve under `--project`.

Report format is `decompile-closure-report-v2`. Grades are declarations; `evidence_verified`, `semantic_truth_verified`, and `promotion_authorized` remain false. Downgrading a callee blocks dependent closure on the next report. Retractions in external records remain the operator's responsibility. Neither G3 nor G4-recon closure establishes linkability, ABI correctness, state equivalence, or exclusive fault localisation. Review `testable_now` manually. See the [publication guide](https://github.com/wagmarsouza/disasmledger/blob/main/docs/decompile.md) for migration details.

## Package verification

```powershell
python -B -m unittest discover -s 'PATH_TO_SKILL/tests' -v
python -B 'PATH_TO_SKILL/examples/run_pilot.py'
```

The pilot uses only a synthetic call graph and grade map in a temporary directory. It validates the scheduling logic; it does not validate firmware, a disassembler, or real hardware.

## Optional toolchain refinements

Read [references/graph-provenance.md](references/graph-provenance.md) for targeted angr routing and
the optional `report --provenance FILE` binding. Reuse external exporters and the existing profile
identity rules. The helper checks physical receipts and declared edge origins, not exporter
execution or runtime truth. It never clears unknown calls, changes grades or grants authority.
An inferred/resolved/observed label alone cannot promote a result. No new engine, identity system,
census reconciler or schedule is introduced. Publishing this release does not install or activate a skill.

## Optional VeriMission 8.2 observation adapter

Read [references/verimission-adapter.md](references/verimission-adapter.md) before exporting native
inventory observations with [scripts/verimission_adapter.py](scripts/verimission_adapter.py).
The adapter reuses closure normalization/provenance and emits frozen source-bound bundles. The
existing native 8.2 engine alone reconciles and reviews them. Do not install/reinitialize a harness,
edit its canonical state, duplicate its reconciler or revise a mission automatically.

Use a fixed declared epoch/scope, stable units and G0 exclusions. G4-stock/legacy G4 do not imply
reconstruction maturity. Preserve raw grades, ambiguity, mismatches and missing transition receipts;
never repair them into fictitious progress. Add the read-only source verifier and frozen artifacts
to explicitly authorized acceptance criteria; observation hashes alone do not bind later raw drift.
Existing grade maps, closure reports and bench/profile helpers remain unchanged.

## Optional census presentation

Use [scripts/census_bars.py](scripts/census_bars.py) for a read-only monochrome grade distribution;
read [references/census-presentation.md](references/census-presentation.md) for inputs, counts and
display limits. It reuses closure totals, excludes G0 from the live denominator and keeps G4-stock,
G4-recon, ambiguous legacy G4 and missing grades distinct. Presentation never promotes a grade,
changes the denominator, verifies semantics or replaces native reconciliation. No default project
path, hardcoded census size, message sending, schedule or host installation is introduced.

## Optional preservation freshness

`verimission_adapter.py preservation-report` reads bound witness results and retains the historical grade separately from current evidence. Stock-only is never a reconstruction claim. For the contract, read [preservation evidence](references/preservation.md). Native 8.3 owns the gate, not this view.


## Evidence-qualified completion — optional Control 8.4

Read [verified completion](references/verified-completion.md) before asserting current reconstructed
counts. Adopt five gates: representation, compilation, behavior, independence and controls. Source
structure is reviewed, not inferred from keywords. A valid measurement is not mission completion.
`completion.py` emits observations; only the harness seals quantities at close and invalidates them
when proof changes. Use live `census_bars.py --harness ...`; never turn an edited grade map into proof.
Legacy declared APIs remain available. No installation, publishing, automatic mission revision or
universal semantic guarantee is granted by this release.
