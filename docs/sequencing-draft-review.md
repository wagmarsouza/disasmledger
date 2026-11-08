# Review — up-front call-graph export sequencing draft

Assessment only. No PR, issue, publication or change to the original private draft.

The proposed documentation hint is useful for a whole-image reconstruction campaign: obtain a
reviewed initial graph before using closure-based leverage to select work. Existing local guidance
already covers identity, reuse invalidation and unknown edges; this is a sequencing clarification,
not a missing exporter or proof mechanism. The adapter adoption guide now makes that timing explicit.

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

Suggested compact wording:

> For a whole-image reconstruction, export and review an initial call graph before closure-based
> scheduling. Reuse it while the binary, map, relevant tool versions and settings remain compatible;
> reassess/re-export after changes. Scheduling reflects the declared graph only: preserve unresolved
> calls and incomplete-inventory warnings, and investigate selected indirect edges without treating
> recovered targets as runtime proof.

No new API, backend installation or behavior change is implied by that paragraph.
