# Stage pipeline and grade ladder

A decompilation mission is a sequence of stages, each ending in a gate. Work advances
only when the gate passes. The pipeline and the ladder are the same discipline seen two
ways: the pipeline is what you do; the ladder is what a result is allowed to claim.

## The grade ladder

| Grade | Meaning | Gate that must pass to reach it |
| --- | --- | --- |
| **G0** | Bogus, empty, or not a real unit | Confirmed absent/placeholder; excluded from the live denominator |
| **G1** | Raw: disassembly and control-flow only | Boundaries and instructions decoded; still only bytes |
| **G2** | Semantics: a described model (roles, offsets, a descriptor) | A coherent reading exists — but understanding is **not** reconstruction |
| **G3** | Compiles: source that reproduces the logic | The source **compiles** under the real toolchain, with layout `_Static_assert`s |
| **G4** | Behaviour: bench-confirmed | Runs on the bench with **two witnesses on different branches/outputs** and a positive control |

Optional rung **M (match)** sits between G3 and G4: the compiled output is diffed against
the original instructions (objdiff/asm-differ) and, when functionally correct but not
byte-identical, a permuter searches equivalent forms. M is a deterministic, cheap check
for pure-logic units; G4 is the behavioural witness for units with state or peripherals.

Rules that keep the ladder honest:
- The ladder is not an automatic escalator. A narrow G4 may answer less than a precise G2
  about a different question. State what each grade does and does not cover.
- "Compiles" (G3) catches syntax and types, nothing about behaviour. Only M or G4 catches a
  wrong model that still compiles. Never promote G3 to a behavioural claim.
- Two witnesses are the structural minimum, not semantic sufficiency: they must exercise
  **different branches or outputs**, with a known positive control, or the bench proves nothing.
- Coverage is verified units over total inventoried units. Unknown total ⇒ indeterminate.
  Do not fabricate a "% understood" from names, line counts, or cycle counts.

## The stage pipeline

### 1. Target identity and map
Fix identity and the address map (binary-analysis-profile). No decode before the target is
frozen. Keep ISA/endianness/base uncertainty explicit until discriminated.

### 2. Inventory and triage (classify before promote)
Build a versioned inventory and partition each unit by real structure: leaf (no callees),
caller, indirect dispatch (vtable/jump table), pool/accessor, float/VFP, data/table. The
partition decides the tool and the reachable grade. A bulk pass that assigns a grade before
classifying is how grade inflation starts; split first, grade second.

### 3. Type model per cluster
Before transcribing a cluster, write its type hypothesis — structs, offsets, callee
signatures — in a shared header. Reconstructing one member often corrects the signatures the
whole cluster reuses, so the model pays for itself and prevents divergent per-unit guesses.

### 4. Transcription to source (→ G3 via the compile gate)
Write code that reproduces loads, stores, offsets, and constants — a body, not a descriptor
and not a paraphrase. Run the compile gate (`-c -Wall -Wextra`). A descriptor that does not
compile is G2, not G3. This is the mechanical boundary that makes "G3 = compiles" checkable.

### 5. Match and/or bench (→ M, → G4)
For pure-logic units, diff the compiled bytes against the original (M). For units with state,
peripherals, or control flow that bytes alone cannot settle, run the bench (renode-bench)
cold forced-invoke with two discriminating witnesses and a positive control (→ G4). Record
inputs, initial state, injections, stubs, stopping condition, and failures; bound the claim to
exactly what was exercised.

### 6. Promotion and propagation
Promote only to the grade whose gate passed. Record the bounded claim, grade, gate, evidence,
denominator, contradictions, and next step. If a result falls, retract it and **propagate the
retraction in the same pass** to every dependent result, pointer, and schedule entry. When a
result advances, update the cold-start pointers that depend on it too.

### 7. Reconcile and resume
Keep identity, hypothesis, evidence, contradictions, and the next discriminating test in the
capsule; check freshness before reuse. Reconcile the live count against the maps/inventory
every cycle so drift is detectable. On a new firmware version, restate identity and re-check
applicability — a matching name does not transfer evidence.

## Anti-patterns (the failure modes this ladder exists to prevent)

- **Naming by form/position/arguments instead of decoding** — an allocator that returns its
  second argument, a CRC mislabelled as a writer. Decode the body; a plausible name is a
  candidate, not a finding.
- **Crossing an id/index space between firmwares or namespaces** — the spaces are often
  permutations, not shifts. Cross by proven label; derive, never inherit, a number.
- **Chasing the wrong symptom** — resolving the question the user did not ask. Register the
  user's exact words and consult the screen/ground truth before inferring.
- **Searching the wrong layer** — looking for a control law in the display/menu code, or for a
  value where the symptom is visibility. Let the symptom pick the layer.
- **Build-before-understand** — emitting a patch or a large graft on an unproven model; the
  most expensive error is shipping the *wrong feature*, not a bug in the right one.
- **Inflating completeness** — declaring "complete" on the framework while the core does not
  run, or marking a grade without its gate. Completeness is of the core that runs.
- **Declaring impossible with the solution on disk** — inventory existing artifacts and tools
  before calling anything HW-only or unreachable.
- **Circles and lazy holds** — recircling a residual with a weaker instrument, or reporting a
  floor while real work remains. Stop a circle; name the block; surface it.
