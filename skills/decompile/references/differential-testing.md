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

- **C1 — closure (required).** The transitive closure of `f`'s callees is already G3+ (ideally
  G4). Otherwise the test runs against stubs/unknowns and measures your own assumptions —
  zero information.
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
(`{fn: "G0".."G4"}`) and reports, read-only:

- **testable_now** — not-done units whose callee-closure is complete (C1 satisfied): the units
  you can differentially test immediately as you reconstruct them.
- **top_leverage** — undone helpers ranked by number of distinct undone callers (C2): where a
  single reconstruction propagates furthest.
- **ft_g3_closed / ft_g4_closed** — counts of units whose closure is fully G3+ / fully G4; the
  G4-closed set localizes a mismatch to the unit itself (callees already proven).
- **totals / coverage flags** — done over inventoried, plus an indeterminate flag when any
  callee is ungraded. Cycles among undone units resolve to "not closed", never an infinite loop.

It does not disassemble, execute, grade, or promote. It is a scheduler: it tells you *what is
worth testing next and why*, not whether anything is correct. The grades it reads come from the
gates (compile, match, bench); the graph comes from the call-graph backend.

## Honest limits

A differential/bench result proves the reconstruction matches the original **on the witnessed
inputs/branches, cold**. It does not prove un-witnessed paths, nor behaviour under full
boot/therapy state (which may be HW-gated). A G3-closed closure links and runs, but a mismatch
could lie in a G3 callee; a **G4-closed** closure (callees bench-proven) localizes the fault to
`f` — prefer it when choosing what to certify.
