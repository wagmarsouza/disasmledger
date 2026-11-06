# Differential testing: when the recompiled unit accelerates the rest

Testing a reconstructed unit against the original serves two different purposes, and they do
not trigger at the same time:

- **Certification (local).** A test proves *this* unit matches the original on the exercised
  inputs. It raises confidence in that unit and teaches nothing about the others. Re-testing an
  isolated, already-done leaf is certification only.
- **Acceleration (propagating).** A test becomes reusable knowledge for the *other*,
  not-yet-done units. This only happens under the conditions below.

The common mistake is to gate testing on a coverage percentage ("we are only at 15%, too
early"). Coverage is the wrong number. The right number is **call-graph closure**: whether a
unit's transitive callees are already reconstructed, so the test runs against known code
instead of stubs/unknowns. A low overall coverage can still have a large *closed* sub-region
if the high-fan-in infrastructure was reconstructed first.

## Criteria — test unit `f` for acceleration when all hold

- **C1 — closure (required for this scheduling policy).** Transitive callees must be declared
  G3 or G4-recon (prefer G4-recon). Unknown adjacency and unresolved indirect calls block closure.
  Tests with controlled stubs can still teach local facts, but must disclose their assumptions
  and cannot establish integrated reconstruction equivalence.
- **C2 — leverage (priority).** Order by fan-in: proving a helper propagates a prior to its
  callers. A helper with fan-in 100–1000 is a jackpot; a fan-0/fan-out-0 leaf is certification
  only. Attack threshold: fan-in ≥ ~30 at the start (the top helpers), then ≥ ~3 once a
  differential harness exists.
- **C3 — discrimination (required).** At least two witnesses on **different branches/outputs**,
  with a positive control. Two witnesses on the same branch do not discriminate.
- **C4 — hypothesis (bonus).** `f` exercises a struct offset or control-flow the shared type
  model infers; the test then confirms or refutes the model for every unit that reuses it.

Selection, in short: test `f` ⟺ `C1 ∧ C3 ∧ (fanin(f) ≥ K ∨ hypothesis(f))`.

## Using `closure.py`

`closure.py` consumes a declared call graph (`{fn: [callees]}`) and a declared grade map
(`{fn: "G0"|"G1"|"G2"|"G3"|"G4-stock"|"G4-recon"}`) and reports, read-only:

- **testable_now** — not-done units whose callee-closure is complete (C1 satisfied): the units
  you can differentially test immediately as you reconstruct them.
- **top_leverage** — undone helpers ranked by number of distinct undone callers (C2): where a
  single reconstruction propagates furthest.
- **ft_g3_closed / ft_g4_closed** — live units whose callees are declared G3-or-G4-recon /
  G4-recon respectively. These measure callee closure, excluding the unit's own grade; even an
  ungraded leaf has empty callee closure. They are not verification counts.
- **totals / coverage flags** — G0 is excluded from live counts. Out-of-graph grade identifiers
  are rejected. Missing grades, unknown calls/adjacency, ambiguous legacy G4, or absent inventory
  completeness keep coverage indeterminate. Cycles conservatively remain not closed.

It does not disassemble, execute, grade, or promote. It is a scheduler: it tells you *what is
worth testing next and why*, not whether anything is correct. Grades must be recorded from
the gates; the helper does not verify those records. The graph comes from the call-graph backend.
Legacy G4 is accepted for inspection but blocks reconstruction closure. Report format is
`decompile-closure-report-v2`; `evidence_verified` stays false.

A static call graph (from BL/BLX immediates) misses **indirect** dispatch edges — vtable and
jump-table calls whose target is computed. Those unseen edges make the closure look *more* closed
than it is, so `testable_now` and the FT counts are an optimistic upper bound: a unit reached
mainly through dispatch into not-done code can appear ready when it is not. Confirm the closure by
hand for any unit whose callers or callees are dominated by indirect dispatch, and prefer a graph
backend that recovers dispatch edges when one is available.

## The recompile-and-bench executor (G4-recon)

The closure report says *which* unit to test; the executor is *how* you test it. It turns the
reconstruction's own behaviour into evidence, which is stronger than characterising the stock:

1. **Compile our C++ body** to a position-independent Thumb `.text` blob (the real cross-toolchain,
   the target's `-mcpu`).
2. **Load the blob into RAM** at a base address and **forced-invoke it** on the same bench the stock
   was measured on — call the function directly rather than driving the whole UI.
3. **Compare our outputs to the stock witnesses** already established for that function, under the
   two-witness discipline: at least two witnesses on different branches/outputs, plus a clean return.
4. A match supports **G4-recon** within the witnessed scope after evidence review. A mismatch
   blocks promotion: investigate source, ABI, dependencies, initial state, and bench setup before
   assigning the cause to C++ (R80).

This is emulator-agnostic. Route a **pure-logic leaf** to Unicorn (CPU-only, fast, no peripherals);
route a unit bound to **peripherals or an active boot/therapy context** to Renode. The
[renode-bench](../../renode-bench/SKILL.md) skill ships `scripts/differential.py`, which owns the
generic parts (compile the blob, lay it in RAM, compare under the discipline) and takes your bench
`invoke` as a plug-in, so the same harness serves either emulator.

**Position-independence limit (honest bound).** Running our body in RAM only proves the stock when
the blob is position-independent: a leaf with no absolute literal-pool reference and no BL/BLX to an
address not loaded in the same space. For a caller, load its callees too — or a stub already proven
equivalent — at their own addresses, or the invoke jumps into emptiness and the "match" is
meaningless. This is why classification (leaf / caller / dispatch) precedes the test, and why the
closure schedule prefers units whose callee-closure is already G4.

## Honest limits

A differential/bench result proves the reconstruction matches the original **on the witnessed
inputs/branches, cold**. It does not prove un-witnessed paths, nor behaviour under full
boot/therapy state (which may be HW-gated). G3 closure does not establish linking or execution.
G4-recon closure reduces some uncertainty, but ABI, shared state, layout, and bench setup may
still cause mismatches. Static graphs can omit indirect edges: record unresolved dispatch in
`unknown_calls` and review completeness before relying on readiness suggestions.
