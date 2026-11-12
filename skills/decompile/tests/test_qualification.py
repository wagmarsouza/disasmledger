"""Inflation and target-profile regressions; compiler/executor here are synthetic."""
import copy
from pathlib import Path
import json
import unittest
from qualification_fixture import QualificationFixture,load,sha

class QualificationTests(unittest.TestCase):
    def test_physical_platform_and_tool_resources_are_live_evidence(self):
        with QualificationFixture() as f:
            (f.root/'rom.bin').write_bytes(b'approved independent platform')
            ref=f.ref('rom.bin')
            f.config['profile']['platform_images']={'rom':ref};f.save_backend()
            f.qprofile['dependencies']['platform_images']={'rom':ref};f.save_profile()
            result=f.qmeasure();self.assertEqual(result['claimed_verified'],1)
            refs=result['units'][0]['artifacts']
            self.assertIn(ref,list(refs.values()))
            self.assertIn(f.ref('tool.py'),list(refs.values()))
            self.assertIn(f.ref('stock.bin'),list(refs.values()))
    def test_transitive_dependency_sources_are_bound_and_cycles_close_without_bonus(self):
        with QualificationFixture() as f:
            q=load('qualification').Qualification(f.root,'contract.json','binding-only','a'*64)
            (f.root/'src/V.c').write_text('int v(void){return 1;}')
            (f.root/'src/W.c').write_text('int w(void){return 2;}')
            q.units['U1']['depends_on']=['V']
            q.units['V']={'deliverable':'src/V.c','depends_on':['W']}
            q.units['W']={'deliverable':'src/W.c','depends_on':['U1']}
            refs=q.bindings('U1')
            self.assertIn(f.ref('src/W.c'),list(refs.values()))
            old=f.ref('src/W.c');(f.root/'src/W.c').write_text('changed dependency')
            with self.assertRaises(ValueError):q.bound(old)
            close=load('closure').qualified_units
            self.assertEqual(close({'a','b'},{'a':['b'],'b':['a']}),{'a','b'})
            self.assertEqual(close({'a'},{'a':['b'],'b':[]}),set())
    def test_six_current_gates_qualify_one_stable_unit(self):
        with QualificationFixture() as f:
            result=f.qmeasure();self.assertEqual(result['claimed_verified'],1)
            self.assertEqual(set(result['units'][0]['gates']),{'D-a','D-b','D-c','D-d','D-e','D-f'})
            proof=json.loads((f.root/result['units'][0]['artifacts']['qualification_receipt']['path']).read_text())
            self.assertTrue(proof['assessment']['reconstructed_eligible']);self.assertTrue(proof['executed'])
    def test_renamed_registers_do_not_turn_a_reviewed_translation_into_structured_source(self):
        with QualificationFixture() as f:
            f.qreview['representation']='mechanical';f.write('reviews/U1.recovery.json',f.qreview)
            result=f.qmeasure();self.assertEqual(result['claimed_verified'],0)
            self.assertEqual(result['units'][0]['gates']['D-b'],'fail')
    def test_failed_unit_does_not_automatically_downgrade_its_category(self):
        with QualificationFixture() as f:
            f.corpus['fault']='original_call';f.write('witnesses/U1.json',f.corpus)
            result=f.qmeasure();self.assertEqual(result['claimed_verified'],0)
            proof=json.loads((f.root/result['units'][0]['artifacts']['qualification_receipt']['path']).read_text())
            self.assertEqual(proof['category'],'independent-validated');self.assertFalse(proof['assessment']['automatic_reclassification'])
    def test_review_cannot_silently_switch_the_predeclared_category(self):
        with QualificationFixture() as f:
            f.qreview['category']='analysis';f.write('reviews/U1.recovery.json',f.qreview)
            result=f.qmeasure();self.assertEqual(result['claimed_verified'],0)
    def test_known_placeholder_and_unresolved_operations_cannot_count(self):
        for fault in ('marker','unresolved','incomplete'):
            with self.subTest(fault=fault),QualificationFixture() as f:
                if fault=='marker':
                    (f.root/'src/U1.c').write_text('/* Could not recover */ int f(int x){return x+1;}')
                    f.review['source_sha256']=f.qreview['source_sha256']=sha(f.root/'src/U1.c')
                    f.write('reviews/U1.json',f.review)
                elif fault=='unresolved':f.qreview['unresolved_operations']=['missing indirect branch']
                else:f.qreview['body_complete']=False
                f.write('reviews/U1.recovery.json',f.qreview)
                result=f.qmeasure();self.assertEqual(result['claimed_verified'],0)
                self.assertEqual(result['units'][0]['gates']['D-d'],'fail')
    def test_goto_and_data_constant_are_not_universal_rejections(self):
        with QualificationFixture() as f:
            (f.root/'src/U1.c').write_text('int f(int x){int data=0x08001000;goto done;done:return x+1;}')
            f.review.update(source_sha256=sha(f.root/'src/U1.c'),acknowledged_signals=['goto_control_flow'])
            f.qreview['source_sha256']=sha(f.root/'src/U1.c')
            f.write('reviews/U1.json',f.review);f.write('reviews/U1.recovery.json',f.qreview)
            self.assertEqual(f.qmeasure()['claimed_verified'],1)
    def test_target_mismatch_and_unapproved_platform_fail_before_execution(self):
        with QualificationFixture() as f:
            f.qprofile['target']['architectures']=['ARM'];f.save_profile()
            with self.assertRaises(ValueError):f.qmeasure()
            self.assertFalse((f.root/'completion').exists())
    def test_inventoried_callee_cannot_be_relabelled_as_an_external_service(self):
        with QualificationFixture() as f:
            f.config['profile']['allowed_external_calls']=['f'];f.save_backend()
            f.qprofile['dependencies']['allowed_external_calls']=['f'];f.save_profile()
            with self.assertRaises(ValueError):f.qmeasure()
    def test_platform_boundary_in_backend_must_match_the_pinned_target_profile(self):
        with QualificationFixture() as f:
            f.config['profile']['allowed_external_calls']=['arbitrary_original'];f.save_backend()
            with self.assertRaises(ValueError):f.qmeasure()
    def test_missing_observable_and_missing_input_scenario_refuse_qualification(self):
        for fault in ('memory','scenario'):
            with self.subTest(fault=fault),QualificationFixture() as f:
                if fault=='memory':f.qprofile['validation']['observables'].append('memory')
                else:f.qprofile['validation']['required_scenarios']=['boundary']
                f.save_profile();self.assertEqual(f.qmeasure()['claimed_verified'],0)
    def test_weak_controls_and_wrong_execution_still_fail_the_new_gate(self):
        for fault in ('old_image','unknown_call','old_run','omitted','no_reset','all_faults'):
            with self.subTest(fault=fault),QualificationFixture() as f:
                f.corpus['fault']=fault;f.write('witnesses/U1.json',f.corpus)
                self.assertEqual(f.qmeasure()['claimed_verified'],0)
    def test_proof_is_reused_only_with_current_source_review_and_profile(self):
        with QualificationFixture() as f:
            first=f.qmeasure();f.write('previous.json',first)
            second=f.qmeasure(f.ref('previous.json'),run='reuse')
            old=first['units'][0]['artifacts']['completion_receipt']
            self.assertEqual(second['units'][0]['artifacts']['completion_receipt'],old)
            (f.root/'src/U1.c').write_text('int f(int x){return x+2;}')
            result=f.qmeasure(f.ref('previous.json'),run='drift');self.assertEqual(result['claimed_verified'],0)
    def test_profile_or_category_change_cannot_be_hidden_as_cache_revalidation(self):
        with QualificationFixture() as f:
            first=f.qmeasure();f.write('previous.json',first)
            f.contract['category']='analysis';f.save_contract()
            with self.assertRaises(ValueError):f.qmeasure(f.ref('previous.json'),run='downgrade')
    def test_audit_forces_actual_backend_reexecution(self):
        with QualificationFixture() as f:
            first=f.qmeasure();f.write('previous.json',first);f.write('selection.json',{'id':'plan','units':['U1']})
            result=load('qualification').audit(f.root,'contract.json','audit','a'*64,'selection.json',f.ref('previous.json'))
            self.assertEqual(result['recount_ids'],['U1']);self.assertTrue(result['units'][0]['executed'])
            self.assertTrue(result['controls']['healthy_passed']);self.assertTrue(result['controls']['known_bad_rejected'])
    def test_previous_grade_headline_cannot_promote_without_actual_source(self):
        with QualificationFixture() as f:
            (f.root/'src/U1.c').unlink();self.assertEqual(f.qmeasure()['claimed_verified'],0)
    def test_wrong_elf_class_or_machine_cannot_pass_the_build_gate(self):
        with QualificationFixture() as f:
            f.qprofile['build']={'format':'elf','bits':32,'machine':40};f.save_profile()
            self.assertEqual(f.qmeasure()['claimed_verified'],0)

if __name__=='__main__':unittest.main()
