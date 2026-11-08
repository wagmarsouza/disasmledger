# DisasmLedger → VeriMission 8.2 adapter

Local development preview. `scripts/verimission_adapter.py` exports declared snapshots and verifies
their physical source bindings. It does not contain the VeriMission executor or its reconciler.
Export/verify work without VeriMission installed; actual reconciliation requires the existing 8.2
`periodic_review` inventory workflow. No skill, tool, service, schedule or live mission is installed.

## Adopt an explicit epoch

Use the original target/unit identities from binary-analysis-profile, not fresh numeric aliases.
Create a `disasm-verimission-contract-v1` from `assets/templates/verimission-contract.example.json`:

- `target`: existing original-binary path/SHA-256 receipt, project-relative.
- `scope`: the exact declared inventory scope; it is not automatically the whole firmware.
- `anchor`: the native review epoch's cycle anchor; zero for a new mission.
- `units`: unique IDs of the full declared scoped inventory, including G0 exclusions.
- `excluded_g0`: the fixed G0 subset for this epoch.
- `projection`: `reconstruction-v1`.

The graph must declare scoped inventory completeness, and its ID universe must exactly match the
contract. Completeness is still a declaration, not authenticated by this adapter. A changed target,
unit universe or G0 membership needs a deliberately reviewed new epoch/contract and the existing
human-authorized mission revision workflow. The adapter never invokes that workflow. Do not remove
newly inconvenient units, relabel G0 or edit the denominator to make a report pass. If all units are
excluded, use notes-only review; a fake 0/0 inventory policy is not generated.

For a whole-image campaign, obtain and review a useful initial graph before graph-based scheduling
and baseline adoption. Reuse it only while relevant inputs remain compatible. An export is not
guaranteed complete, and a partial graph supports only declared-edge leverage, not a true global
fan-in maximum. Preserve unknown calls and use the existing focused-analysis guidance as needed.

## Reconstruction projection and its limits

| Original declared grade | Native observation category |
| --- | --- |
| Missing grade | `ungraded`, with a missing-grade note |
| G1, G2, G3, G4-recon | Same label |
| G4-stock | `ungraded` for reconstruction; retain stock-only note and original raw value |
| Legacy G4 | `ungraded`; retain ambiguity note and original raw value |
| G0 | Excluded only by the frozen epoch subset |

G4-stock does not establish reconstruction maturity. The single-label source format cannot express
both stock observation and an independent compile grade; do not infer an earlier G3 from history.
The receipt preserves raw live/closed grade maps so projection is explicit, not lost information.
The adapter does not edit those maps. Existing closure scheduling and original grade semantics remain intact.

The native inventory categories are `ungraded`, G1, G2, G3 and G4-recon. Its denominator is the fixed
epoch's non-G0 unit count. Counters are named `declared_compiled_or_compared` and `declared_compared`
to avoid presenting declared grades as independently verified behavioral coverage. They are not
instruction/path/whole-system coverage and do not measure stock-only observations.

## Per-cycle frozen inputs

Use `disasm-cycle-snapshot-v1` from `assets/templates/verimission-cycle.example.json`. Supply the
cycle number, callgraph receipt, separate live/closed `decompile-grades-v1` receipts, transitions,
and optional `facts_recorded`/`facts_used` labels. Live and closed may reference the same frozen
file when that is actually the observed source. Keep cycle-specific immutable filenames.

Optional `provenance` references an existing `decompile-provenance-v1` file. The adapter reuses
`closure.bound_report`, checks the target binding and collects its nested evidence dependencies.
Without it, graph identity/freshness is checked but producer/version execution is not authenticated.
The binary profile and existing provenance workflow remain responsible for map/configuration context.

Transition records use native keys `id`, `from`, `to`, `kind`, `reason`, `evidence` and optional
`claim_id`, with original grade labels in from/to. `ungraded` may represent a previously missing grade.
Provide actual current evidence path/SHA-256 receipts. The adapter maps labels and preserves the
declared kind; it never guesses the prior cycle, manufactures missing receipts or fixes a wrong kind.
Native 8.2 checks actual changes, direction, claim links, regressions and arithmetic.

Changes that remain in the same reconstruction category, such as stock-only/ambiguous labels, are
retained as `unprojected_transitions` in the conversion receipt and not counted as reconstruction
progress. A baseline cannot claim transitions, and excluded IDs cannot carry projected transitions.
The receipt reports source/implementation hashes, projection notes and the suggested native inventory
policy. It always declares reconciliation and semantic verification false.

## Export and verify

```powershell
$adapter = 'C:\source\DisasmLedger\skills\decompile\scripts\verimission_adapter.py'
$project = 'C:\project'
python -B $adapter --project $project export --contract analysis/adapter-contract.json --input analysis/cycle-0000.json --bundle exports/cycle-0000
python -B $adapter --project $project verify --contract analysis/adapter-contract.json --input analysis/cycle-0000.json --bundle exports/cycle-0000
```

Create the authorized `exports` parent first. Export reserves a NEW directory containing
`observation.json` and `receipt.json`; existing artifacts are never overwritten. The baseline input
must use the anchor cycle and an empty transition list. Subsequent cycles need their own bundles.
Input/evidence/output paths stay within the project and cannot use `.harness` state. Strict JSON
loading reuses the closure helper's duplicate-key/nonfinite rejection.

Exit 0 means conversion/source verification within this scope, never reconciliation or grade truth.
Exit 2 means rejected, changed, incomplete or invalid data. Output is an `ok`/`result` JSON envelope.
Verification regenerates the expected projection in memory and compares exact observation/receipt
bytes, source hashes, contract/input digests and adapter/helper versions. It never rewrites files.
An interrupted multi-file export can leave a partial directory; inspect it and preserve history.
Verification refuses incomplete bundles. There is no transaction spanning two output files or a lock
on future source changes, and local checksums do not authenticate a malicious operator.

## Use the existing native reconciler

Read the baseline receipt's `inventory_policy`. During authorized adoption, copy it into the
existing mission's `periodic_review.inventory`, align `anchor`, and set native paths such as:

```json
{
  "baseline": "exports/cycle-0000/observation.json",
  "observation_pattern": "exports/cycle-{cycle:04d}/observation.json"
}
```

These are fragments, not a full mission or authority to change one. Set the native cadence, notes,
governing instructions and mutable sections through the normal 8.2 contract. Do not reinitialize
an existing mission or replace its acceptance tests with this adapter check.

Add an explicit read-only adapter verifier to the authorized criteria. Verify every relevant frozen
bundle, including the epoch baseline/preceding window source. Declare the contract, cycle inputs,
all `receipt.sources`, observations/receipts and the actual adapter/closure/verifier code as artifacts.
Use cycle-specific criteria/paths so later snapshots do not invalidate earlier evidence by sharing
a mutable current-grades file. Frozen artifacts and checks must exist before verified close.

Merely pinning the emitted observation does NOT detect later raw-source drift: the source verifier
and its declared artifacts are necessary. The integration pilot demonstrates an actual native
criterion that verifies the baseline and all cycle bundles before the boundary closes.

Then use native `check`, `digest`, `decade-review`/`close --review-input` and `validate` normally.
Native 8.2 owns conservation, live/closed equality, marked changes, justified retractions, possible
losses, reread, core protection, consolidation and YAML events. The adapter preserves mismatches and
unmarked changes so that engine can refuse them. A justified downward correction can lower counters;
possible missing fact use needs explicit review, not automatic deletion. No native store is edited here.

## Tested scope

The repository includes an explicit pilot:

```powershell
python -B examples/run_verimission_adapter_pilot.py --harness C:\source\VeriMission\harnesses\v8.2\scripts\harness.py
```

It uses the original engine supplied by path and synthetic temporary projects only, never firmware
or real model/agent work. Review [the verification report](../../../docs/verimission-adapter-verification.md)
for exact observed outcomes. No universal grade-gate truth, source authorship or hardware correctness
is established by a successful export or native consistency check.
