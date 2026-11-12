"""Author portable templates only; never touch a mission or install tools."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'skills/decompile/assets'
def write(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def ref(path):return {'path':path,'sha256':'0'*64}

base={'format':'decompile-target-profile-v1','id':'arm-thumb-c-reviewed-template',
    'target':{'architectures':['ARMv7E-M'],'endianness':'little','address_unit_bytes':1,'isa_modes':['thumb']},
    'language':'c','backend':'c-source-v1','reviewers':['review-required'],
    'dependencies':{'allowed_external_calls':[],'platform_images':{}},
    'build':{'format':'elf','bits':32,'machine':40},
    'validation':{'method':'differential','execution_kind':'pc-trace','min_cases':8,
        'observables':['return','memory','termination'],'required_scenarios':['normal','boundary'],
        'assumptions':['REPLACE: CPU/extensions/ABI, memory/peripheral/reset model and bounded input domain']},
    'stub_markers':['halt_baddata','Could not recover']}
write(Path('profiles/arm-thumb-c.example.json'),base)
p=copy.deepcopy(base);p['id']='native-elf-x86_64-c-reviewed-template'
p['target'].update(architectures=['x86_64'],isa_modes=['native']);p['build'].update(bits=64,machine=62)
p['validation'].update(execution_kind='process-image',observables=['returncode','stdout_hex','stderr_hex','termination'],
    assumptions=['REPLACE: native ABI/runtime/input domain; process origin is not an instruction trace'])
write(Path('profiles/native-elf-x86_64-c.example.json'),p)
p=copy.deepcopy(base);p.update(id='llvm-ir-equivalence-adapter-required',language='llvm-ir',backend='external-v1')
p['target'].update(architectures=['x86_64'],isa_modes=['native'])
p['build']={'format':'adapter-validated','bits':None,'machine':None}
p['validation']={'method':'formal-equivalence','execution_kind':'adapter','min_cases':0,
    'observables':['return','memory','termination'],'required_scenarios':[],
    'assumptions':['REPLACE: formal model linking original binary and candidate IR, semantics and input bounds']}
write(Path('profiles/llvm-ir-equivalence.example.json'),p)
p=copy.deepcopy(p);p.update(id='analysis-only-adapter-required',language='analysis-report')
p['validation'].update(method='none',observables=[],assumptions=['REPLACE: reviewed analytical scope, no behavioral claim'])
write(Path('profiles/analysis-only.example.json'),p)
write(Path('templates/qualification-contract.example.json'),{
    'format':'decompile-qualification-contract-v1','id':'REPLACE-approved-mission-epoch','category':'independent-validated',
    'profile':ref('analysis/target-profile.json'),'target':ref('analysis/target.json'),
    'universe':ref('analysis/universe.json'),'callgraph':'analysis/callgraph.json',
    'backend':{'kind':'c-source-v1','config':ref('analysis/completion-config.json')},
    'reviews':{'U1':'analysis/reviews/U1.recovery.json'},'unit_manifests':{'U1':'analysis/units/U1.json'},
    'input_patterns':['src/**/*','negative/**/*','analysis/**/*.json','evidence/**/*','tool-resources/**/*'],
    'budget_seconds':600,'work_pattern':'qualification/{run}'})
write(Path('templates/recovery-review.example.json'),{
    'format':'decompile-recovery-review-v1','unit':'U1','source_sha256':'0'*64,
    'category':'independent-validated','representation':'structured','reviewer':'review-required',
    'body_complete':False,'unresolved_operations':['REPLACE: review all recovery gaps before clearing this list'],
    'dependencies_complete':False,'dependencies':[],'marker_justifications':{}})
write(Path('templates/external-verifier.example.json'),{
    'format':'decompile-external-verifier-v1','argv':['python','tool-resources/approved_verifier.py'],
    'executable_sha256':'0'*64,'files':{'tool-resources/approved_verifier.py':'0'*64},
    'entrypoints':{'U1':'REPLACE-real-entrypoint'},'witnesses':{},
    'negative_candidates':{'U1':ref('negative/U1.ir')},'timeout_seconds':300})

if __name__=='__main__':print('Authored Decompile3 templates; no installation or publication')
