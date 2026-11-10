# Optional preservation evidence for VeriMission 8.3

The original `differential(...) -> bool` API is unchanged. Its new optional `preservation` argument
exports a complete, current `verimission-results-v1` file and requires explicit reset before every
witness. This is not emulator dispatch or grade promotion. The helper has no VeriMission dependency.

Pass exactly these fields:

```python
preservation = {
    "project": project_root,
    "output": project_relative_fresh_report_path,
    "unit": stable_unit_id,
    "run_id": os.environ["VERIMISSION_RUN_ID"],
    "context_sha256": os.environ["VERIMISSION_CONTEXT_SHA256"],
    "references": {
        "stock": {"path": "evidence/stock.bin", "sha256": stock_sha256},
        "witnesses": {"path": "analysis/witnesses.json", "sha256": witnesses_sha256},
        "executor": {"path": "bench/executor.json", "sha256": executor_sha256}
    },
    "reset": explicit_reset_callable,
    "reset_policy": "REPLACE with the actual independent-state policy"
}
```

`stock` and `witnesses` are required physical references; other reference roles are optional but
should bind relevant executor/toolchain/ABI/context resources. Witnesses must be a JSON list
matching the in-memory cases (including expectations); every case needs a unique stable `name`.
No target-specific address, denominator or firmware rule is included. Keep the unit ID stable.

The neutral case ID is `UNIT::name`. `observed` contains the actual invoke outputs; each case
contract binds reference hashes, witness identity and the declared reset policy. An expected
register return with wrong declared memory effects is a failed witness. Only observables in the
case contract are compared; do not infer unobserved side effects, all-input equivalence or hardware
correctness. Use an appropriate clean-return trap and resource limits in the existing invoke contract.

The caller's reset and invoke implementations are not authenticated. Bind their source/configuration
as protected/context files and include reconstructed source/blob, helpers, ABI, layout and relevant
globals in the native engine's input manifest. A context declaration does not prove an executor
honored it. Missing capabilities, source drift or a reset error must remain incomplete evidence.

Reference hashes are checked before reset and before final export; results never overwrite an
existing file. An exception before completion emits no successful result. The native engine
must bind the writer to an approved check, input hashes, fresh run ID and current context.

The read-only decompile view can inspect an existing report. Run this from the decompile skill folder (or adjust the script path in the complete repository); the renode-bench standalone ZIP does not install a sibling skill:

```text
python scripts/verimission_adapter.py --project /project preservation-report --callgraph analysis/callgraph.json --grades analysis/grades.json --results reports/current.json
```

That view retains historical grades, shows witness mismatch/staleness and keeps stock-only units
separate. It never reconciles inventory, changes grades, authenticates an execution, or authorizes
a reconstruction claim. G4-recon history and current proof freshness are separate axes.

The repository's `examples/run_preservation_pilot.py --harness /path/to/v8.3/scripts/harness.py`
uses the real native gate with a fake invoke and synthetic nonexecutable reference. It validates
control integration only, not a real CPU, Renode/Unicorn capability or real firmware behavior.
