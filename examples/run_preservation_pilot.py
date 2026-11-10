"""Exercise the REAL native 8.3 gate using a clearly synthetic differential executor."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

REPO=Path(__file__).resolve().parents[1]
WRAPPER='''import hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path('helpers').resolve()))
from differential import differential
cases=json.loads(Path('witnesses.json').read_text())
mode=json.loads(Path('candidate.json').read_text())['mode']
def invoke(**kwargs):
 value=kwargs['regs']['0']
 return {'reg0':value+1,'memory':value+3 if mode=='faithful' else 0}
references={role:{'path':path,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
for role,path in [('stock','stock.bin'),('witnesses','witnesses.json'),('executor','executor.json')]}
ok=differential('SYNTHETIC executor',cases,invoke,blob=b'\\x00',print_report=False,
preservation={'project':str(Path.cwd()),'output':str(Path(os.environ['VERIMISSION_REPORT']).relative_to(Path.cwd())),
'unit':'UNIT-A','run_id':os.environ['VERIMISSION_RUN_ID'],'context_sha256':os.environ['VERIMISSION_CONTEXT_SHA256'],
'references':references,'reset':lambda:None,'reset_policy':'synthetic-independent-cases'})
sys.exit(0 if ok else 1)
'''


def run(harness_script):
    spec=importlib.util.spec_from_file_location('native83_binary_pilot',harness_script)
    hmod=importlib.util.module_from_spec(spec); spec.loader.exec_module(hmod)
    with tempfile.TemporaryDirectory(prefix='disasm83-preservation-') as tmp:
        p=Path(tmp); (p/'helpers').mkdir()
        for name in ('differential.py','preservation_receipt.py'):
            shutil.copyfile(REPO/'skills/renode-bench/scripts'/name,p/'helpers'/name)
        (p/'wrapper.py').write_text(WRAPPER)
        (p/'stock.bin').write_bytes(b'SYNTHETIC NON-EXECUTABLE REFERENCE')
        cases=[{'name':'low','regs':{'0':1},'expect':{'reg0':2,'memory':4}},
               {'name':'high','regs':{'0':5},'expect':{'reg0':6,'memory':8}}]
        (p/'witnesses.json').write_text(json.dumps(cases))
        (p/'executor.json').write_text(json.dumps({'engine':'fake invoke','hardware_validated':False}))
        (p/'candidate.json').write_text(json.dumps({'mode':'faithful'}))
        baseline={'format':'verimission-baseline-v1','reference':{'kind':'specification','id':'synthetic-stock-witnesses'},
                  'protected_files':{name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in
                                     ('wrapper.py','witnesses.json','helpers/differential.py','helpers/preservation_receipt.py')},
                  'context_files':{name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ('stock.bin','executor.json')},
                  'obligations':[{'id':'W-'+case['name'],'criterion':'BENCH','case':'UNIT-A::'+case['name'],'critical':True,
                                  'sources':['candidate.json'],'comparator':{'kind':'status'}} for case in cases], 'debt':[]}
        (p/'baseline.json').write_text(json.dumps(baseline))
        policy={'schema':1,'baseline':{'path':'baseline.json','sha256':hashlib.sha256((p/'baseline.json').read_bytes()).hexdigest()},
                'input_patterns':['wrapper.py','helpers/*.py','witnesses.json','candidate.json'],
                'criteria':{'BENCH':{'output_pattern':'reports/{run}.json'}},'mode':'full','graph':{},'graph_complete':False,'environment':[]}
        mission={'objective':'Check the preservation gate using synthetic differential witnesses','mode':'light',
                 'in_scope':['temporary synthetic fixtures'],'out_of_scope':['real firmware','emulator execution','installation'],
                 'criteria':[{'id':'BENCH','description':'Retain witnessed return AND memory effects',
                              'argv':[sys.executable,'-B','wrapper.py'],'artifacts':['candidate.json','wrapper.py','witnesses.json']}],
                 'budget':{'max_no_progress':10,'max_same_failures':10},'regression_policy':policy}
        h=hmod.Harness(p); h.init(mission)
        def start():
            review=h.review('binary-fixture')['review']
            return h.start({'topic':'binary-fixture','task':'witness','premise':'Same explicit synthetic observables',
                'residual':'Check return and memory','review_id':review['id'],'reviewed_claims':review['claims'],'criteria':['BENCH'],
                'approach':{'method':'finite synthetic differential','inputs':'bound witnesses','environment':'fake invoke, no hardware'},
                'reverify_reason':'Revalidate current synthetic candidate'})['cycle']
        first=start(); assert h.check(first,'BENCH')['passed']; h.close(first,'verified','change candidate')
        (p/'candidate.json').write_text(json.dumps({'mode':'bad-memory'}))
        broken=start(); assert not h.check(broken,'BENCH')['passed']
        try: h.close(broken,'verified','must not accept correct return with wrong memory')
        except hmod.Refusal as error: assert error.code=='REGRESSION_BLOCKED'
        else: raise AssertionError('Side-effect regression accepted')
        h.interrupt(broken,'repair synthetic memory effect')
        (p/'candidate.json').write_text(json.dumps({'mode':'faithful'}))
        restored=start(); assert h.check(restored,'BENCH')['passed']; h.close(restored,'verified','revalidated')
        assert h.accept_mission()['accepted']
        return {'native_harness_version':hmod.VERSION,'side_effect_regression_blocked':True,'restored':True,
                'real_emulator_executed':False,'real_firmware_used':False,'promotion_authorized':False,'semantic_truth_verified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--harness',required=True,type=Path)
    args=parser.parse_args(); print(json.dumps(run(args.harness.resolve(strict=True))))
