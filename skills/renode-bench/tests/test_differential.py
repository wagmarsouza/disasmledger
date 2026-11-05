import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/differential.py"
spec = importlib.util.spec_from_file_location("differential", SCRIPT)
diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diff)

TRAP = 0x20000080
BLOB = b"\x00\xbf\x70\x47"  # arbitrary; the fake invokes below never execute it


def adder(fn, regs, seeds, reads, steps):
    # Simulates a faithful stock leaf f(a, b) = a + b, with a clean return.
    return {"pc": TRAP, "reg0": (regs.get(0, 0) + regs.get(1, 0)) & 0xFFFFFFFF}


def subtractor(fn, regs, seeds, reads, steps):
    # A WRONG model: returns a - b.
    return {"pc": TRAP, "reg0": (regs.get(0, 0) - regs.get(1, 0)) & 0xFFFFFFFF}


def two_cases():
    return [
        dict(regs={0: 2, 1: 3}, reads=["pc", ("reg", 0)], expect={"pc": TRAP, "reg0": 5}, name="2+3"),
        dict(regs={0: 10, 1: 7}, reads=["pc", ("reg", 0)], expect={"pc": TRAP, "reg0": 17}, name="10+7"),
    ]


class DifferentialTests(unittest.TestCase):
    def reject(self, code, call):
        with self.assertRaises(diff.DifferentialError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_faithful_reconstruction_matches(self):
        self.assertTrue(diff.differential("ok", two_cases(), adder, blob=BLOB,
                                          clean_pc=TRAP, print_report=False))

    def test_wrong_reconstruction_is_rejected(self):
        self.assertFalse(diff.differential("bad", two_cases(), subtractor, blob=BLOB,
                                           clean_pc=TRAP, print_report=False))

    def test_dirty_return_fails_even_if_values_match(self):
        def dirty(fn, regs, seeds, reads, steps):
            return {"pc": 0x08001234, "reg0": (regs.get(0, 0) + regs.get(1, 0)) & 0xFFFFFFFF}
        self.assertFalse(diff.differential("dirty", two_cases(), dirty, blob=BLOB,
                                           clean_pc=TRAP, print_report=False))

    def test_single_witness_refused(self):
        self.reject("WITNESS", lambda: diff.differential("one", two_cases()[:1], adder, blob=BLOB))

    def test_non_discriminating_witnesses_refused(self):
        same = [two_cases()[0], dict(two_cases()[0])]  # identical expectations
        self.reject("WITNESS", lambda: diff.differential("same", same, adder, blob=BLOB))

    def test_requires_exactly_one_of_src_or_blob(self):
        self.reject("INPUT", lambda: diff.differential("both", two_cases(), adder, cpp_src="x", blob=BLOB))
        self.reject("INPUT", lambda: diff.differential("neither", two_cases(), adder))

    def test_blob_seeds_pack_little_endian_and_pad(self):
        seeds = diff.blob_seeds(b"\x01\x02\x03\x04\x05", 0x20004000)
        self.assertEqual(seeds[0], (0x20004000, 0x04030201, "dword"))
        # trailing partial word is right-padded with zeros
        self.assertEqual(seeds[1], (0x20004004, 0x00000005, "dword"))

    def test_distinct_expectations_counts_nontrivial(self):
        self.assertEqual(diff.distinct_expectations(two_cases()), 2)
        self.assertEqual(diff.distinct_expectations([{"expect": {"pc": TRAP}}]), 0)

    def test_blob_seeds_cover_the_whole_blob(self):
        blob = bytes(range(16))
        self.assertEqual(len(diff.blob_seeds(blob, 0x20000000)), 4)

    def test_cli_selftest_is_green(self):
        run = subprocess.run([sys.executable, "-B", str(SCRIPT), "--selftest"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("SELFTEST OK", run.stdout)


if __name__ == "__main__":
    unittest.main()
