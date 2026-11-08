# Using the Renode bench

## Target preparation

Before writing the bench, document the firmware's origin and SHA-256. Confirm the architecture, instruction mode, endianness, memory map, load offset or address, reset vector or initial PC/SP, and required peripherals. If an item is not established, label it as a hypothesis and prepare a test that can refute it.

Use a dedicated bench directory separate from original binaries. Keep `.resc`, `.repl`, logs, traces, and reports together. Avoid absolute paths in artifacts intended for other machines; inject real paths into a local copy or use variables supported by your workflow.

The `.repl` file is part of the evidence. A correct CPU model with missing peripherals may send firmware into loops, safe failures, or artificial paths. Document omitted peripherals and expected behaviour in their absence.

## Headless execution

On Windows:

```powershell
$renode = 'C:\Program Files\Renode\bin\Renode.exe'
& $renode --disable-gui --console 'C:\project\bench\boot-trace.resc'
```

On other systems, adjust the executable path. Use the installed version's supported mechanism to verify its version before comparing results across machines. Apply an external process timeout so a stalled bench cannot run indefinitely. Capture stdout, stderr, and the exit code. A timeout leaves the run outcome unknown until generated files are reconciled.

`:name:` and `:description:` metadata in `.resc` files must remain on one line. Use `#` for longer comments. End headless scripts with `quit`. Check syntax against the documentation for the installed version because monitor and tracing APIs may change.

## Hooks and injections

Prefer an initial run without hooks. A hook may observe, stop, or change state, but each change narrows the conclusion. Record its address, purpose, precondition, register or memory change, stopping condition, and justification.

Do not use hooks to cross a security boundary that the user has not authorised. When an authorised bypass is required to test a later component, place an explicit stop before any out-of-scope region and disclose that the path was forced. Behaviour after an injection does not represent natural boot behaviour.

## Trace interpretation

The analyser groups nearby transitions into blocks using a configurable distance. This is a navigation heuristic, not an instruction decoder or control-flow graph. Frequent loops may represent waiting, an error, a scheduler, or a model artifact. An apparent jump may be normal flow, an exception, or an alignment or ISA problem.

Correlate addresses with static analysis configured for the same binary, map, and mode. Distinguish:

- observed address;
- decoded instruction;
- candidate function or boundary;
- semantic hypothesis;
- behaviour confirmed by a test.

Do not count the same reformatted trace as independent evidence. When comparing configurations, preserve both datasets, their hashes and parameters, and the criteria selected in advance.

## Differential recompile-and-bench

A bench normally characterises the *original* function. The differential harness
([scripts/differential.py](../scripts/differential.py)) verifies a *reconstruction* instead: it
compares your recompiled C++ with the stock witnesses, catching observable mismatches that a
clean compile may miss.

The loop: compile the candidate C++ to a position-independent Thumb `.text` blob with the target's
real cross-toolchain; load the blob into RAM at a base address; forced-invoke it at that base on the
same bench; and compare its outputs to the witnesses already established for the stock function. The
harness enforces the two-witness discipline — at least two witnesses on different branches or outputs,
plus a clean return — and refuses a single or non-discriminating witness set. A match supports the
reconstruction only under the witnessed conditions, and nothing more. A mismatch needs investigation
of the reconstruction, ABI, setup and bench; it does not establish an exclusive fault cause.

The harness owns only the generic parts (compile, lay the blob in RAM, compare under the discipline).
Execution is yours to supply as an `invoke(fn, regs, seeds, reads, steps) -> {label: int}` callable,
where `label` is `pc`, `reg<N>`, or `mem_<ADDR8X>` and `seeds` is `[(addr, value, size)]`. Route a
pure-logic leaf to a CPU-only emulator (Unicorn), and a unit bound to peripherals or a boot/therapy
context to Renode.

Honest bound: a RAM-body comparison requires a position-independent blob to be interpretable — a
leaf with no absolute literal-pool reference and no call to an address not loaded in the same space.
For a caller, load its callees, or a stub already proven equivalent, at their own addresses first, or
the invoke jumps into emptiness and the match is meaningless. Classify the unit before trusting a pass,
and record the toolchain, flags, emulator, and version as part of the evidence.

For explicit support/unknown/unsupported requirements and versioned context preflight, read
[executor-capabilities.md](executor-capabilities.md). It reuses the same differential comparison
and never replaces it with a capability claim, chooses a fallback or grants permission to execute.

## Integration with a long-running harness

In a controlled mission, separate acquisition from validation. Renode execution may generate files; `check` should read frozen artifacts and verify hashes, format, and expectations. Do not perform mutable generation inside a check that promises stable, read-only evidence.

Record the evidence with a claim ceiling: emulation method, platform, injections, sample, observation points, and what was not tested. Report coverage with a defined denominator. If the path inventory is unknown, overall coverage is indeterminate.
