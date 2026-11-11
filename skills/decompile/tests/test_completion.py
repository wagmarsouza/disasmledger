"""Inflation controls at the domain boundary; fixture tools are deliberately synthetic."""
from pathlib import Path
import json
import os
import subprocess
import sys
import unittest
from completion_fixture import Fixture,load,sha

class CompletionTests(unittest.TestCase):
    def test_header_drift_invalidates_cached_build_and_its_source_review(self):
        with Fixture() as f:
            (f.root/'header.h').write_text('int dependency;')
            f.config['units']['U1']['build_inputs']=['header.h'];f.save()
            f.review['build_inputs_sha256']=load('completion').digest({'header.h':sha(f.root/'header.h')})
            f.write('reviews/U1.json',f.review)
            first=f.measure();self.assertEqual(first['claimed_verified'],1);f.write('previous.json',first)
            (f.root/'header.h').write_text('long dependency;')
            self.assertEqual(f.measure(previous=f.ref('previous.json'),run='header-changed')['claimed_verified'],0)

    def test_cli_accepts_native_engine_absolute_fresh_output(self):
        with Fixture() as f:
            output=f.root/'native-report.json'
            script=Path(__file__).resolve().parents[1]/'scripts/completion.py'
            env={**os.environ,'VERIMISSION_MEASUREMENT_KIND':'measurement','VERIMISSION_MEASUREMENT_RUN_ID':'cli-run',
                 'VERIMISSION_MEASUREMENT_CONTEXT_SHA256':'a'*64,'VERIMISSION_MEASUREMENT_REPORT':str(output)}
            p=subprocess.run([sys.executable,'-B',str(script),'--project',str(f.root),'--config','config.json'],
                             capture_output=True,text=True,env=env)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertEqual(json.loads(output.read_text())['claimed_verified'],1)
    def test_two_aliases_of_one_entry_cannot_qualify_as_two_functions(self):
        with Fixture() as f:
            u=dict(f.unit,id='alias',size=4);f.write('units/alias.json',u)
            from completion_fixture import profile
            identity=profile().manifest_digest(profile().validate_unit(f.root,f.target,u)['identity'])
            f.universe['units'].append({'id':'alias','identity':identity,'deliverable':'src/alias.c','depends_on':[]})
            f.write('universe.json',f.universe);f.config['universe']=f.ref('universe.json')
            f.config['units']['alias']={**f.config['units']['U1'],'unit_manifest':'units/alias.json','symbol':'alias'};f.save()
            with self.assertRaises(ValueError):f.measure()
    def test_all_faults_are_not_a_healthy_positive_control(self):
        with Fixture() as f:
            f.corpus['fault']='all_faults';f.write('witnesses/U1.json',f.corpus)
            self.assertEqual(f.measure()['claimed_verified'],0)
    def test_audit_forces_reexecution_and_exact_full_recount(self):
        with Fixture() as f:
            first=f.measure();f.write('previous.json',first);f.write('selection.json',{'id':'plan','units':['U1']})
            result=load('completion').audit(f.root,'config.json','audit-run','a'*64,'selection.json',f.ref('previous.json'))
            self.assertEqual(result['recount_ids'],['U1']);self.assertTrue(result['units'][0]['executed'])
            new=result['units'][0]['artifacts']['completion_receipt']
            self.assertNotEqual(first['units'][0]['artifacts']['completion_receipt'],new)

    def test_straight_line_source_with_bound_execution_qualifies(self):
        with Fixture() as f:
            r=f.measure();self.assertEqual(r['claimed_verified'],1)
            self.assertTrue(all(v=='pass' for v in r['units'][0]['gates'].values()))
    def test_grades_without_source_do_not_qualify(self):
        with Fixture() as f:
            (f.root/'src/U1.c').unlink();self.assertEqual(f.measure()['claimed_verified'],0)
    def test_descriptor_transliteration_and_hybrid_not_mislabelled_done(self):
        for kind in ('descriptor','machine-transliteration','hybrid'):
            with self.subTest(kind=kind),Fixture() as f:
                f.review['representation']=kind;f.write('reviews/U1.json',f.review)
                self.assertEqual(f.measure()['claimed_verified'],0)
    def test_dummy_condition_does_not_override_review(self):
        with Fixture() as f:
            (f.root/'src/U1.c').write_text('int f(int x){if(0){x=0;}return x+1;}')
            f.review.update(source_sha256=sha(f.root/'src/U1.c'),representation='machine-transliteration')
            f.write('reviews/U1.json',f.review);self.assertEqual(f.measure()['claimed_verified'],0)
    def test_old_loaded_image_original_reentry_and_unknown_execution_fail(self):
        for fault in ('old_image','original_call','unknown_call','old_run','omitted','no_reset'):
            with self.subTest(fault=fault),Fixture() as f:
                f.corpus['fault']=fault;f.write('witnesses/U1.json',f.corpus)
                self.assertEqual(f.measure()['claimed_verified'],0)
    def test_non_discriminating_negative_control_refuses_qualification(self):
        with Fixture() as f:
            (f.root/'negative/U1.c').write_bytes((f.root/'src/U1.c').read_bytes())
            self.assertEqual(f.measure()['claimed_verified'],0)
    def test_source_review_must_bind_current_source(self):
        with Fixture() as f:
            (f.root/'src/U1.c').write_text('int f(int x){return x+2;}')
            self.assertEqual(f.measure()['claimed_verified'],0)
    def test_data_address_constant_not_automatically_an_original_code_call(self):
        with Fixture() as f:
            (f.root/'src/U1.c').write_text('int f(int x){int data=0x08001000;return x+1;}')
            f.review['source_sha256']=sha(f.root/'src/U1.c');f.write('reviews/U1.json',f.review)
            self.assertEqual(f.measure()['claimed_verified'],1)
    def test_approved_platform_execution_is_separate_from_stock_calls(self):
        with Fixture() as f:
            (f.root/'rom.bin').write_bytes(b'platform primitive')
            f.config['profile']['platform_images']['rom']=f.ref('rom.bin');f.save()
            f.corpus['fault']='platform';f.write('witnesses/U1.json',f.corpus)
            self.assertEqual(f.measure()['claimed_verified'],1)
    def test_cached_proof_reused_only_when_every_source_and_tool_binding_is_current(self):
        with Fixture() as f:
            first=f.measure();f.write('previous.json',first)
            second=f.measure(previous=f.ref('previous.json'),run='second-run')
            self.assertEqual(second['claimed_verified'],1)
            self.assertEqual(second['units'][0]['artifacts']['completion_receipt'],first['units'][0]['artifacts']['completion_receipt'])
            (f.root/'src/U1.c').write_text('int f(int x){return x+2;}')
            self.assertEqual(f.measure(previous=f.ref('previous.json'),run='changed-run')['claimed_verified'],0)
    def test_mutated_receipt_cannot_be_reused_as_evidence(self):
        with Fixture() as f:
            first=f.measure();f.write('previous.json',first)
            ref=first['units'][0]['artifacts']['completion_receipt'];(f.root/ref['path']).write_text('{}')
            # Requalification may execute again, but the altered receipt never receives reuse credit.
            second=f.measure(previous=f.ref('previous.json'),run='requalified')
            self.assertNotEqual(ref,second['units'][0]['artifacts']['completion_receipt'])
    def test_budget_exhaustion_never_emits_complete_success(self):
        with Fixture() as f:
            f.config['budget_seconds']=0;f.save()
            with self.assertRaises(ValueError):f.measure()
    def test_duplicate_physical_entry_is_not_two_functions(self):
        with Fixture() as f:
            f.config['units']['ALIAS']=dict(f.config['units']['U1']);f.save()
            with self.assertRaises(ValueError):f.measure()

if __name__=='__main__':unittest.main()
