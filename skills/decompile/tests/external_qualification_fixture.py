"""Executed synthetic verifier protocol, not an LLVM parser or equivalence prover."""
from qualification_fixture import QualificationFixture,sha
import sys

ADAPTER='''import hashlib,json,os
from pathlib import Path
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,data):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(data,f)
def ref(path):return {'path':Path(path).resolve().relative_to(Path.cwd()).as_posix(),'sha256':sha(path)}
request=json.loads(Path(os.environ['DECOMPILE_QUALIFICATION_REQUEST']).read_text())
root=Path(os.environ['DECOMPILE_QUALIFICATION_REPORT']).parent
fault=Path('external-fault.txt').read_text() if Path('external-fault.txt').exists() else ''
category=request['category'];method=request['profile']['validation']['method'];rows=[]
for u in request['units']:
 uid=u['id'];criteria={k:('pass' if k in request['required_criteria'] else 'not-applicable') for k in request['criteria']}
 artifacts={};validation={'verdict':'not-applicable','healthy_control':'unknown','known_bad_control':'unknown','executed':True,'case_ids':[],'observables':[],'scenarios':[]}
 if u['ready'] and category!='analysis':
  image=root/(uid+'.ir');image.write_text('synthetic validated construction')
  build=root/(uid+'.build.json');write(build,{'format':'decompile-build-binding-v1','unit':uid,'run_id':request['run_id'],
    'source_sha256':u['artifacts']['deliverable']['sha256'],'artifact_sha256':sha(image),
    'profile_sha256':request['profile_ref']['sha256'],'exit_code':0})
  artifacts.update(constructed_artifact=ref(image),build_binding=ref(build))
 if u['ready'] and category=='independent-validated':
  proof=root/(uid+'.proof.json');negative=Path(u['artifacts']['negative_candidate']['path'])
  controls=root/(uid+'.controls.json');write(controls,{'format':'decompile-control-binding-v1','unit':uid,
    'run_id':request['run_id'],'command_context_sha256':request['command_context_sha256'],
    'original_sha256':request['original_binary']['sha256'],'candidate_sha256':u['artifacts']['deliverable']['sha256'],
    'constructed_sha256':artifacts['constructed_artifact']['sha256'],'negative_sha256':sha(negative),
    'profile_sha256':request['profile_ref']['sha256'],'healthy_passed':True,'known_bad_rejected':True})
  verdict='matched' if method=='differential' else 'equivalent'
  context=root/(uid+'.validation.json');write(context,{'format':'decompile-validation-context-v1','unit':uid,
    'run_id':request['run_id'],'command_context_sha256':request['command_context_sha256'],
    'original_sha256':request['original_binary']['sha256'],'candidate_sha256':u['artifacts']['deliverable']['sha256'],
    'constructed_sha256':artifacts['constructed_artifact']['sha256'],'profile_sha256':request['profile_ref']['sha256'],
    'method':method,'verdict':verdict,'assumptions':request['profile']['validation']['assumptions'],
    'observables':request['profile']['validation']['observables']})
  write(proof,{'synthetic_protocol_only':True,'unit':uid,'run_id':request['run_id']})
  artifacts.update(validation_context=ref(context),proof_certificate=ref(proof),control_evidence=ref(controls),negative_candidate=ref(negative))
  validation.update(verdict=verdict,healthy_control='pass',known_bad_control='rejected',observables=request['profile']['validation']['observables'])
  if method=='differential':
   corpus=Path(u['artifacts']['witnesses']['path'])
   artifacts['witnesses']=ref(corpus);validation['case_ids']=['one','two']
 if fault=='unknown':validation['verdict']='unknown'
 if fault=='weak':validation['known_bad_control']='missed'
 if fault=='cached':validation['executed']=False
 if fault=='old_control' and 'control_evidence' in artifacts:
  file=root/(uid+'.controls.json');v=json.loads(file.read_text());v['run_id']='old-control-run';file.write_text(json.dumps(v));artifacts['control_evidence']=ref(file)
 if fault=='invented_corpus' and 'validation_context' in artifacts:
  file=root/(uid+'.validation.json');v=json.loads(file.read_text());v['observables']=[];file.write_text(json.dumps(v));artifacts['validation_context']=ref(file)
 if fault=='omitted_case':validation['case_ids']=['one']
 if fault=='same_negative' and 'negative_candidate' in artifacts:artifacts['negative_candidate']=u['artifacts']['deliverable']
 if fault=='omit_build':artifacts.pop('build_binding',None)
 if fault=='wrong_source' and 'validation_context' in artifacts:
  file=root/(uid+'.validation.json');v=json.loads(file.read_text());v['candidate_sha256']='0'*64;file.write_text(json.dumps(v));artifacts['validation_context']=ref(file)
 if fault=='weaken_assumptions' and 'validation_context' in artifacts:
  file=root/(uid+'.validation.json');v=json.loads(file.read_text());v['assumptions']=['assume outputs equal'];file.write_text(json.dumps(v));artifacts['validation_context']=ref(file)
 rows.append({'id':uid,'identity':u['identity'],'category':category,'source_sha256':u['artifacts'].get('deliverable',{}).get('sha256'),
              'criteria':criteria,'artifacts':artifacts,'validation':validation})
value={'format':'decompile-adapter-observation-v1','run_id':request['run_id'],'command_context_sha256':request['command_context_sha256'],
       'category':category,'method':method,'complete':True,'units':rows}
if fault=='inflate':value['claimed_verified']=99999
if fault=='duplicate':value['units'].append(value['units'][0])
if fault=='old_run':value['run_id']='old-run'
write(os.environ['DECOMPILE_QUALIFICATION_REPORT'],value)
'''

class ExternalFixture(QualificationFixture):
    def __init__(self,category='independent-validated',method='formal-equivalence'):
        self.category=category;self.method=method
    def __enter__(self):
        super().__enter__()
        (self.root/'approved_verifier.py').write_text(ADAPTER)
        self.write('external.json',{'format':'decompile-external-verifier-v1','argv':[sys.executable,'approved_verifier.py'],
            'executable_sha256':sha(sys.executable),'files':{'approved_verifier.py':sha(self.root/'approved_verifier.py')},
            'witnesses':{'U1':self.ref('witnesses/U1.json')} if self.method=='differential' else {},
            'negative_candidates':{'U1':self.ref('negative/U1.c')} if self.category=='independent-validated' else {},
            'entrypoints':{'U1':'f'},'timeout_seconds':20})
        self.qprofile.update(language='llvm-ir',backend='external-v1')
        self.qprofile['id']='synthetic-external-protocol'
        self.qprofile['build']={'format':'adapter-validated','bits':None,'machine':None}
        self.qprofile['validation']={'method':self.method,'execution_kind':'adapter',
            'min_cases':2 if self.method=='differential' else 0,
            'observables':[] if self.method=='none' else ['return','termination'],
            'required_scenarios':[],'assumptions':['bounded finite synthetic model'] if self.method=='formal-equivalence' else []}
        self.contract['category']=self.category
        self.contract['backend']={'kind':'external-v1','config':self.ref('external.json')}
        self.contract['input_patterns']+=['external.json','approved_verifier.py','external-fault.txt']
        self.qreview.update(category=self.category,representation={'analysis':'analytical','mechanical-translation':'mechanical'}.get(self.category,'structured'))
        self.write('reviews/U1.recovery.json',self.qreview);self.save_profile()
        return self

