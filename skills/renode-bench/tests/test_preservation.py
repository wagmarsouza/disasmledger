import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/differential.py'
spec=importlib.util.spec_from_file_location('preservation_diff',SCRIPT)
d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.cases=[{'name':'one','regs':{0:1},'expect':{'reg0':2,'mem0':4}},
                    {'name':'two','regs':{0:2},'expect':{'reg0':3,'mem0':5}}]
        (self.root/'stock.bin').write_bytes(b'synthetic')
        (self.root/'witnesses.json').write_text(json.dumps(self.cases))
        self.resets=[]
        self.config={'project':str(self.root),'output':'result.json','unit':'UNIT-A','run_id':'run-a',
                     'context_sha256':'a'*64,'references':{role:{'path':p,'sha256':hashlib.sha256((self.root/p).read_bytes()).hexdigest()}
                     for role,p in [('stock','stock.bin'),('witnesses','witnesses.json')]},
                     'reset':lambda:self.resets.append('reset'),'reset_policy':'cold-independent'}

    def tearDown(self): self.temp.cleanup()

    def run_diff(self, invoke=None, config=None):
        invoke=invoke or (lambda **k:{'reg0':k['regs'][0]+1,'mem0':k['regs'][0]+3})
        return d.differential('synthetic',self.cases,invoke,blob=b'\x00',print_report=False,
                              preservation=self.config if config is None else config)

    def test_neutral_report_and_reset_each_witness(self):
        self.assertIs(self.run_diff(),True)
        report=json.loads((self.root/'result.json').read_text())
        self.assertEqual(report['format'],'verimission-results-v1')
        self.assertEqual(report['cases'][0]['id'],'UNIT-A::one')
        self.assertEqual(self.resets,['reset','reset'])
        self.assertEqual(report['cases'][0]['status'],'pass')

    def test_correct_return_with_wrong_memory_is_failure(self):
        self.assertIs(self.run_diff(lambda **k:{'reg0':k['regs'][0]+1,'mem0':0}),False)
        self.assertEqual(json.loads((self.root/'result.json').read_text())['cases'][0]['status'],'fail')

    def test_reset_required_and_no_automatic_grade_promotion(self):
        bad={**self.config,'reset':None}
        with self.assertRaises(d.DifferentialError): self.run_diff(config=bad)
        self.assertFalse((self.root/'result.json').exists())

    def test_duplicate_witness_ids_refused(self):
        self.cases[1]['name']='one'
        with self.assertRaises(d.DifferentialError): self.run_diff()

    def test_reference_drift_and_overwrite_refused(self):
        (self.root/'stock.bin').write_bytes(b'changed')
        with self.assertRaises(d.DifferentialError): self.run_diff()
        (self.root/'stock.bin').write_bytes(b'synthetic')
        (self.root/'result.json').write_text('preserve')
        with self.assertRaises(d.DifferentialError): self.run_diff()
        self.assertEqual((self.root/'result.json').read_text(),'preserve')

    def test_source_change_during_invoke_refused(self):
        def invoke(**k):
            (self.root/'witnesses.json').write_text('changed')
            return {'reg0':k['regs'][0]+1,'mem0':k['regs'][0]+3}
        with self.assertRaises(d.DifferentialError): self.run_diff(invoke)

    def test_path_escape_refused(self):
        with self.assertRaises(d.DifferentialError): self.run_diff(config={**self.config,'output':'../elsewhere.json'})


if __name__=='__main__': unittest.main()
