# Verification — local toolchain refinements, 2026-11-08

Source baseline: `b9b7be5`. Development branch: `feature/toolchain-refinements`.
No installation, publication, release tag, live project migration, engine setup or real target run.

## Observed test results

| Suite | Tests run | Passed | Skipped |
| --- | ---: | ---: | ---: |
| Binary Analysis Profile, unchanged | 25 | 24 | 1 |
| Renode Bench, including 19 new capability tests | 33 | 33 | 0 |
| Decompile, including 13 new provenance tests | 42 | 42 | 0 |
| Total | 100 | 99 | 1 |

The skipped test is the pre-existing symlink-escape test: the Windows account cannot create
symlinks. It was already skipped in the 68-test baseline. No new test was disabled or skipped.
Path traversal, absolute evidence paths and harness-state evidence rejection are tested separately.
Final suite runs completed successfully in 0.607, 1.015 and 0.894 seconds respectively.

## Other executed checks

- Existing binary-profile synthetic pilot passed its positive/negative CLI cases with files preserved.
- Existing closure synthetic pilot passed its scheduling and claim-ceiling checks.
- Existing differential `--selftest` passed acceptance, mismatch and witness-discrimination checks.
- New integrated synthetic pilot passed: unresolved graph calls stay blocked, an unknown MMIO
  requirement prevents invocation, a separate CPU-only unit matches in the fake bench, and changed
  target bytes invalidate graph provenance. No requirement was removed from the blocked unit.
- All three skill metadata validators passed with explicit PyYAML. The Renode validator required
  `python -X utf8` because the Windows default text encoding could not decode its UTF-8 typography.
  This was a validator invocation fix, not a change to the user's system encoding.
- `git diff --check` passed. Binary Analysis Profile has no source diff from the baseline.

New tests also cover changed export/grade/edge receipts, wrong graph binding, producer-context
drift, unknown/duplicate edge annotations and explicit annotation coverage. Capability tests cover
target mismatch, changed receipts/configuration, supported/unsupported/unknown states, ineligible
CLI exit 2, missing/partial context, missing assessor, context mutation during a run and refusal
before compiler/invocation. Real subprocesses exercise the opt-in CLI and legacy CLI.

## Evidence ceiling

These tests use synthetic local bytes, declared receipts and fake invoke callbacks. They do not
install or run angr, Ghidra, Unicorn, Renode or the ARM cross-toolchain; no firmware is executed.
The angr recipe is checked against official documentation, not a runtime target test. Capability
support remains declared and evidence-bound, not authenticated. The assessor does not prove that
a supplied callable used the declared engine. File hashes are snapshots, not operator signatures
or locks, and a matching differential observation does not establish universal hardware behavior.

Run the commands in [the refinement guide](toolchain-refinements.md) to reproduce the tested scope.
