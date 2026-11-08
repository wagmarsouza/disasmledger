# Toolchain refinements — local development

No installation, publication, external-engine installation, live-target execution or migration.
Development starts at `b9b7be5` on a separate feature worktree. Preserve the existing closure report,
grade ladder, conservative unknown-edge treatment, differential boolean API and trace/profile helpers.

Baseline: 68 tests ran across all three skills: 67 passed and the existing Windows symlink test
was skipped because this account cannot create symlinks. No test was disabled for this work.

## Additive slices

1. Optional closure provenance ties an existing export and grade map to physical binary/export/
   evidence hashes and declared producer version/options. Edge origin annotations distinguish
   inference, tool-declared resolution and runtime observation without promoting grades or removing
   unknown calls. Preserve the original output and behavior when the option is absent.
2. A standalone bench capability assessor checks a target-bound, version/configuration-specific
   manifest against a unit's declared feature requirements. Supported features require current
   evidence receipts; unsupported/unknown requirements refuse eligibility. No brand-based feature
   assumptions, automatic escalation or emulator dispatch.
3. Opt-in differential preflight reuses the assessor before compilation/invocation and checks
   freshness afterward. Existing calls remain unchanged. Wrong/missing capabilities must prevent
   execution, while a changed context during execution invalidates the contextual result.
4. Document targeted angr routing and conservative Capstone/emulation claim ceilings. Reuse existing
   profile identity/revalidation rules; do not build another identity system, graph exporter, census
   reconciler, scheduler, emulator or VeriMission copy.

Tests use synthetic files and fake invocation functions only. They test consistency/gating, not
actual engine capability, native ARM compilation, CFG accuracy or real hardware equivalence.
