"""AST signals are evidence for reviewed structure, never keyword-based completion."""
import importlib.util
from pathlib import Path
import unittest

def module():
    p=Path(__file__).resolve().parents[1]/'scripts/source_structure.py'
    s=importlib.util.spec_from_file_location('source_structure_test',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class StructureTests(unittest.TestCase):
    def test_valid_straight_line_function_needs_no_branch_or_loop(self):
        r=module().analyze('int f(int x){return x+1;}','f')
        self.assertTrue(r['has_body']);self.assertEqual(r['branches'],0)
        self.assertFalse(r['semantic_truth_verified'])
    def test_descriptor_is_not_a_function_body(self):
        with self.assertRaises(ValueError):module().analyze('struct descriptor { int x; };','f')
    def test_dummy_if_does_not_establish_structure(self):
        r=module().analyze('int f(int x){if(0){x=42;}return x;}','f')
        self.assertIn('constant_condition',r['signals']);self.assertFalse(r['completion_authorized'])
    def test_register_bank_is_a_review_signal_not_automatic_truth(self):
        r=module().analyze('int f(int x){int r0,r1,r2,r3;r0=x;r1=r0;r2=r1;r3=r2;return r3;}','f')
        self.assertIn('register_bank',r['signals'])
    def test_goto_is_not_unconditionally_rejected(self):
        r=module().analyze('int f(int x){if(x)goto out;x=1;out:return x;}','f')
        self.assertEqual(r['gotos'],1);self.assertTrue(r['has_body'])
    def test_direct_and_indirect_calls_distinguished(self):
        r=module().analyze('int g(int);int f(int x){int (*p)(int)=g;return p(x);}','f')
        self.assertTrue(r['indirect_calls'])
    def test_missing_or_wrong_symbol_not_accepted(self):
        with self.assertRaises(ValueError):module().analyze('int other(){return 0;}','f')
    def test_invalid_c_is_not_relabelled_readable(self):
        with self.assertRaises(ValueError):module().analyze('int f( broken','f')

if __name__=='__main__':unittest.main()
