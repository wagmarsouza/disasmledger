# DisasmLedger — Decompile 3.0

Decompile3.0 introduces target-neutral qualification criteria while preserving the existing
workflow and APIs. The skill ID remains `decompile`; metadata version is `3.0.0`, component tag
`decompile-v3.0.0`. Older component and repository releases remain available. Publishing or
extracting this release installs nothing and does not migrate an existing project.

## Downloads

- [Standalone Decompile3.0](https://github.com/wagmarsouza/disasmledger/releases/download/decompile-v3.0.0/decompile-3.0.0.zip)
- [Complete DisasmLedger](https://github.com/wagmarsouza/disasmledger/releases/download/decompile-v3.0.0/DisasmLedger-Decompile-3.0.0.zip)
- [Usage instructions](https://github.com/wagmarsouza/disasmledger/releases/download/decompile-v3.0.0/INSTRUCOES_DE_USO.md)
- [Public validation receipt](https://github.com/wagmarsouza/disasmledger/releases/download/decompile-v3.0.0/PUBLICATION_RECEIPT.json)
- [SHA256 checksums](https://github.com/wagmarsouza/disasmledger/releases/download/decompile-v3.0.0/SHA256SUMS.txt)

The standalone archive includes the canonical binary identity helper as a distribution resource;
it is not a separately maintained identity engine. The complete archive also includes unchanged
`renode-bench` and `binary-analysis-profile`. External compilers, emulators and proof engines are
not bundled or installed. Existing local qualification ZIPs are retained; public ZIPs update the
documentation and release metadata without changing qualified executable semantics.

## Six generic requirements, target-specific checks

| Gate | Requirement |
| --- | --- |
| D-a | Effective recovery artifact bound to the original and physical unit identity |
| D-b | Representation appropriate to the category declared before verification |
| D-c | Independent implementation and explicit, closed dependency/platform boundary |
| D-d | Complete recovery with unresolved operations/placeholders disclosed and reviewed |
| D-e | Actual construction appropriate to the target, representation and approved recipe |
| D-f | Bounded behavioral/equivalence evidence binding original AND candidate, with controls |

Four application rules remain mandatory: fix the category before evaluation; approve external
dependencies/platforms beforehand; use current physical evidence and revalidate after drift;
never compensate one missing/failed/unknown/N/A required gate with a score from another.

`analysis`, `mechanical-translation` and `recompilable` remain separate milestones. Only
`independent-validated` with all six current gates and a qualified dependency closure can enter
the reconstructed counter, and only the native harness can seal that quantity at `close`.
Register names, `goto` and hexadecimal data are review signals, not universal lexical bans.
Read the [full qualification guide](../skills/decompile/references/generic-qualification.md).

## Commands and adoption without installation

In an extracted standalone folder, with the declared Python dependencies already available:

```powershell
python -B scripts/qualification.py --help
python -B -m unittest discover -s tests -v
python -B examples/run_qualification_pilot.py --harness C:/tools/harness_v8.4/scripts/harness.py
```

Ask the agent to read `SKILL.md` explicitly. There is no universal slash command. Adapt the
templates in `assets/profiles/` and `assets/templates/`; placeholder hashes, paths, assumptions
and reviewer names are not production defaults. The C backend reuses `completion.py` for
independent reconstruction. Other categories/languages/methods require an explicitly approved
external verifier that actually performs construction and verification; the protocol is not a
bundled universal LLVM/C++ prover.

For native [Control8.4](https://github.com/wagmarsouza/long-project-agent-harness/releases/tag/v2.4.0-rc.1),
adopt M/A measurement/audit criteria, gates D-a..D-f, protected files, pinned roles and explicit
budgets only in an authorized new mission or explicit revision. Never edit `state.yaml` directly
or treat an edited grade TSV as proof. The harness owns the universe, closure, denominator,
close, audit hold and historical credit; decompile emits evidence observations. Source/original/
dependency/platform/tool-resource drift invalidates the relevant current evidence. Native live
bars retain declared/verified-now/pending/stale and G4-stock/G4-recon separation. Revalidation
after repair is not new work. Existing 8.2 observation/legacy helpers retain their original scope.

## Executed qualification and evidence ceiling

Qualified runtime source: `ed44fabc20fe8211cc6c78bdda0ab65542a8d110`. Windows/Python3.12 and
Ubuntu/WSL/Python3.14 each passed all167 Decompile cases (123 preserved +44 new), plus40 Renode
and25 identity cases, with one existing Windows symlink-permission skip and no Linux skip.
The actual isolated ZIP passed167 cases again and a relocated native-harness integration pilot.
An actual GCC/native ELF x86_64 process-comparison pilot passed, including a discriminating
negative, close, original/source freshness, selected reexecution and repair without new-work credit.
Three targeted guard inversions were detected after healthy baselines; this is not a global
mutation score. Official skill validation, resource parity, manifest/CRC/SHA checks also passed.

The native pilot initially exhausted the synthetic fixture's 10s compiler cap. The diagnosed
native-only tool/check budgets were made explicit and finite; all acceptance gates and controls
remained. A Windows legacy pilot initially produced no complete observation; its unchanged
repeat passed. Those incomplete attempts were not converted into successful measurements.
Local raw logs and machine-specific paths are excluded from public assets. The public receipt
distinguishes the qualified runtime, publication commit and public artifact hashes. Hosted CI,
when run, is separate evidence and must be assessed from its actual outcome.

Finite cases/scenario tags do not prove branch coverage, universal equivalence, readability,
hardware fidelity or honest behavior by a malicious approved verifier/reviewer. ARM/IR examples
validate configuration structure, not a real ARM firmware or LLVM equivalence proof. Complete
dependency disclosure, target ABI/memory models and real verifier work remain trusted boundaries.
System tools outside the project are rechecked at execution, not continuously monitored by a
nested receipt. Use an explicit project-bound freshness check when that is required.

## Prior releases and rollback

Use `decompile-v2.0.0` and its original assets to reproduce the previous component release.
Publishing3.0 does not overwrite those tags/assets. A consuming mission must review its own
adoption/rollback explicitly; changing a package cannot silently rewrite its recorded contract.
