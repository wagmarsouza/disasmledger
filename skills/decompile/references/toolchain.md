# Tool-per-stage routing

No single tool spans the pipeline, and the skill does not bundle any of them. This is the
routing map: which external tool fits which stage, and the claim each one may and may not
support. Install and license each tool yourself; treat every version and configuration as
part of the evidence.

## Map

| Stage | Tool(s) | Produces | Does NOT establish |
| --- | --- | --- | --- |
| Identity / map | file/binwalk, SVD-Loader, binary-analysis-profile | hash, segments, peripheral names | architecture legitimacy, behaviour |
| Triage / inventory | capstone (fast linear/targeted disasm), the call graph | boundaries, structure classes, fan-in | function-boundary proof, semantics |
| Call graph / closure | Ghidra/pyghidra headless, pyghidra-mcp, `closure.py` | adjacency, fan-in, FT (closed) sets | that an edge is exercised at runtime |
| Deep decompile | Ghidra / pyghidra (interactive or headless) | pseudocode, types, xrefs | correctness of the pseudocode |
| Residual indirect-edge investigation | angr static/symbolic CFG analyses, when justified | candidate/resolved indirect targets with assumptions | that all targets were found or a path executed |
| Transcription gate | arm-none-eabi-gcc/clang (`-c -Wall -Wextra`) | a compile (G3) | behaviour (compiling ≠ correct) |
| Byte/instruction match | objdiff, asm-differ, decomp-permuter | an instruction diff / a match (M) | behaviour beyond the matched bytes |
| Bench / behaviour | Unicorn (CPU-only) OR Renode (peripherals), renode-bench | a two-witness observation (G4) | hardware behaviour, universality |

## Choosing the disassembly/decompile backend

- **capstone** for fast, scriptable, targeted disassembly and for structural scans
  (fan-in, instruction patterns, candidate boundaries). Cheap and embeddable; no decompiler.
- **Ghidra / pyghidra (headless)** when pattern/signature search fails and you need the
  **call graph** or a data-flow-heavy function that has no distinct signature — e.g. a control
  loop reached only by indirect dispatch. A pattern match finds the function with a shape; a
  call graph finds the function by its position in the program. Reuse an existing
  call-graph exporter (for example a headless `ExportCalls` script or `pyghidra-mcp`) rather
  than rebuilding one; feed its JSON to `closure.py`.
- **SVD-Loader** early, to name memory-mapped peripheral registers from the vendor SVD. It
  turns anonymous MMIO offsets into names and saves manual datasheet cross-referencing; it
  does not prove how the firmware uses them.

## Choosing the emulator: Unicorn vs Renode

- **Unicorn** (CPU-only) for **pure-logic units** that touch no peripherals: set up memory,
  start at the function address, stop after return, read the result. Fast and cheap — the right
  tool for the mass of leaf and arithmetic units. It models no peripherals, so anything that
  reads a sensor, drives a timer, or depends on an interrupt will not run meaningfully.
- **Renode** (whole device, peripheral models) for units bound to peripherals or to an active
  therapy/boot context: sensor→controller→actuator loops, ISR-dispatched ticks, boot-gated
  code. Use renode-bench; prefer boot-then-invoke or forced-invoke with declared injections.
  Emulation is a model, not hardware.

Both are forced-invoke in spirit: call the target directly rather than driving the whole UI.
Route a unit to Unicorn first if its triage class is pure-logic; escalate to Renode when it
reads or writes peripherals, or when passive execution cannot reach it.

## The compile gate and the match rung

- The **compile gate** is the mechanical definition of G3: the transcription must compile
  under the real cross-toolchain with layout `_Static_assert`s. A unit that only "reads right"
  is G2. Keep the exact compiler, flags, and version in the evidence.
- **objdiff / asm-differ** diff the compiled object against the original instructions; a clean
  diff is the M rung. When the code is functionally correct but does not match, a
  **permuter** searches semantically equivalent forms. Matching is strong, deterministic
  evidence for pure-logic units; it still says nothing about paths the inputs did not reach.

## A note on LLM-assisted decompilation

Model-produced pseudocode is a candidate, never a fact. Published results show naive
LLM decompilation can score *below* a raw decompiler, and that the reliable pattern is a
**constraint-guided loop**: produce, compile, diff/bench, repair from the error, repeat. That
loop is exactly the compile gate + match + two-witness bench in this skill. Use a model to
draft or refine a transcription; let the gate and the bench decide, and quarantine any
agent's claim until it is independently checked.

## Reuse, focused analysis and capability evidence

Read [graph-provenance.md](graph-provenance.md) for a focused angr workflow and optional physical
export binding. Start with the existing graph's unresolved calls, not a second full-image inventory.
Recovered targets may still be incomplete. Annotate inferred, tool-declared resolved and observed
origins without erasing unresolved sites or counting graph growth as a grade promotion.

Capstone decodes bytes under the chosen ISA/mode; successful decoding alone proves neither that
the bytes are code nor a true function boundary. Its [SKIPDATA documentation](https://www.capstone-engine.org/skipdata.html)
explicitly warns about that distinction. Treat discovered inventory size as a candidate denominator
until reviewed. Cross-check boundaries with map, control flow, references and other evidence.

Initial exports can be reused only while relevant inputs remain compatible. Existing
binary-analysis-profile already governs hashes, maps, unit identities and changed configurations:
reuse those controls instead of a second identity system. A matching label or index does not prove
cross-build identity, and a tool database mutation does not itself establish changed semantics.

Choose an executor by declared, evidenced capabilities for this configuration, not an unconditional
float/MMIO rule. ARM VFP setup can matter in Unicorn; peripheral/boot requirements may justify a
different model. Use the optional [bench capability guide](../../renode-bench/references/executor-capabilities.md).
Neither executor is final authority for untested real-hardware behavior. No automatic dispatch,
fallback, engine installation or new census/review scheduler is introduced here.
