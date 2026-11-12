# Decompile 3.0 — generic gates, explicit target profiles

Decompile3.0 component release. Publishing does not install tools or migrate a mission.
The historical completion/closure/census/preservation
commands remain. This layer adds a generic contract and reuses the existing C execution engine,
canonical binary identity helper and native Control8.4 measurement/audit protocol. It introduces
no second ledger, queue, background loop or automatic mission revision.

## Categories and the claim ceiling

| Fixed category | Required gates | Successful claim | Reconstructed counter |
| --- | --- | --- | --- |
| `analysis` | D-a, D-b, D-d | Traceable analytical artifact under the declared review | No |
| `mechanical-translation` | D-a, D-b, D-d, D-e | Constructible mechanical representation | No |
| `recompilable` | D-a, D-b, D-d, D-e | Structured artifact builds under the declared target recipe | No |
| `independent-validated` | All six | Independent reconstruction validated within the stated scope | Yes, only after native `close` |

Each receipt includes all six statuses, category satisfaction, assumptions and observables.
Non-required gates are N/A in the detailed receipt and `unknown` on the native measurement wire.
Unknown/N/A never becomes pass. A unit is qualified only if its entire dependency closure is
also qualified. Mutually dependent groups can qualify together, but no excluded/missing/failed
dependency is silently forgiven. The caller's own construction and validation still have to pass.

The gate names are universal requirements, not a universal test implementation. D-b needs a
source-bound representation review; it does not equate absence of `r0` or `goto` with structure.
D-d detects declared unresolved operations and profile failure markers, with physically justified
exceptions. A marker can also be legitimate program data. Neither rule detects all fake bodies.
D-c depends on an adequately reviewed complete original call graph; an omitted edge can escape
an inadequate inventory. D-e needs actual construction, not a pre-existing image copied into a
report. D-f binds original AND reconstructed artifact, and reports only the configured domain.

## Files to prepare in the authorized project

1. Existing `binary-target-v1`, `binary-unit-v1`, neutral `verimission-universe-v1` and complete
   `decompile-callgraph-v1` manifests. Preserve physical identities and G0 reasons.
2. A `decompile-target-profile-v1` based on `assets/profiles/*.json`. Fix architecture, ISA,
   endianness/address units, language/backend, dependency/platform boundary, reviewer declarations,
   construction format and validation method/assumptions/observables before execution.
3. One source-bound `decompile-recovery-review-v1` per live unit: category, representation,
   body completeness, unresolved operations, exact dependencies and marker justifications.
4. A `decompile-qualification-contract-v1`, pinning profile, target, universe and backend config
   by `{path,sha256}`. Paths are project-relative; only output folders may initially be absent.
   `input_patterns` must cover all relevant source, headers, linker files, support inputs,
   original, corpora, reviews, manifests, profile/config and verifier resources. Do not scan output
   folders or `.harness`. Complete relevant-input disclosure remains the adapter author's duty.

Templates have placeholder hashes and paths. They are deliberately not executable defaults.
The profile IDs are examples, not a promise that the associated toolchain is installed/tested.
For a new target, create an explicit reviewed profile; never guess architecture from a filename
or automatically choose a looser profile after failure.

## C compatibility backend

`backend: c-source-v1` currently supports `independent-validated` only. Its backend config is the
existing `disasm-completion-config-v1` from [verified completion](verified-completion.md). Keep
the C structural review and new generic recovery review; they have different schema contracts.
Compiler, preprocessor and executor are explicit argv recipes with executable/resource hashes.
They run without a shell, with finite timeouts, captured logs and separate healthy/candidate/
known-bad execution. No tools are installed or discovered as a substitute after failure.

ELF checks enforce class, endianness and machine. CPU extensions, hard/soft-float ABI, calling
convention, linked callee implementations, memory/peripheral model and permitted undefined
behavior must be enforced by the approved compiler/executor and complete build inputs. ELF
machine alone does not prove ABI compatibility. `process-image` proves selected-process image
origin under the trusted runner; use `pc-trace` with suitable instrumentation for firmware flows.
Neither mode independently proves absence of a malicious runner or hidden host delegation.

Use a profile-specific corpus size and distinct actual inputs. The floor of two inputs and an
effective known-bad control is a minimum sanity condition, not adequate coverage for every unit.
Required scenario labels must be present, but are not branch-coverage measurements. Every
observable (return, termination, memory, exceptions, I/O, etc.) must actually be supplied by the
runner. Equal faults, omitted vectors, old-run/image proofs, unresolved calls and missed controls
cannot qualify. Widen scope explicitly when a unit's risks require stronger evidence.

## Other languages and methods: approved external verifier

`external-v1` executes a pinned argv, never imports an arbitrary existing report or scalar count.
The config `decompile-external-verifier-v1` fixes executable hash, static project resources,
entrypoints, witness references and finite timeout. Differential witnesses are fixed beforehand;
formal/symbolic methods use an empty witness map. The fresh request path and fresh output path
are supplied in `DECOMPILE_QUALIFICATION_REQUEST` and `DECOMPILE_QUALIFICATION_REPORT`.

Request: `decompile-adapter-request-v1`, fixed run/context/category/profile/original/units, current
source identities and required gates. Response: `decompile-adapter-observation-v1`, exactly one
row per live unit, explicit six statuses, physical artifacts and fresh validation scope.
The executable fixture in `tests/external_qualification_fixture.py` documents the wire format;
it is a synthetic protocol test, NOT a real LLVM validator or equivalence prover.

For D-e, the verifier supplies a constructed artifact and a `decompile-build-binding-v1` linking
unit/run/source/artifact/profile and successful construction exit code. For D-f, it supplies a
proof certificate, distinct negative candidate, control binding and `decompile-validation-context-v1`
linking both original and candidate, constructed artifact, method, assumptions, observables and
fresh command context. Differential case IDs must match the predeclared physical corpus exactly;
formal/symbolic verdict must be `equivalent`, never `unknown`. Controls must be fresh, healthy
must pass and known-bad must be rejected. External reports are always freshly executed; external
cache reuse is not supported. Core recomputes the dependency-closed count itself.

The core checks protocol integrity and bindings; the approved verifier must really perform the
construction/proof/control work and verify its own detailed certificate/logs. There is no bundled
universal proof checker or defense against a deliberately lying approved executable/reviewer.
Do not describe a synthetic protocol receipt as actual proof of a target's equivalence.

## Native Control8.4 adoption, use and migration

Do not modify an active project's `.harness/state.yaml`. Use a newly authorized mission or the
existing explicit mission-revision workflow. Keep original universe, exclusions and denominators;
new gate names/categories are not a reason to silently relabel past results. See the native
harness's `--help` and `references/v84-measurements.md` for its revision and command contracts.

Configure criteria M (measurement) and A (audit) with the SAME argv:

```json
["python", "PATH_TO_SKILL/scripts/qualification.py", "--project", "PROJECT_ROOT", "--contract", "analysis/qualification.json"]
```

Set `measurement_policy.required_gates` to `["D-a","D-b","D-c","D-d","D-e","D-f"]`.
Protect contract/profile/backend config and executable verifier resources by hash. Include all
relevant project input patterns. Use pinned roles `qualification_contract`, `qualification_profile`,
`witnesses`, `negative_source` (C) or `negative_candidate` (external), plus `verifier_context` (C)
where applicable. Freeze external negative controls as approved input artifacts, rather than
regenerating a different negative for each run. Keep audit cadence/sample and acceptance
denominator explicit. A changed profile/contract/category refuses previous evidence and needs
explicit native revision, never an `approved: true` flag inside an adapter file.

The harness provides `VERIMISSION_MEASUREMENT_*` context, output/previous refs, and frozen audit
selection. A successful `check` records observations; it does NOT seal/promote the count. Run
native `close`, respect mandatory boundary reviews and use native `measurement-report` or
`census_bars.py --harness ...` to read currently verified/pending/stale results. Do not manually
edit a competing TSV. Preserve G4-stock and G4-recon separately. Revalidation after repair is
not new work. A selected audit forces backend reexecution plus controls and complete recount.

Current proofs directly bind original image, transitive dependency sources, platform files,
project-local tool resources and all resulting evidence. Native live views detect their drift.
For system tools outside the project, identity is rechecked when executing; an unchanged JSON
receipt is not continuous monitoring of a global executable. Include a project-local pinned
toolchain or an approved freshness check if immediate global-tool drift detection is required.
Likewise, adoption must protect the qualification scripts and canonical identity helper; moving
or editing those tools requires revalidation. No polling or background authority is introduced.

## Commands and test limits

Without installing a skill, ask the agent to read the extracted `SKILL.md` and apply it to the
authorized project. There is no cross-agent universal slash command. CLI observation exit0
means a well-formed complete measurement; its count may still be zero. Exit2 means incomplete,
timeout or rejected integrity/protocol. Always inspect gates and receipts, not only exit status.

```powershell
python -B -m unittest discover -s PATH_TO_SKILL/tests -v
python -B PATH_TO_SKILL/examples/run_qualification_pilot.py --harness PATH_TO_CONTROL84/scripts/harness.py
python -B PATH_TO_SKILL/scripts/qualification.py --help
```

The pilot creates/removes only its temporary mission. Without `--compiler`, compiler/executor
are synthetic protocol fixtures. On Linux x86_64, `--compiler /usr/bin/gcc` adds actual native
compilation and host process comparisons. Neither is ARM firmware, hardware, or actual formal
equivalence qualification. See the delivery validation report for what was actually run.
