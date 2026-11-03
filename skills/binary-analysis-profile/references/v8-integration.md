# Optional integration with VeriMission

This package does not include a copy of the harness. If the project already uses VeriMission, consult the installed version and its original modules. Do not initialise a second state store, edit canonical state, or change global rules to adopt this profile. The commands below were written for V8.0 and must be checked against the version actually installed.

## Existing mission

1. Open the V8.0 skill and run `resume` and `validate` with the correct `--project` value.
2. Search existing results and review the topic before starting an investigation. Preserve the current `review → start → check → close` flow, criteria, and receipts.
3. Use the helper only for criteria that are already compatible. To add, remove, or change a criterion in the active mission, prepare a proposal only after an explicit user request or authorisation, then follow the human `preview-mission` / `revise-mission` process. Never apply an automatic migration.
4. Separate the target-integrity criterion from real semantic criteria. The first may use `target` or `unit`; the others require a tool or test that discriminates the statement. `witnesses` checks a report; it does not generate or authenticate an execution.

## Example criterion for a new mission

Replace paths and the description before `init`. This example checks documentary integrity, not firmware behaviour:

```json
{
  "id": "BIN-ID",
  "description": "Check target identity and consistency of the declared map without authenticating architecture or semantics",
  "argv": ["REAL_PYTHON", "-B", "tools/binary_profile.py", "--project", "REAL_ROOT", "target", "--input", "analysis/target.json"],
  "artifacts": ["evidence/image.bin", "analysis/target.json", "tools/binary_profile.py"]
}
```

For this example to work, copy the helper to `tools/binary_profile.py` in the project. The local copy lets V8 protect the verifier version as well. Do not declare one local copy as evidence while silently running another version from the skill. Review the code before execution; verify the real Python path too. The bundled pilot demonstrates this arrangement with synthetic bytes.

V8 runs argv with the project root as the working directory. Declare all relevant paths explicitly in `artifacts`, including copied inputs, logs, and external verifiers. Do not rely on glob expansion. For `unit`, include the target and unit manifests. For `witnesses`, also include the report and every file referenced by its cases and control. Hashing the report alone does not protect later changes to its external files.

Generate and freeze the files before `check`. The command's exit code must reflect the result; do not wrap a failure in a command that always returns zero. Inspect `result.passed` in the coordinator output. If a result cannot be reproduced read-only, separate authorised acquisition from verification of the record and disclose the proof boundary. Do not invent a re-execution.

## Recording scope and resumption

Use `evidence-scope` with the actual check to state what it verifies, what it does not verify, its limitations, and coverage over the relevant universe. Consult the schema of the installed V8 distribution; do not create a parallel format or substitute declarations for evidence. The core's three denominators continue to apply where relevant.

Link tasks and claims through real dependencies. Aliases help recovery but do not prove equivalence between regions. Use `context-pack` and `view-status`, or `capsule` and `capsule-status`, for resumption. Check canonical state for the installed version when views disagree. Capsules cannot be imported as authorisation or fact. Do not copy everything into global memory or maintain a competing fact list in status JSON.

After invalidating configuration or evidence, review affected dependants through the V8 workflow. Retraction and revalidation preserve history and do not count as new discovery. At closure, `traceability`, `accept-mission`, and `validate` assess the adopted contract; accepting an integrity criterion does not mean the target's semantics were fully recovered.
