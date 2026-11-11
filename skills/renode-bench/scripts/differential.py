"""Differential recompile-and-bench harness: prove OUR recompiled C++ reproduces the STOCK
function on a bench, under the two-witness discipline.

This is the executor half of the DisasmLedger E7 loop; the scheduler half lives in the
decompile skill (`closure.py`, which says WHICH unit is worth testing). It moves a claim from
"the original function does X" (characterising the stock) to "OUR reconstruction does X"
(proving the transcription): it compiles our C++ body to a position-independent Thumb blob,
loads the blob into RAM at a base address, forced-invokes it on the bench, and checks the
outputs against the witnesses already established for the stock function.

WHAT IT OWNS vs WHAT IT DELEGATES
  It owns the generic, target-independent parts: compiling our C++ to a `.text` blob, laying
  the blob into RAM, and comparing outputs under the discrimination rule. It does NOT own the
  execution primitive -- that is emulator- and board-specific. You pass an `invoke` callable;
  Unicorn (CPU-only, for pure-logic leaves) or a Renode forced-invoke engine (for peripheral or
  boot-gated code) both satisfy the same contract. Record the toolchain, flags, emulator, and
  version: they are part of the evidence.

THE POSITION-INDEPENDENCE LIMIT (honest bound)
  A RAM-body comparison requires a position-independent blob to be interpretable: a leaf
  with no absolute literal-pool reference and no BL/BLX to an address that is not loaded in the
  same space. For a caller, load its callees too (or a stub already proven equivalent) at their
  own addresses, or the invoke jumps into emptiness. A blob that fails this prints a match that
  means nothing. Classify the unit (leaf / caller / dispatch) before trusting a pass.

WHAT A PASS MEANS
  "Our recompiled body reproduces the stock on the witnessed inputs/branches, cold." It does NOT
prove un-witnessed paths, behaviour under live boot/therapy state, or semantic intent. A mismatch
requires review of reconstruction, ABI, setup and bench, not exclusive blame on the transcription.
Do not promote on mismatch.

Programmatic use (the invoke contract matches a forced-invoke engine's `invoke`):
    from differential import differential
    ok = differential("leaf 0x0806CF0C", cases, invoke=my_invoke,
                      cpp_src=OUR_CPP, base=0x20004000, clean_pc=0x20000080)

`invoke(fn, regs, seeds, reads, steps) -> {label: int}` where label is 'pc', 'reg<N>', or
'mem_<ADDR8X>', and seeds is [(addr, value, 'byte'|'word'|'dword')]. The harness prepends the
seeds that load the blob; your invoke only has to execute at `fn` and read the observables back.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

GPP = os.environ.get("ARM_GPP", "arm-none-eabi-g++")
OBJCOPY = os.environ.get("ARM_OBJCOPY", "arm-none-eabi-objcopy")
# Cortex-M4F defaults. Override per target; they are evidence, so record what you used.
DEFAULT_CFLAGS = ["-O2", "-c", "-std=c++11", "-mcpu=cortex-m4", "-mthumb",
                  "-ffreestanding", "-fno-exceptions"]


class DifferentialError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def compile_blob(cpp_src, cflags=None, gpp=GPP, objcopy=OBJCOPY):
    """Compile a C++ source into a raw Thumb .text blob (bytes). Needs the ARM cross-toolchain.

    The source must define the target with the EXACT ABI of the stock function (args in r0,r1,...
    as the original expects), e.g. `extern "C" void f(void* p, unsigned mask, unsigned flag){...}`.
    """
    flags = list(DEFAULT_CFLAGS if cflags is None else cflags)
    d = tempfile.mkdtemp(prefix="disasm-diff-")
    cpp = os.path.join(d, "f.cpp")
    obj = os.path.join(d, "f.o")
    binf = os.path.join(d, "f.bin")
    with open(cpp, "w", encoding="utf-8") as fh:
        fh.write(cpp_src)
    subprocess.check_call([gpp] + flags + ["-o", obj, cpp])
    subprocess.check_call([objcopy, "-O", "binary", "-j", ".text", obj, binf])
    with open(binf, "rb") as fh:
        return fh.read()


def blob_seeds(blob, base):
    """Seeds that load `blob` into RAM at `base`, little-endian, one word at a time.

    The last partial word is right-padded with zero bytes so a blob whose length is not a
    multiple of four still lands intact.
    """
    return [(base + i, struct.unpack("<I", blob[i:i + 4].ljust(4, b"\0"))[0], "dword")
            for i in range(0, len(blob), 4)]


def distinct_expectations(cases):
    """Count the DISTINCT non-trivial expected-output tuples across cases (ignores 'pc').

    Two witnesses that expect the same output do not discriminate a wrong model from a right one;
    the discrimination rule (R80 C3) needs at least two different expectations.
    """
    seen = set()
    for c in cases:
        exp = c.get("expect", {})
        key = tuple(sorted((k, v) for k, v in exp.items() if k != "pc"))
        if key:
            seen.add(key)
    return len(seen)


def differential(title, cases, invoke, cpp_src=None, blob=None, base=0x20004000,
                 clean_pc=None, cflags=None, steps=60, print_report=True, executor_context=None, preservation=None):
    """Prove OUR reconstruction reproduces the stock witnesses on the bench.

    Exactly one of `cpp_src` (compiled here) or `blob` (a precompiled Thumb .text) is given.
    `cases`: list of {regs, seeds, reads, expect, name}. `expect` maps invoke output labels to the
    STOCK witness values. Requires >=2 cases on >=2 distinct outputs/branches, else raises
    DifferentialError. `invoke` is the pluggable bench primitive. `clean_pc`, when set and a case
    expects 'pc', must be hit (the planted trap) for that case to count as a clean return.

    Returns True only if every case matches and the discrimination minimum holds. A pass is bounded
    to the witnessed inputs/branches, cold; it is not semantic truth. On mismatch: fix, do not promote.

    Optional executor_context={project, manifest, requirements} uses the bundled capability assessor.
    It prevents invocation for unsupported/unknown requirements and rejects a stale context. It does
    not authenticate that the supplied invoke actually uses that executor. Legacy calls are unchanged.
    """
    if (cpp_src is None) == (blob is None):
        raise DifferentialError("INPUT", "pass exactly one of cpp_src or blob")
    if len(cases) < 2:
        raise DifferentialError("WITNESS", "need at least two witnesses (two-witness discipline)")
    if distinct_expectations(cases) < 2:
        raise DifferentialError("WITNESS", "witnesses must exercise at least two distinct outputs/branches")

    recorder = None
    if preservation is not None:
        helper = Path(__file__).with_name('preservation_receipt.py')
        spec = importlib.util.spec_from_file_location('disasm_preservation_receipt', helper)
        receipt = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(receipt)
            recorder = receipt.Recorder(preservation, cases)
        except (ValueError, TypeError, OSError, ImportError) as error:
            raise DifferentialError('PRESERVATION', str(error)) from error

    assessment, initial_identity = None, None
    if executor_context is not None:
        if not isinstance(executor_context, dict) or set(executor_context) != {'project', 'manifest', 'requirements'}:
            raise DifferentialError('CAPABILITY', 'executor_context requires project, manifest and requirements')
        helper = Path(__file__).with_name('executor_capabilities.py')
        spec = importlib.util.spec_from_file_location('disasm_executor_capabilities', helper)
        capability = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(capability)
        except (OSError, ImportError) as error:
            raise DifferentialError('CAPABILITY', 'Bundled capability assessor is unavailable; contextual execution refused') from error

        def recheck_context():
            try:
                report = capability.assess(executor_context['project'], executor_context['manifest'], executor_context['requirements'])
            except capability.CapabilityError as error:
                raise DifferentialError(error.code, str(error)) from error
            if not report['eligible']:
                raise DifferentialError('CAPABILITY', 'Required capabilities are unsupported or unknown; inspect assessment before choosing an executor')
            identity = (report['manifest_sha256'], report['requirements_sha256'])
            if initial_identity is not None and identity != initial_identity:
                raise DifferentialError('CAPABILITY_STALE', 'Executor/requirements changed during invocation; reconcile outcome without blind replay')
            return report, identity
        assessment, initial_identity = recheck_context()

    body = blob if blob is not None else compile_blob(cpp_src, cflags)
    load = blob_seeds(body, base)
    rows, allok = [], True
    for c in cases:
        if recorder is not None:
            try: recorder.reset()
            except (ValueError, OSError) as error:
                raise DifferentialError('PRESERVATION', str(error)) from error
        if executor_context is not None:
            recheck_context()
        seeds = load + list(c.get("seeds", []))
        got = invoke(fn=base, regs=c.get("regs", {}), seeds=seeds,
                     reads=c.get("reads", ["pc"]), steps=c.get("steps", steps))
        if executor_context is not None:
            recheck_context()
        exp = c.get("expect", {})
        clean = True
        if clean_pc is not None and "pc" in exp:
            clean = got.get("pc") == clean_pc
        match = clean and all(got.get(k) == v for k, v in exp.items())
        allok = allok and match
        rows.append((c.get("name", ""), got, exp, match))

    if recorder is not None:
        try: recorder.finish(rows)
        except (ValueError, TypeError, OSError) as error:
            raise DifferentialError('PRESERVATION', str(error)) from error

    if print_report:
        print("=== %s [differential: OUR recompiled C++ vs stock] blob=%dB ===" % (title, len(body)))
        if assessment is not None:
            print('  Capability context:', assessment['manifest_sha256'],
                  'requirements:', assessment['requirements_sha256'], '(declarations checked; runtime not authenticated)')
        for i, (name, got, exp, match) in enumerate(rows, 1):
            shown = {k: (hex(got.get(k)) if isinstance(got.get(k), int) else got.get(k)) for k in exp}
            print("  W%d %-12s got=%s [expect=%s] %s" % (i, name, shown, exp, "OK" if match else "FAIL"))
        print("  OUR RECOMPILED == STOCK:", allok)
        if not allok:
            print("  >> Observed mismatch: review reconstruction, ABI, initial state and bench configuration. "
                  "Do not promote or infer an exclusive fault cause.")
    return allok


def _selftest():
    """Offline check of the compare + discipline logic. No bench, no cross-toolchain.

    A fake invoke simulates a stock leaf f(a, b) = a + b by reading r0/r1 from the case regs and
    returning the sum in reg0 with a clean return. It proves the harness ACCEPTS a faithful model,
    REJECTS a wrong one, and ENFORCES the two-witness discrimination -- the logic the real bench relies on.
    """
    TRAP = 0x20000080

    def fake_invoke(fn, regs, seeds, reads, steps):
        return {"pc": TRAP, "reg0": (regs.get(0, 0) + regs.get(1, 0)) & 0xFFFFFFFF}

    def fake_invoke_wrong(fn, regs, seeds, reads, steps):
        return {"pc": TRAP, "reg0": (regs.get(0, 0) - regs.get(1, 0)) & 0xFFFFFFFF}

    cases = [
        dict(regs={0: 2, 1: 3}, reads=["pc", ("reg", 0)], expect={"pc": TRAP, "reg0": 5}, name="2+3"),
        dict(regs={0: 10, 1: 7}, reads=["pc", ("reg", 0)], expect={"pc": TRAP, "reg0": 17}, name="10+7"),
    ]
    blob = b"\x00\xbf\x70\x47"  # arbitrary bytes; the fake invoke does not execute them

    checks = {
        "faithful model matches": differential("selftest+", cases, fake_invoke, blob=blob,
                                               clean_pc=TRAP, print_report=False) is True,
        "wrong model is rejected": differential("selftest-", cases, fake_invoke_wrong, blob=blob,
                                                clean_pc=TRAP, print_report=False) is False,
    }
    for raiser, why in (
        (lambda: differential("one", cases[:1], fake_invoke, blob=blob), "one witness refused"),
        (lambda: differential("same", [cases[0], dict(cases[0])], fake_invoke, blob=blob),
         "non-discriminating witnesses refused"),
        (lambda: differential("both", cases, fake_invoke, cpp_src="x", blob=blob), "ambiguous input refused"),
    ):
        try:
            raiser()
            checks[why] = False
        except DifferentialError:
            checks[why] = True

    for label, ok in checks.items():
        print(("PASS" if ok else "FAIL") + " - " + label)
    good = all(checks.values())
    print("SELFTEST OK - differential compare/discipline logic verified (no bench, no toolchain)"
          if good else "SELFTEST FAILED")
    return 0 if good else 1


def main():
    ap = argparse.ArgumentParser(description="DisasmLedger differential recompile-and-bench harness")
    ap.add_argument("--selftest", action="store_true",
                    help="run the offline compare/discipline self-check (no bench, no toolchain)")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    ap.print_help()
    print("\nThis harness is used programmatically: import `differential` and pass your bench "
          "`invoke` callable. See the module docstring and references/usage.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
