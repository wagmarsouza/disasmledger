# DisasmLedger — Decompile 2.0

Decompile2.0 publishes the previously qualified evidence-bound reconstruction extension.
The component identifier remains `decompile`; version metadata is 2.0.0. The tag
`decompile-v2.0.0` avoids confusion with the older repository-wide `v2.0.0` release.
There is no downgrade or replacement of that old release. Legacy closure/grade/provenance,
inventory-adapter and preservation APIs remain available; no live project is migrated.

## Downloads

- [Standalone Decompile2.0](https://github.com/wagmarsouza/disasmledger/releases/download/decompile-v2.0.0/decompile-2.0.zip)
- [Complete DisasmLedger sources](https://github.com/wagmarsouza/disasmledger/releases/download/decompile-v2.0.0/DisasmLedger-Decompile-2.0.zip)

The standalone archive includes the canonical binary_profile identity helper as a byte-identical
distribution resource, not another maintained identity engine. Complete sources contain sibling
skills, including the previously qualified optional 8.3 preservation witnesses. Siblings are not
installed automatically. Read the receipt/checksums and [verified-completion guide](verified-completion.md).

## Evidence pipeline and scope

All five gates must qualify: source representation, actual compilation, finite differential
behavior, execution-image independence and discriminating healthy/known-bad controls. AST signals
assist approved review; keyword presence/absence cannot prove structured reconstruction.
Descriptor/transliteration/hybrid labels, stale source/review, old loaded image, original/unknown
code reentry, omitted witnesses, missing reset and weak controls cannot qualify through these gates.
Legitimate straight-line code and data-address constants are not forbidden by a brittle regex.

With [Control8.4](https://github.com/wagmarsouza/long-project-agent-harness/releases/tag/v2.4.0-rc.1),
the native harness owns the universe, denominator, closure, live eligibility and audit hold.
`completion.py` emits observations without editing the mission ledger. `census_bars.py --harness`
queries the live authority and separates declared/verified-now/pending/stale. Declared overlaps;
the other three partition the approved live denominator. G4-stock and G4-recon stay separate.

## Use without installation

Python3.11+ runs legacy stdlib helpers. The optional new AST gate additionally requires pycparser
(requirements-verified.txt) and an explicitly approved compiler/executor appropriate to the target.
No external engine/compiler is bundled or installed. In an extracted standalone folder:

```powershell
python -B scripts/completion.py --help
python -B scripts/census_bars.py --help
python -B examples/run_measurement_pilot.py --harness C:/tools/harness_v8.4/scripts/harness.py
python -B scripts/census_bars.py --project C:/your-project --callgraph analysis/callgraph.json --grades analysis/grades.json --harness C:/tools/harness_v8.4/scripts/harness.py --ascii
```

Ask the agent to read SKILL.md explicitly; there is no universal slash command. Adopt policy
only through an authorized mission or explicit revision, never by editing state.yaml/reinitializing.
The pilot creates a disposable synthetic project; `--compiler /usr/bin/gcc` on Linux adds real
native C compilation/process execution. It is not ARM firmware, Renode/Unicorn or hardware validation.

## Executed qualification and limits

Qualified runtime snapshot: `08b6daee798cbebeea9c47f8da1bdc53c02f7f39` (then local metadata0.8.0-preview).
The 2.0 version change affects metadata/docs, not executable semantics. Windows and Ubuntu/WSL each
passed 123 Decompile tests, 40 Renode tests and 25 profile tests (one Windows-only symlink skip;
no Linux skip). Extracted standalone gates, official skill validation, live bars and the integrated
GCC pilot passed. Four guard inversions across both projects were detected, not a global mutation score.

Initial Linux runs encountered infrastructure timeouts, including old CLI helpers and a trivial
GCC compile. They are retained. Repeating with dependencies/logs on Linux and reduced contention
passed with product code, timeouts and gates unchanged. Hosted CI results, if run, are separate
actual evidence. The release receipt distinguishes qualification and publication commits.

Physical hashes/receipts do not authenticate a hostile reviewer/runner. Approved source review,
complete declared dependencies, origin reporting and finite witnesses remain trust boundaries.
No universal semantic, readability, hostile-tamper or firmware-equivalence guarantee is made.
Real mission data, user credentials and local absolute-path logs are excluded from release assets.
Publishing/extracting does not install skills or migrate live projects. Previous releases remain.
