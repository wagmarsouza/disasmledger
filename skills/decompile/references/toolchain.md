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
