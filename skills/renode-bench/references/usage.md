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

## Integration with a long-running harness

In a controlled mission, separate acquisition from validation. Renode execution may generate files; `check` should read frozen artifacts and verify hashes, format, and expectations. Do not perform mutable generation inside a check that promises stable, read-only evidence.

Record the evidence with a claim ceiling: emulation method, platform, injections, sample, observation points, and what was not tested. Report coverage with a defined denominator. If the path inventory is unknown, overall coverage is indeterminate.
