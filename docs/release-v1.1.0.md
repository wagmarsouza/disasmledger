# DisasmLedger v1.1.0 — Decompile workflow

This release adds **DisasmLedger Decompile 0.2.0** alongside Binary Analysis Profile and Renode Bench. Decompile provides a staged reconstruction workflow, a grade ladder separating original observations from reconstructed-code comparisons, tool routing, and a read-only call-graph scheduler.

Renode Bench 1.1.0 adds a programmable differential comparison helper. The ARM compiler and target-specific emulator invocation remain external dependencies.

## Install

```sh
npx skills add wagmarsouza/disasmledger --skill binary-analysis-profile
npx skills add wagmarsouza/disasmledger --skill renode-bench
npx skills add wagmarsouza/disasmledger --skill decompile
```

The ZIP asset includes the three sibling skill directories and publication documentation. The source archive contains the full release. External tools and firmware are not bundled.

## Validation and scope

The release was checked with the three unit-test suites, the binary-profile and decompile synthetic pilots, the differential offline self-check, skill frontmatter validation, and GitHub CLI publication validation. Tests use synthetic inputs and fake execution; no real firmware, ARM toolchain, Renode backend, or hardware was validated.

The supplied scheduler retains known limitations: a generic G4 label, G0 and out-of-graph grade counting, optimistic closure for absent adjacency, and declared grades without evidence verification. Read [the Decompile guide](https://github.com/wagmarsouza/disasmledger/blob/v1.1.0/docs/decompile.md) before relying on readiness or totals.

Existing skill identifiers and installation commands remain stable. The repository retains its existing distribution terms; no reuse licence has been added.
