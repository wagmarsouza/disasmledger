# Optional versioned executor capability gate

Local development preview; no emulator is installed, selected or started by this assessor.
The trace analyzer and legacy `differential(...) -> bool` calls remain unchanged. The new gate is
opt-in and stdlib-only. It evaluates declarations and physical receipt freshness, not real engine
capability or permission. Use the existing binary profile for target identity and address maps.

## Contracts

Copy `assets/templates/executor-capabilities.example.json` and `executor-requirements.example.json`.
Replace every placeholder using actual evidence from the authorized bench. The templates start
with unknown capability; they are not an operational default or a claim that a tool was tested.

`bench-executor-capabilities-v1` requires:

- `target_sha256`: the existing profile's binary identity.
- `executor`: name, actual version, CPU model, and full relevant configuration object. Record
  platform/map, hooks, injections, initial-state policy and relevant toolchain settings here or as
  explicit evidence dependencies. Do not put credentials or private transcripts in manifests.
- `capabilities`: named features, each with status `supported`, `unsupported` or `unknown`, reason
  and evidence list. Supported features require current project-relative path/SHA-256 receipts.
  A reason alone is not tested support. Feature names are project declarations; examples include
  `cold-invoke`, `vfp`, `mmio`, `interrupts` and `boot-state`.
- `assessment_context_sha256`: `executor_capabilities.context_digest(manifest)`, binding target and
  executor version/configuration. Changes require capability reassessment, not automatic rebinding.

`bench-requirements-v1` requires `target` (binary path/SHA-256), a stable `unit_id`, and a nonempty
unique `required_features` list. Do not silently treat an unclassified unit as pure logic. The unit ID
is a declaration; use the existing unit manifest to establish its actual identity.

```python
from executor_capabilities import context_digest
print(context_digest(manifest))
```

Import from the actual skill's scripts folder. Record the printed value in a newly reviewed
manifest after acquiring the real evidence. Computing a binding does not test a capability.
All receipts in the manifest must remain fresh, including those for capabilities not required by
the current unit, because the assessment is bound to that whole declared context.

## Assessment and escalation

```powershell
python -B 'PATH_TO_SKILL/scripts/executor_capabilities.py' --project 'PROJECT_ROOT' assess --manifest bench/executor.json --requirements bench/requirements.json
```

The command is read-only and emits an `ok`/`result` envelope. Exit 0 means every required feature
has declared supported status with matching receipts. Exit 2 means ineligible/invalid/stale input;
for a valid ineligible assessment, inspect `result.unknown`, `unsupported` and `reasons` rather than
only `ok`. Missing features are unknown. Booleans are not capability statuses. Paths cannot escape
the project or use harness state. No target is executed and no files are written.

For an ineligible assessment, explicitly record the missing features and review an alternative
executor's own versioned manifest. Changing executor, initialization, hooks, maps or tool versions
changes the context. Do not automatically fall back, rerun an unknown outcome, promote a grade,
or infer that choosing Renode makes a feature supported. Existing authorization boundaries apply.

Unicorn is a reasonable first candidate for a pure CPU unit, but VFP is not universally excluded:
its [official FAQ](https://github.com/unicorn-engine/unicorn/blob/master/docs/FAQ.md) describes ARM
VFP setup and CPU-model differences. A wrapper may reject it; record that wrapper/configuration
limit. Renode may suit modeled peripherals or boot-state requirements, but those capabilities
still need their own evidence. Neither brand guarantees that a particular bench is sufficient.

## Optional differential preflight

```python
from differential import differential
context = {"project": project_root, "manifest": executor_manifest,
           "requirements": unit_requirements}
matched = differential(title, cases, invoke=the_reviewed_invoke, blob=frozen_blob,
                       clean_pc=return_trap, executor_context=context)
```

Supply the assessor module next to `differential.py`. It assesses before compilation or invocation,
rechecks before and after each invocation and refuses a changed manifest, requirements or referenced
file. It returns the same boolean as before when the comparison completes. Rejections raise
`DifferentialError`; if execution already began, reconcile the actual outcome before any retry.
With reporting enabled, context and requirement hashes appear in the bounded comparison report.
Save the full assessment separately when durable structured provenance is needed.

The caller remains responsible for ensuring `invoke` actually uses the declared executor and
configuration. This helper does not introspect the callable, compiler, live emulator or hardware.
It cannot discover omitted features or authenticate the semantic content of evidence. Hash checks
are snapshots, not an execution lock or tamper-proof signature. A matching differential result
remains limited to its witnesses/model/state, and a mismatch does not uniquely blame the C++ body.
