# Toolchain refinements — local development preview

No installation, publication, live project migration or external-engine setup has been performed.
Development is isolated on `feature/toolchain-refinements`. Decompile is 0.4.0-dev and Renode Bench
is 1.2.0-dev; these are local preview labels, not release tags. Binary Analysis Profile is unchanged.

## What changed

| Component | Additive behavior | Preserved boundary |
| --- | --- | --- |
| Decompile closure | Optional `--provenance` binds target/export/grades/evidence bytes and producer context; reports declared edge origins and annotation coverage | No grade promotion, unknown-call removal, engine execution or changed legacy output without the option |
| Decompile routing | Focused angr guidance for residual indirect-edge questions, with explicit uncertainty and budget | Reuse external exporters; no bundled angr engine or new graph/inventory system |
| Bench capability assessor | Target/version/configuration-specific supported/unsupported/unknown requirements with hashed evidence and eligibility reasons | No runtime feature authentication, invocation authorization, automatic selection or fallback |
| Differential comparison | Optional `executor_context` assesses before compilation and around each invocation; drift refuses the contextual result | Existing bool API, compile/blob handling and two-witness comparison remain available |
| Documentation | Clarified Capstone boundaries, VFP configuration, cross-build identity and non-exclusive mismatch causes | Existing profile identity/revalidation rules are reused, not implemented twice |

## Commands and formats

Read [graph provenance](../skills/decompile/references/graph-provenance.md) for the actual
`decompile-provenance-v1` schema, producer binding and optional closure command. Read
[executor capabilities](../skills/renode-bench/references/executor-capabilities.md) for
`bench-executor-capabilities-v1`, `bench-requirements-v1`, escalation rules and differential use.
The example JSON files are drafts requiring actual local evidence; they do not claim tool support.

```powershell
python -B skills/decompile/scripts/closure.py --project PROJECT_ROOT report --callgraph analysis/callgraph.json --grades analysis/grades.json --provenance analysis/provenance.json
python -B skills/renode-bench/scripts/executor_capabilities.py --project PROJECT_ROOT assess --manifest bench/executor.json --requirements bench/requirements.json
python -B examples/run_toolchain_pilot.py
```

The pilot uses only temporary synthetic data and a fake invocation function. It demonstrates a
blocked peripheral case and a separate CPU-only unit/case, never lowers a unit's requirements to
force a pass, and confirms changed input invalidation. It does not run an emulator or firmware.

## Reproduce verification

Run the repository's existing suite commands, including the new tests they discover:

```powershell
python -B -m unittest discover -s skills/binary-analysis-profile/tests -v
python -B -m unittest discover -s skills/renode-bench/tests -v
python -B -m unittest discover -s skills/decompile/tests -v
python -B skills/binary-analysis-profile/examples/run_pilot.py
python -B skills/decompile/examples/run_pilot.py
python -B skills/renode-bench/scripts/differential.py --selftest
python -B examples/run_toolchain_pilot.py
```

Skill metadata is checked with the host's skill validator in an explicit PyYAML environment; no
runtime PyYAML dependency was added to these stdlib helpers. Exact outcomes and limits are recorded
in [the verification report](toolchain-refinements-verification.md).

## Scope not added

The native census/digest/reconciliation engine stays in VeriMission 8.2. This change does not copy
it or add a specialist census exporter, schedule or ledger. It does not revise missions, upload
artifacts, install tools, authenticate code authorship, prove arbitrary CFG completeness, test
actual engine feature support or establish equivalence on real hardware. Those remain separate,
explicitly scoped work. No PHI, firmware, credentials or private project data enters this preview.
