# VeriMission adapter verification — 2026-11-08

Base: `0ca818a`, local branch `feature/verimission-82-adapter`. Decompile preview 0.5.0-dev;
adapter format implementation 0.1.0-dev. No install, publication, release tag or live migration.

## Repository regression results

| Suite | Run | Passed | Skipped |
| --- | ---: | ---: | ---: |
| Binary Analysis Profile, unchanged | 25 | 24 | 1 |
| Renode Bench, unchanged from prior local preview | 33 | 33 | 0 |
| Decompile, including 28 new adapter tests | 70 | 70 | 0 |
| Total | 128 | 127 | 1 |

The one skip is the pre-existing Windows symlink-creation limitation, present before this work.
No new test was skipped or disabled. Parent traversal, absolute evidence paths and harness-state
references are rejected in separate executed tests. Existing profile, closure and toolchain pilots
and the differential selftest passed. All three skill metadata validators passed in explicit
PyYAML/UTF-8 mode. Native profile/bench helper sources have no diff from the adapter's base commit.

Adapter tests cover reconstruction projection, raw stock/legacy grade retention, fixed G0 exclusions,
unit-universe drift, incomplete/empty inventories, missing grades, live/closed mismatch preservation,
unmarked changes, declared kind/claim passthrough, nonprojected changes, baseline transitions,
current receipts, source path limits, exact native fields, fact labels, source/bundle drift,
exclusive output and a real CLI export/verify roundtrip. Optional provenance tests reuse the existing
binding helper and reject another target or a different grade-file binding.

## Real native 8.2 integration

`examples/run_verimission_adapter_pilot.py` was executed with the original local 8.2 `harness.py`.
The adapter was not substituted for its reconciler. Seven synthetic temporary missions exercised:

1. Normal conversion, frozen-source checks, native digest/review, verified boundary closure and consolidation.
2. Unmarked promotion: native `RECONCILIATION_FAILED` with `unmarked_promotions`; cycle stays active.
3. Justified retraction: native negative compiled/compared delta preserved and corrected ID reported.
4. Unexplained regression: native refusal; no fabricated correction or promotion.
5. Live/closed mismatch: preserved by the adapter and blocked by native reconciliation.
6. Possible lost fact use: native review requires an explicit loss explanation before closing.
7. Raw-source drift: adapter preflight rejects it and native verified close refuses `STALE_ARTIFACT`.

Successful cases also preserve the mission hash, leave the claims collection empty and pass native
`validate`. Reread findings were produced from actual physical synthetic notes; they do not
authenticate cognition. The read-only criterion executes the copied adapter against baseline and
all preceding cycle bundles, with their raw sources/helper code declared as frozen artifacts.

The native harness SHA-256 observed by the pilot was
`54e873bed73dec94716c27d24a6805fb1dbd6ab51632b7722993d06a81d1969d`.
The unmodified native suite separately passed **163 tests** in 61.712 seconds. All 56 payload files
in the original native 8.2 manifest were verified unchanged after testing. No VeriMission source,
installed skill or real mission state was changed.

## Reproduce and limits

```text
python -B -m unittest discover -s skills/decompile/tests -v
python -B -m unittest discover -s skills/renode-bench/tests -v
python -B -m unittest discover -s skills/binary-analysis-profile/tests -v
python -B examples/run_verimission_adapter_pilot.py --harness /path/to/original/v8.2/scripts/harness.py
```

Export and verification do not run grade gates, validate actual inventory completeness, discover
hidden dependencies, authenticate source authorship, execute firmware or prove semantic/hardware
correctness. The native consistency checker also cannot prove a declared grade true. Real external
tools and targets were not exercised. Exclusive output prevents replacement of old artifacts but
does not create an OS transaction across bundle files or a lock on later source edits. Fixed epoch
membership and the scope of this reconstruction projection are explicit adoption constraints.
