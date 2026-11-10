import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('preservation_adapter_test',ROOT/'scripts/verimission_adapter.py')
a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)


class PreservationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name)
        self.graph={'format':'decompile-callgraph-v1','graph':{'A':[]},'inventory_complete':True}
        self.grades={'format':'decompile-grades-v1','grades':{'A':'G4-recon'}}
        self.case={'name':'one','regs':{'0':1},'expect':{'reg0':2}}
        for name,data in [('graph.json',self.graph),('grades.json',self.grades),('witness.json',[self.case])]:
            (self.root/name).write_text(json.dumps(data))
        (self.root/'stock.bin').write_bytes(b'synthetic')
        self.refs={role:{'path':path,'sha256':hashlib.sha256((self.root/path).read_bytes()).hexdigest()}
                   for role,path in [('stock','stock.bin'),('witnesses','witness.json')]}
        self.report={'format':'verimission-results-v1','run_id':'recorded','context_sha256':'a'*64,'complete':True,
                     'cases':[{'id':'A::one','status':'pass','contract':{'references':self.refs,
                               'witness_sha256':hashlib.sha256(json.dumps(self.case,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                               'reset_policy':'cold'}}]}

    def tearDown(self): self.t.cleanup()

    def assess(self):
        (self.root/'result.json').write_text(json.dumps(self.report))
        return a.preservation_report(self.root,'graph.json','grades.json','result.json')

    def test_recon_grade_is_historical_and_sources_are_read_only(self):
        before=(self.root/'grades.json').read_bytes()
        out=self.assess()
        self.assertEqual(out['units'][0]['evidence_status'],'witness_match_observed')
        self.assertFalse(out['promotion_authorized']); self.assertFalse(out['semantic_truth_verified'])
        self.assertEqual(before,(self.root/'grades.json').read_bytes())

    def test_stock_cannot_become_reconstruction_from_a_label(self):
        (self.root/'grades.json').write_text(json.dumps({'format':'decompile-grades-v1','grades':{'A':'G4-stock'}}))
        self.assertEqual(self.assess()['units'][0]['evidence_status'],'stock_only_no_reconstruction_claim')

    def test_failed_recon_requires_revalidation_without_erasing_grade(self):
        self.report['cases'][0]['status']='fail'
        row=self.assess()['units'][0]
        self.assertEqual(row['evidence_status'],'needs_revalidation')
        self.assertEqual(row['historical_grade'],'G4-recon')

    def test_changed_stock_or_witness_sources_refused(self):
        (self.root/'stock.bin').write_bytes(b'changed')
        with self.assertRaises(a.AdapterError): self.assess()

    def test_unknown_unit_and_duplicate_cases_refused(self):
        self.report['cases'][0]['id']='UNKNOWN::one'
        with self.assertRaises(a.AdapterError): self.assess()
        self.report['cases'][0]['id']='A::one'; self.report['cases']*=2
        with self.assertRaises(a.AdapterError): self.assess()


if __name__=='__main__': unittest.main()
