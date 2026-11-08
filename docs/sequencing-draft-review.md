# Review — up-front call-graph export sequencing draft

Initial assessment followed by an explicitly authorized local documentation update on 2026-11-08.
The private PR draft was corrected and the guide updated; no PR, issue or publication was created.

The proposed documentation hint is useful for a whole-image reconstruction campaign: obtain a
reviewed initial graph before using closure-based leverage to select work. Existing local guidance
already covers identity, reuse invalidation and unknown edges; this is a sequencing clarification,
not a missing exporter or proof mechanism. The canonical sequence now lives in the toolchain guide;
the provenance and adapter guides link to it rather than repeat its rules.

Refinements to the proposed wording:

1. Replace unconditional “once” with initial export plus reuse while binary/map/version/settings
   remain compatible. Relevant changes require review/re-export, not eternal cache reuse.
2. Do not guarantee a “complete direct-edge graph” from running a tool. State the graph's declared
   inventory/completeness, keep unknown adjacency/calls, and distinguish candidates from evidence.
3. Do not promise “true max-fan-in”: `closure.py` ranks declared undone direct callers. It does not
   know missing edges, full runtime reachability or a universal best target.
4. Unresolved indirect edges may need focused static/manual/symbolic or runtime investigation.
   angr and a runtime probe are options, not mandatory or infallible alternatives.
5. The illustrative `@@ Choosing ... @@` hunk lacks unified-diff line ranges. Regenerate a real
   patch from the current branch before using `git apply`; do not treat this draft as executable input.

See the [canonical sequencing section](../skills/decompile/references/toolchain.md#whole-image-graph-export-sequencing)
for the maintained wording. The corrected draft contains a real Git-generated patch against its
stated baseline instead of the earlier illustrative hunk. No new API, engine installation or
runtime behavior change is implied by this documentation update.
