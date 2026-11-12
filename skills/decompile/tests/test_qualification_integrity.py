"""Whole-run integrity and shipped profile examples; no target toolchain needed."""
import json
from pathlib import Path
import unittest
from qualification_fixture import QualificationFixture,load
from external_qualification_fixture import ExternalFixture

class QualificationIntegrityTests(unittest.TestCase):
    def test_shipped_profiles_validate_without_relaxing_synthetic_image_checks(self):
        paths=list((Path(__file__).resolve().parents[1]/'assets/profiles').glob('*.json'))
        self.assertGreaterEqual(len(paths),4)
        for path in paths:
            with self.subTest(profile=path.name):
                p=load('qualification_contract').validate_profile(json.loads(path.read_text()))
                self.assertNotEqual(p['build']['format'],'synthetic')
    def test_an_inflight_input_change_refuses_a_complete_measurement(self):
        with QualificationFixture() as f:
            q=load('qualification').Qualification(f.root,'contract.json','snapshot','a'*64)
            q.start();(f.root/'src/U1.c').write_text('int f(int x){return x+2;}')
            with self.assertRaisesRegex(ValueError,'input set changed'):q.current()
    def test_fresh_external_audit_reexecutes_selected_units(self):
        with ExternalFixture() as f:
            prior=f.qmeasure();f.write('previous.json',prior);f.write('selection.json',{'id':'audit','units':['U1']})
            result=load('qualification').audit(f.root,'contract.json','external-audit','a'*64,'selection.json',f.ref('previous.json'))
            self.assertEqual(result['recount_ids'],['U1']);self.assertTrue(result['units'][0]['executed'])
            ref=result['units'][0]['artifacts']['validation_context']
            self.assertEqual(json.loads((f.root/ref['path']).read_text())['run_id'],'external-audit')
    def test_external_corpus_cannot_be_changed_under_an_approved_recipe(self):
        with ExternalFixture(method='differential') as f:
            (f.root/'witnesses/U1.json').write_text('{"cases":[]}')
            with self.assertRaises(ValueError):f.qmeasure()
    def test_equivalence_over_no_observables_is_refused(self):
        with ExternalFixture() as f:
            f.qprofile['validation']['observables']=[];f.save_profile()
            with self.assertRaises(ValueError):f.qmeasure()
    def test_missing_or_na_required_gate_cannot_be_reported_as_done(self):
        module=load('qualification_contract')
        for status in ('fail','unknown','not-applicable'):
            for key in module.CRITERIA:
                gates={k:'pass' for k in module.CRITERIA};gates[key]=status
                self.assertFalse(module.verdict('independent-validated',gates)['reconstructed_eligible'])
        with self.assertRaises(ValueError):module.verdict('independent-validated',{'D-a':'pass'})

if __name__=='__main__':unittest.main()
