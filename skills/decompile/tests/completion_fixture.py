"""Synthetic protocol tools only. Actual GCC execution is a separate Linux pilot."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
def load(name):
    s=importlib.util.spec_from_file_location('completion_test_'+name,SCRIPTS/(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def profile():
    p=SCRIPTS.parents[1]/'binary-analysis-profile/scripts/binary_profile.py'
    if not p.is_file():p=SCRIPTS/'vendor/binary_profile.py'
    s=importlib.util.spec_from_file_location('existing_profile_test',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

TOOL='''import hashlib,json,sys
from pathlib import Path
mode=sys.argv[1]
if mode in ('compile','preprocess'):
 Path(sys.argv[3]).write_bytes(Path(sys.argv[2]).read_bytes())
else:
 stock,image,corpus,output,unit,entry,run=sys.argv[2:]
 def ref(path):return {'path':Path(path).resolve().relative_to(Path.cwd()).as_posix(),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
 w=json.loads(Path(corpus).read_text());source=Path(image).read_text(errors='replace')
 fault=w.get('fault');loaded=stock if fault=='old_image' else image
 rows=[]
 for case in w['cases']:
  x=case['input'];got=x+2 if 'x+2' in source else x+1
  events=[{'role':'candidate','image':ref(loaded),'pc':4096}]
  if fault=='original_call':events.append({'role':'original','image':ref(stock),'pc':8192})
  if fault=='unknown_call':events.append({'role':'unknown','image':ref(image),'pc':10240})
  if fault=='platform':events.append({'role':'platform:rom','image':ref('rom.bin'),'pc':12288})
  rows.append({'id':case['id'],'stock':x+1,'candidate':got,'stock_status':'fault' if fault=='all_faults' else 'returned',
               'candidate_status':'fault' if fault=='all_faults' else 'returned','reset':fault!='no_reset','execution':events})
 value={'format':'disasm-execution-v1','unit':unit,'entry':entry,'run_id':run if fault!='old_run' else 'old',
        'image':ref(loaded),'stock':ref(stock),'witnesses':ref(corpus),'complete':True,'cases':rows}
 if fault=='omitted':value['cases'].pop()
 with Path(output).open('x') as f:json.dump(value,f)
'''

class Fixture:
    def __enter__(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='decompile-completion-test-');self.root=Path(self.tmp.name)
        for folder in ('src','reviews','witnesses','negative','units'):(self.root/folder).mkdir()
        (self.root/'stock.bin').write_bytes(b'original')
        (self.root/'tool.py').write_text(TOOL)
        (self.root/'src/U1.c').write_text('int f(int x){return x+1;}')
        (self.root/'negative/U1.c').write_text('int f(int x){return x+2;}')
        self.target={'format':'binary-target-v1','binary':'stock.bin','sha256':sha(self.root/'stock.bin'),
            'architecture':'synthetic-protocol','endianness':'little','address_unit_bytes':1,
            'segments':[{'id':'text','address_space':'ram','file_offset':0,'size':8,'virtual_base':4096}],
            'analysis_configuration':{'tool':'synthetic fixture','version':'1','settings':{}},'provenance':'not real firmware'}
        self.unit={'format':'binary-unit-v1','id':'U1','target_sha256':self.target['sha256'],
            'segment':'text','file_offset':0,'size':8,'virtual_address':4096,'isa_mode':'synthetic',
            'classification':'candidate_function','boundary_hypothesis':'synthetic fixture only'}
        self.write('target.json',self.target);self.write('units/U1.json',self.unit)
        identity=profile().manifest_digest(profile().validate_unit(self.root,self.target,self.unit)['identity'])
        self.universe={'format':'verimission-universe-v1','units':[{'id':'U1','identity':identity,
            'deliverable':'src/U1.c','depends_on':[]}],'excluded':[]}
        self.write('universe.json',self.universe)
        self.review={'format':'disasm-source-qualification-v1','unit':'U1','source_sha256':sha(self.root/'src/U1.c'),
            'representation':'structured-source','reviewer':'independent-review-fixture','dependencies_complete':True,
            'dependencies':[],'acknowledged_signals':[],'indirect_resolutions':{},
            'build_inputs_sha256':hashlib.sha256(b'{}').hexdigest()}
        self.write('reviews/U1.json',self.review)
        self.corpus={'format':'disasm-witnesses-v1','cases':[{'id':'one','input':1,'purpose':'first input'},
                                                         {'id':'two','input':2,'purpose':'different input'}]}
        self.write('witnesses/U1.json',self.corpus)
        tool={'executable_sha256':sha(Path(sys.executable)),'files':{'tool.py':sha(self.root/'tool.py')}}
        self.config={'format':'disasm-completion-config-v1','target':self.ref('target.json'),
            'universe':self.ref('universe.json'),'work_pattern':'completion/{run}',
            'budget_seconds':60,'tool_timeout_seconds':10,
            'profile':{'reviewers':['independent-review-fixture'],'execution_kind':'pc-trace',
                       'platform_images':{},'allowed_external_calls':[]},
            'tools':{'compiler':{**tool,'argv':[sys.executable,'tool.py','compile','{source}','{output}'],
                     'preprocess_argv':[sys.executable,'tool.py','preprocess','{source}','{output}']},
                     'executor':{**tool,'argv':[sys.executable,'tool.py','run','{stock}','{image}','{witnesses}',
                                              '{report}','{unit}','{entry}','{run}']}},
            'units':{'U1':{'unit_manifest':'units/U1.json','symbol':'f','qualification':'reviews/U1.json',
                           'witnesses':'witnesses/U1.json','negative_source':'negative/U1.c','build_inputs':[]}}}
        self.save();return self
    def __exit__(self,*args):self.tmp.cleanup()
    def write(self,path,value):(self.root/path).write_text(json.dumps(value),encoding='utf-8')
    def ref(self,path):return {'path':path,'sha256':sha(self.root/path)}
    def save(self):self.write('config.json',self.config)
    def measure(self,previous=None,run='test-run'):
        return load('completion').measure(self.root,'config.json',run,'a'*64,previous=previous)
