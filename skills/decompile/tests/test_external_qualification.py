"""Generic adapters are executed/bound; unknown proofs and analytical labels cannot inflate counts."""
import json
import unittest
from external_qualification_fixture import ExternalFixture,sha

class ExternalQualificationTests(unittest.TestCase):
    def test_synthetic_formal_protocol_binds_both_original_and_candidate(self):
        with ExternalFixture() as f:self.assertEqual(f.qmeasure()['claimed_verified'],1)
    def test_analysis_and_build_milestones_never_enter_the_reconstructed_counter(self):
        for category in ('analysis','mechanical-translation','recompilable'):
            with self.subTest(category=category),ExternalFixture(category,method='none') as f:
                result=f.qmeasure();self.assertEqual(result['claimed_verified'],0)
                row=result['units'][0];proof=json.loads((f.root/row['artifacts']['qualification_receipt']['path']).read_text())
                self.assertTrue(proof['assessment']['category_satisfied']);self.assertFalse(proof['assessment']['reconstructed_eligible'])
                self.assertEqual(row['gates']['D-f'],'unknown')
    def test_unknown_or_vacuous_equivalence_does_not_become_a_pass(self):
        for fault in ('unknown','weak','same_negative','wrong_source','weaken_assumptions','omit_build','cached','old_control','invented_corpus'):
            with self.subTest(fault=fault),ExternalFixture() as f:
                (f.root/'external-fault.txt').write_text(fault)
                self.assertEqual(f.qmeasure()['claimed_verified'],0)
    def test_fresh_executed_adapter_cannot_supply_its_own_counter_or_duplicate_units(self):
        for fault in ('inflate','duplicate','old_run'):
            with self.subTest(fault=fault),ExternalFixture() as f:
                (f.root/'external-fault.txt').write_text(fault)
                with self.assertRaises(ValueError):f.qmeasure()
    def test_differential_protocol_requires_exact_executed_case_ids(self):
        with ExternalFixture(method='differential') as f:
            self.assertEqual(f.qmeasure()['claimed_verified'],1)
        with ExternalFixture(method='differential') as f:
            (f.root/'external-fault.txt').write_text('omitted_case')
            self.assertEqual(f.qmeasure()['claimed_verified'],0)
    def test_modified_approved_verifier_cannot_run_under_the_old_recipe(self):
        with ExternalFixture() as f:
            (f.root/'approved_verifier.py').write_text('raise SystemExit(0)')
            with self.assertRaises(ValueError):f.qmeasure()
    def test_original_image_cannot_be_approved_as_a_platform_to_hide_delegation(self):
        with ExternalFixture() as f:
            f.qprofile['dependencies']['platform_images']={'original-disguised':f.ref('stock.bin')};f.save_profile()
            with self.assertRaises(ValueError):f.qmeasure()
    def test_live_entrypoint_cannot_be_added_to_the_external_allowlist(self):
        with ExternalFixture() as f:
            f.qprofile['dependencies']['allowed_external_calls']=['f'];f.save_profile()
            with self.assertRaises(ValueError):f.qmeasure()

if __name__=='__main__':unittest.main()
