# Optional graph provenance and focused indirect-edge recovery

Local development preview. The existing `decompile-callgraph-v1`, grade map and closure-report-v2
remain unchanged. `report --provenance FILE` adds a physical binding and edge-origin summary;
without that option the legacy report is unchanged. No exporter, angr installation or execution is
bundled. This helper still does not disassemble, schedule external jobs or promote grades.

## Reuse identity instead of duplicating it

Use binary-analysis-profile's existing target/unit manifests to establish input identity and
revalidation conditions. The provenance file references the same original binary hash; it does
not replace the target manifest or revalidate the address map. Matching names/indices across
builds do not establish unit equivalence. Use the existing profile rules for that comparison.

Reuse an existing Ghidra/pyghidra exporter. Freeze its JSON, producer version/options and supporting
artifacts. Initial exports may be reused while relevant bytes, maps, modes, versions and settings
remain compatible. Reassess/re-export after changes; do not silently update old receipts.

## Focused angr routing

When unresolved indirect calls block useful closure, select a bounded investigation and reuse
the confirmed target/map. Try the faster static CFG analysis first; escalate to symbolic-emulated
recovery only for a justified residual question, with explicit initial-state assumptions and a timebox.
The official [angr CFG guide](https://docs.angr.io/en/latest/analyses/cfg.html) describes their different
completeness limits and relevant options. Example for an already authorized/configured environment:

```python
project = angr.Project(binary_path, load_options={"auto_load_libs": False})
cfg = project.analyses.CFGFast(function_starts=selected_starts,
                             force_complete_scan=False,
                             resolve_indirect_jumps=True)
```

Raw firmware also requires the correct loader, architecture, map and mode from its target profile.
Selected starts seed analysis; they do not guarantee a strict region limit. Review the installed
version's region/budget controls. A timeout is incomplete analysis, not evidence of a leaf. Preserve
unresolved indirect sites in `unknown_calls` or unknown adjacency even if some targets are recovered.
Export through the existing graph format; do not count a resolved static edge as exercised behavior.
This recipe was documentation-checked, not executed against a real target in this development.

## Provenance format

Copy `assets/templates/provenance.example.json` and fill actual current receipts. Required fields:

- `format`: `decompile-provenance-v1`.
- `target`, `callgraph`, `grades`: project-relative `{path, sha256}` receipts.
- `producer`: name, version and settings used for the export.
- `export_context_sha256`: `closure.export_context(provenance)`, binding target and producer context.
- `edges`: optional-coverage list of annotated edges already present in the graph. Each has caller,
  callee, basis (`inferred`, tool-declared `resolved`, or declared runtime `observed`) and at least
  one current evidence receipt. An empty list reports 0/total coverage, not complete evidence.

Calculate the context hash only after reviewing the actual export context:

```python
from closure import export_context
print(export_context(provenance))
```

Import from the actual skill's `scripts` folder. Put that value into a newly reviewed declaration;
do not recompute it automatically to silence a stale-context refusal. Hashes bind declarations,
not authorship. An operator can still describe an export incorrectly.

```powershell
python -B 'PATH_TO_SKILL/scripts/closure.py' --project 'PROJECT_ROOT' report --callgraph analysis/callgraph.json --grades analysis/grades.json --provenance analysis/provenance.json
```

Exit 0 means the declared report was produced; exit 2 means invalid/stale input. Input files are
never rewritten. Evidence cannot leave the project or point into `.harness`. Graph and grade
paths selected on the CLI must be the exact files referenced in the provenance declaration.

The result includes the provenance/context hashes, physical hash match, declared producer,
edge-origin counts and annotated/total edges. Recovered origins never clear unknown calls, alter
grades or authenticate runtime edges. `evidence_verified`, `semantic_truth_verified` and
`promotion_authorized` remain false. A static export is not an authenticated execution trace,
and receipt freshness is not a lock on later human changes.
