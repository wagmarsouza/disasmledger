"""Finite evidence-qualified reconstruction checks. Not a decompiler, emulator or second ledger."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

def sibling(name,path=None):
    s=importlib.util.spec_from_file_location('completion_'+name,path or Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

closure=sibling('closure');structure=sibling('source_structure')
profile_path=Path(__file__).parents[2]/'binary-analysis-profile/scripts/binary_profile.py'
if not profile_path.is_file():profile_path=Path(__file__).parent/'vendor/binary_profile.py'

GATES=['representation','compilation','behavior','independence','controls']
def need(condition,message):
    if not condition:raise ValueError(message)
def encoded(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
def digest(v):return hashlib.sha256(encoded(v)).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class Verifier:
    def __init__(self,root,config_file,run_id,context):
        self.root=Path(root).resolve(strict=True);self.started=time.monotonic()
        need(re.fullmatch(r'[A-Za-z0-9_-]{1,128}',run_id) is not None,'Safe fresh run ID required')
        need(re.fullmatch('[a-f0-9]{64}',context) is not None,'Current context hash required')
        self.run_id=run_id;self.context=context;self.config_path=self.path(config_file)
        self.config=closure.load_json(self.config_path);v=self.config
        need(isinstance(v,dict) and set(v)=={'format','target','universe','work_pattern','budget_seconds',
             'tool_timeout_seconds','profile','tools','units'} and v['format']=='disasm-completion-config-v1','Use the exact completion config')
        need(type(v['budget_seconds']) is int and 1<=v['budget_seconds']<=3600 and
             type(v['tool_timeout_seconds']) is int and 1<=v['tool_timeout_seconds']<=1800,'Declare finite verifier/tool budgets')
        self.deadline=self.started+min(v['budget_seconds'],float(os.environ.get('VERIMISSION_TIMEOUT',v['budget_seconds'])))
        need(isinstance(v['work_pattern'],str) and v['work_pattern'].count('{run}')==1,'A fresh work pattern is required')
        self.work=self.path(v['work_pattern'].replace('{run}',run_id),False)
        need(not self.work.exists(),'Existing run artifacts are preserved; choose a fresh run ID')
        self.profile=sibling('profile_identity',profile_path)
        self.target=closure.load_json(self.bound(v['target']));self.universe=closure.load_json(self.bound(v['universe']))
        self.profile.validate_target(self.root,self.target)
        u=self.universe
        need(isinstance(u,dict) and set(u)=={'format','units','excluded'} and u['format']=='verimission-universe-v1','Use the neutral fixed universe')
        self.units={r['id']:r for r in u['units']}
        need(len(self.units)==len(u['units']) and len({r['identity'] for r in u['units']})==len(u['units']),'Duplicate IDs/physical identities refused')
        excluded=[r['id'] for r in u['excluded']]
        need(len(set(excluded))==len(excluded) and set(excluded)<=set(self.units),'Invalid exclusions')
        self.live=set(self.units)-set(excluded)
        need(isinstance(v['units'],dict) and set(v['units'])==self.live,'Domain inputs must match the full live inventory')
        p=v['profile'];need(isinstance(p,dict) and set(p)=={'reviewers','execution_kind','platform_images','allowed_external_calls'},'Use the explicit source/execution profile')
        need(p['execution_kind'] in ('pc-trace','process-image') and isinstance(p['reviewers'],list) and p['reviewers'],
             'Declare execution kind and approved independent reviewers')
        need(isinstance(p['platform_images'],dict) and isinstance(p['allowed_external_calls'],list),'Declare platform/callee boundaries')
        for ref in p['platform_images'].values():self.bound(ref)
        need(set(v['tools'])=={'compiler','executor'},'Compiler and executor are separate approved tools')
        self.tools={name:self.tool(name) for name in v['tools']}
        self.symbols={row['symbol']:uid for uid,row in v['units'].items()}
        need(len(self.symbols)==len(v['units']),'One declared symbol per unit; aliases cannot increase counts')
        anchors=set()
        for uid,setting in v['units'].items():
            path=self.path(setting['unit_manifest'],False)
            if not path.is_file():continue
            declared=closure.load_json(path);checked=self.profile.validate_unit(self.root,self.target,declared)
            identity=checked['identity']
            anchor=tuple(identity[k] for k in ('binary_sha256','segment','address_space','file_offset','isa_mode'))
            need(anchor not in anchors,'Two aliases/boundary guesses at the same physical entry are not two functions')
            anchors.add(anchor)
        self.context_value={'config_sha256':sha(self.config_path),'compiler':self.tools['compiler']['identity'],
            'executor':self.tools['executor']['identity'],'validator_sha256':sha(__file__),
            'structure_sha256':sha(structure.__file__),'profile_helper_sha256':sha(profile_path),'closure_sha256':sha(closure.__file__)}
        raw=encoded(self.context_value);context_path=self.path('completion-context/'+hashlib.sha256(raw).hexdigest()+'.json',False)
        context_path.parent.mkdir(parents=True,exist_ok=True)
        if context_path.exists():need(context_path.read_bytes()==raw,'Context artifact was modified')
        else:
            with context_path.open('xb') as f:f.write(raw)
        self.context_ref=self.ref(context_path)

    def remaining(self):
        value=self.deadline-time.monotonic()
        if value<=0:raise TimeoutError('Completion budget exhausted; no complete report is authorized')
        return value
    def context_current(self):
        need(sha(self.config_path)==self.context_value['config_sha256'],'Completion policy changed during execution')
        need(sha(__file__)==self.context_value['validator_sha256'] and sha(structure.__file__)==self.context_value['structure_sha256'] and
             sha(profile_path)==self.context_value['profile_helper_sha256'] and sha(closure.__file__)==self.context_value['closure_sha256'],
             'Verifier implementation changed during execution')
        for name in self.tools:need(self.tool(name)['identity']==self.context_value[name],'Compiler/executor changed during execution')
    def path(self,value,exists=True):
        p=closure.evidence_path(self.root,value)
        if exists:need(p.is_file(),'Required physical evidence file is missing: '+str(value))
        return p
    def ref(self,path):
        p=Path(path).resolve();need(p.is_relative_to(self.root),'Evidence must stay inside the project')
        return {'path':p.relative_to(self.root).as_posix(),'sha256':sha(p)}
    def bound(self,ref):
        need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'A physical path/hash reference is required')
        p=self.path(ref['path']);need(sha(p)==ref['sha256'],'Referenced evidence changed: '+ref['path']);return p
    def tool(self,name):
        v=self.config['tools'][name]
        fields={'argv','executable_sha256','files'}|({'preprocess_argv'} if name=='compiler' else set())
        need(isinstance(v,dict) and set(v)==fields,'Use an explicit approved tool recipe')
        argv=v['argv'];need(isinstance(argv,list) and argv and all(isinstance(x,str) and x for x in argv),'Explicit argv required')
        exe=Path(argv[0]) if Path(argv[0]).is_absolute() else Path(shutil.which(argv[0]) or self.root/argv[0])
        exe=exe.resolve();need(exe.is_file() and sha(exe)==v['executable_sha256'],'Compiler/executor identity changed')
        refs={}
        for relative,expected in v['files'].items():
            ref={'path':relative,'sha256':expected};self.bound(ref);refs[relative]=expected
        if name=='compiler':need(isinstance(v['preprocess_argv'],list) and v['preprocess_argv'] and v['preprocess_argv'][0]==argv[0],
                                  'Preprocessing must use the same approved compiler executable')
        return {'value':v,'exe':str(exe),'identity':{'executable_sha256':v['executable_sha256'],'files':refs,'recipe_sha256':digest(v)}}
    def execute(self,kind,argv,values,directory,label):
        self.remaining();tool=self.tool(kind)
        try:actual=[tool['exe'],*[arg.format_map(values) for arg in argv[1:]]]
        except (ValueError,KeyError):raise ValueError('Unknown tool placeholder') from None
        result=subprocess.run(actual,cwd=self.root,shell=False,capture_output=True,
            timeout=min(self.remaining(),self.config['tool_timeout_seconds']),
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        refs={}
        for name,raw in [('stdout',result.stdout),('stderr',result.stderr)]:
            path=directory/(label+'.'+name)
            with path.open('xb') as f:f.write(raw)
            refs[name]=self.ref(path)
        self.remaining();need(result.returncode==0,'Tool failed: '+kind)
        return {'argv':actual,'exit_code':result.returncode,'logs':refs}
    def input_state(self,uid):
        original=self.units[uid];u=self.config['units'][uid]
        need(set(u)=={'unit_manifest','symbol','qualification','witnesses','negative_source','build_inputs'},'Use exact unit input paths')
        need(isinstance(u['build_inputs'],list) and len(set(u['build_inputs']))==len(u['build_inputs']),
             'Declare complete header/linker/support inputs without duplicates')
        refs={name:self.ref(self.path(path)) for name,path in {
            'deliverable':original['deliverable'],'unit_profile':u['unit_manifest'],'source_review':u['qualification'],
            'witnesses':u['witnesses'],'negative_source':u['negative_source']}.items()}
        unit=closure.load_json(self.bound(refs['unit_profile']));checked=self.profile.validate_unit(self.root,self.target,unit)
        need(unit['id']==uid and self.profile.manifest_digest(checked['identity'])==original['identity'],'Unit identity differs from binary-profile/universe')
        review=closure.load_json(self.bound(refs['source_review']))
        need(isinstance(review,dict) and set(review)=={'format','unit','source_sha256','representation','reviewer',
            'dependencies_complete','dependencies','acknowledged_signals','indirect_resolutions','build_inputs_sha256'} and
            review['format']=='disasm-source-qualification-v1','Use a source-bound independent qualification')
        need(review['unit']==uid and review['source_sha256']==refs['deliverable']['sha256'],'Source review is stale or for another unit')
        need(review['reviewer'] in self.config['profile']['reviewers'] and review['representation']=='structured-source',
             'Descriptor, transliteration, hybrid or unreviewed representation cannot count as structured reconstruction')
        need(review['dependencies_complete'] is True and isinstance(review['dependencies'],list) and
             set(review['dependencies'])==set(original['depends_on']),'Unknown/inconsistent dependencies cannot qualify')
        build_inputs={path:sha(self.path(path)) for path in u['build_inputs']}
        need(review['build_inputs_sha256']==digest(build_inputs),'Source review does not cover current headers/linker/support inputs')
        for path,checksum in build_inputs.items():refs['build-input-'+digest(path)]={'path':path,'sha256':checksum}
        corpus=closure.load_json(self.bound(refs['witnesses']))
        need(isinstance(corpus,dict) and corpus.get('format')=='disasm-witnesses-v1' and isinstance(corpus.get('cases'),list),
             'Physical discriminating witness corpus required')
        cases=corpus['cases'];need(len(cases)>=2 and len({r['id'] for r in cases})==len(cases) and
            len({digest(r['input']) for r in cases})>=2,'At least two distinct stable witness inputs required')
        refs.update(target_profile=self.config['target'],universe=self.config['universe'],verifier_context=self.context_ref)
        return {'refs':refs,'review':review,'corpus':corpus,'symbol':u['symbol'],'unit':checked,
                'signature':digest({'refs':refs,'context':self.context_value,'identity':original['identity']})}

    def assess_structure(self,uid,state,preprocessed):
        analysis=structure.analyze(preprocessed.read_text(encoding='utf-8'),state['symbol'])
        review=state['review']
        need(set(analysis['signals'])<=set(review['acknowledged_signals']),'AST review signals were not addressed')
        allowed=set(self.units[uid]['depends_on']);external=set(self.config['profile']['allowed_external_calls'])
        for symbol in analysis['direct_calls']:
            need(symbol in external or self.symbols.get(symbol) in allowed,'Callee is outside reconstructed closure/approved platform calls')
        resolutions=review['indirect_resolutions']
        need(isinstance(resolutions,dict) and set(resolutions)==set(analysis['indirect_calls']),
             'Every indirect call requires a bound resolution; unknown calls cannot qualify')
        extra={}
        for site,item in resolutions.items():
            need(set(item)=={'targets','evidence'} and item['targets'] and set(item['targets'])<=allowed|external,
                 'Indirect targets must stay within declared closed dependencies/platform')
            self.bound(item['evidence']);extra['resolution-'+digest(site)]=item['evidence']
        return analysis,extra

    def execution_result(self,uid,state,image_ref,path,run):
        report=closure.load_json(path)
        fields={'format','unit','entry','run_id','image','stock','witnesses','complete','cases'}
        need(isinstance(report,dict) and set(report)==fields and report['format']=='disasm-execution-v1','Use complete execution provenance')
        stock=self.ref(self.path(self.target['binary']))
        need(report['unit']==uid and report['entry']==state['symbol'] and report['run_id']==run and report['complete'] is True,
             'Wrong unit/entry/run or incomplete execution')
        need(report['image']==image_ref and report['stock']==stock and report['witnesses']==state['refs']['witnesses'],
             'Compiled image, original or witness binding differs from executed image')
        self.bound(image_ref);self.bound(stock);self.bound(report['witnesses'])
        need(isinstance(report['cases'],list),'Actual execution cases required')
        rows={}
        for row in report['cases']:
            need(isinstance(row,dict) and set(row)=={'id','stock','candidate','stock_status','candidate_status','reset','execution'} and row['id'] not in rows,
                 'Unique execution observations are required')
            need(row['stock_status'] in ('returned','stopped','fault') and row['candidate_status'] in ('returned','stopped','fault'),
                 'Timeout/unknown termination is not completed behavioral evidence')
            need(row['reset'] is True and isinstance(row['execution'],list) and row['execution'],
                 'Cold/reset execution provenance required per witness')
            seen_candidate=False
            for event in row['execution']:
                need(isinstance(event,dict) and set(event)=={'role','image','pc'},'Code-origin evidence must be explicit')
                self.bound(event['image'])
                if self.config['profile']['execution_kind']=='pc-trace':
                    need(type(event['pc']) is int and event['pc']>=0,'Actual PC trace required by this profile')
                else:need(event['pc'] is None or type(event['pc']) is int,'Invalid process-image execution record')
                if event['role']=='candidate':
                    need(event['image']==image_ref,'Old/different blob executed instead of reconstruction');seen_candidate=True
                elif isinstance(event['role'],str) and event['role'].startswith('platform:'):
                    name=event['role'].split(':',1)[1]
                    need(self.config['profile']['platform_images'].get(name)==event['image'],'Unapproved platform code execution')
                else:raise ValueError('Original-code reentry or unknown direct/indirect execution cannot qualify')
            need(seen_candidate,'No reconstructed code execution observed')
            rows[row['id']]=row
        expected={r['id'] for r in state['corpus']['cases']}
        need(set(rows)==expected,'Witness omission or unexpected case')
        need(any(r['stock_status'] in ('returned','stopped') for r in rows.values()),'All-fault witnesses are not a healthy reachable function control')
        return {'matched':all(r['stock_status']==r['candidate_status'] and encoded(r['stock'])==encoded(r['candidate']) for r in rows.values()),'witnesses':len(rows)}

    def assess_receipt(self,uid,state,receipt):
        need(receipt.get('format')=='disasm-completion-receipt-v1' and receipt.get('unit')==uid and
             receipt.get('identity')==self.units[uid]['identity'] and receipt.get('signature')==state['signature'],
             'Cached receipt identity/source/tool context changed')
        artifacts=receipt['artifacts']
        for ref in artifacts.values():self.bound(ref)
        analysis,resolutions=self.assess_structure(uid,state,self.bound(artifacts['preprocessed']))
        for role,ref in resolutions.items():need(artifacts.get(role)==ref,'Indirect resolution was not included in proof')
        for kind,source_role,image_role in [('compile','deliverable','compiled_image'),('negative_compile','negative_source','negative_image')]:
            command=receipt[kind]
            source=self.bound(state['refs'][source_role]);image=self.bound(artifacts[image_role])
            values={'source':str(source),'output':str(image)}
            recipe=self.tools['compiler']['value']['argv']
            expected=[self.tools['compiler']['exe'],*[arg.format_map(values) for arg in recipe[1:]]]
            need(command['exit_code']==0 and command['argv']==expected,'Image is not bound to its actual compilation recipe')
            for ref in command['logs'].values():self.bound(ref)
        prefix=receipt['run_id']
        positive=self.execution_result(uid,state,self.ref(self.path(self.target['binary'])),
            self.bound(artifacts['positive_execution']),prefix+'-healthy')
        candidate=self.execution_result(uid,state,artifacts['compiled_image'],
            self.bound(artifacts['candidate_execution']),prefix+'-candidate')
        negative=self.execution_result(uid,state,artifacts['negative_image'],
            self.bound(artifacts['negative_execution']),prefix+'-negative')
        controls=positive['matched'] and not negative['matched']
        gates={'representation':'pass','compilation':'pass','behavior':'pass' if candidate['matched'] else 'fail',
               'independence':'pass','controls':'pass' if controls else 'fail'}
        return gates,analysis

    def execute_unit(self,uid,state):
        directory=self.work/digest(uid)[:20];directory.mkdir(parents=True,exist_ok=False)
        source=self.bound(state['refs']['deliverable']);negative=self.bound(state['refs']['negative_source'])
        preprocessed=directory/'source.i';image=directory/'candidate.bin';bad_image=directory/'negative.bin'
        compile_recipe=self.tools['compiler']['value']
        preprocess=self.execute('compiler',compile_recipe['preprocess_argv'],{'source':str(source),'output':str(preprocessed)},directory,'preprocess')
        need(preprocessed.is_file(),'Compiler did not produce preprocessed source')
        _,extra=self.assess_structure(uid,state,preprocessed)
        good=self.execute('compiler',compile_recipe['argv'],{'source':str(source),'output':str(image)},directory,'compile')
        bad=self.execute('compiler',compile_recipe['argv'],{'source':str(negative),'output':str(bad_image)},directory,'negative-compile')
        need(image.is_file() and bad_image.is_file(),'Compiler did not produce both actual images')
        artifacts={**state['refs'],**extra,'preprocessed':self.ref(preprocessed),'compiled_image':self.ref(image),
                   'negative_image':self.ref(bad_image)}
        for label,candidate in [('healthy',self.path(self.target['binary'])),('candidate',image),('negative',bad_image)]:
            output=directory/(label+'.execution.json');run=self.run_id+'-'+label
            command=self.execute('executor',self.tools['executor']['value']['argv'],
                {'stock':str(self.path(self.target['binary'])),'image':str(candidate),'witnesses':str(self.bound(state['refs']['witnesses'])),
                 'report':str(output),'unit':uid,'entry':state['symbol'],'run':run},directory,label)
            artifacts[('positive' if label=='healthy' else label)+'_execution']=self.ref(output)
            for role,ref in command['logs'].items():artifacts[label+'_'+role]=ref
        receipt={'format':'disasm-completion-receipt-v1','unit':uid,'identity':self.units[uid]['identity'],
            'run_id':self.run_id,'signature':state['signature'],'compile':good,'negative_compile':bad,'preprocess':preprocess,
            'artifacts':artifacts,'semantic_truth_authenticated':False}
        gates,_=self.assess_receipt(uid,state,receipt)
        need(self.input_state(uid)['signature']==state['signature'],'Unit/context changed during verification')
        path=directory/'receipt.json'
        with path.open('xb') as f:f.write(encoded(receipt))
        return {'id':uid,'identity':self.units[uid]['identity'],'gates':gates,
                'artifacts':{**artifacts,'completion_receipt':self.ref(path)}}

    def unit(self,uid,previous=None,force=False):
        self.remaining()
        try:
            state=self.input_state(uid)
            if previous and not force:
                try:
                    ref=previous['artifacts']['completion_receipt'];receipt=closure.load_json(self.bound(ref))
                    gates,_=self.assess_receipt(uid,state,receipt)
                    return {'id':uid,'identity':self.units[uid]['identity'],'gates':gates,
                            'artifacts':{**receipt['artifacts'],'completion_receipt':ref}}
                except (ValueError,OSError,KeyError,TypeError):pass
            return self.execute_unit(uid,state)
        except (TimeoutError,subprocess.TimeoutExpired):raise
        except (ValueError,OSError,KeyError,TypeError) as error:
            directory=self.work/digest(uid)[:20];directory.mkdir(parents=True,exist_ok=True)
            diagnostic=directory/'diagnostic.txt'
            with diagnostic.open('xb') as f:f.write(str(error).encode('utf-8'))
            refs={'diagnostic':self.ref(diagnostic)}
            source=self.path(self.units[uid]['deliverable'],False)
            if source.is_file():refs['deliverable']=self.ref(source)
            return {'id':uid,'identity':self.units[uid]['identity'],'gates':{k:'unknown' for k in GATES},'artifacts':refs}

    def all_units(self,previous=None,force_ids=()):
        old={}
        if previous:
            packet=closure.load_json(self.bound(previous))
            need(packet.get('format')=='verimission-measurement-v1','Previous proof must be an engine-bound measurement')
            old={r['id']:r for r in packet['units']}
            need(len(old)==len(packet['units']),'Duplicate units in previous report')
        rows=[self.unit(uid,old.get(uid),uid in force_ids) for uid in sorted(self.live)]
        eligible={r['id'] for r in rows if all(s=='pass' for s in r['gates'].values())}
        while True:
            after={u for u in eligible if set(self.units[u]['depends_on'])<=eligible}
            if after==eligible:break
            eligible=after
        self.context_current();self.remaining()
        return rows,sorted(eligible)

def measure(project,config,run_id,context,previous=None):
    verifier=Verifier(project,config,run_id,context);rows,eligible=verifier.all_units(previous)
    return {'format':'verimission-measurement-v1','run_id':run_id,'context_sha256':context,
            'universe_sha256':verifier.config['universe']['sha256'],'complete':True,'claimed_verified':len(eligible),'units':rows}

def audit(project,config,run_id,context,selection,previous):
    v=Verifier(project,config,run_id,context);plan=closure.load_json(v.path(selection))
    need(isinstance(plan,dict) and isinstance(plan.get('units'),list) and len(set(plan['units']))==len(plan['units']) and
         set(plan['units'])<=v.live,'Unknown/duplicate audit selection')
    rows,eligible=v.all_units(previous,plan['units']);by_id={r['id']:r for r in rows}
    selected=[];all_controls=True
    for uid in plan['units']:
        row=by_id[uid];ref=row['artifacts'].get('completion_receipt')
        actual=False
        if ref:
            receipt=closure.load_json(v.bound(ref));actual=receipt['run_id']==run_id
        passed=uid in eligible and actual;all_controls=all_controls and passed
        selected.append({'id':uid,'status':'pass' if passed else 'fail','executed':actual,'artifacts':row['artifacts']})
    control_path=v.work/'audit-controls.json';control_path.parent.mkdir(parents=True,exist_ok=True)
    with control_path.open('xb') as f:f.write(encoded({'selected':plan['units'],'recounted':eligible,
        'all_controls_passed':bool(selected) and all_controls,'semantic_truth_authenticated':False}))
    v.remaining()
    return {'format':'verimission-measurement-audit-v1','run_id':run_id,'context_sha256':context,'complete':True,
            'plan_id':plan['id'],'recount_ids':eligible,'units':selected,
            'controls':{'healthy_passed':bool(selected) and all_controls,'known_bad_rejected':bool(selected) and all_controls,
                        'artifacts':{'controls':v.ref(control_path)}}}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',required=True)
    parser.add_argument('--config',required=True);parser.add_argument('--previous',help='JSON path/hash descriptor; native hook normally supplies it')
    args=parser.parse_args()
    try:
        kind=os.environ['VERIMISSION_MEASUREMENT_KIND'];run=os.environ['VERIMISSION_MEASUREMENT_RUN_ID']
        context=os.environ['VERIMISSION_MEASUREMENT_CONTEXT_SHA256']
        previous=json.loads(args.previous or os.environ.get('VERIMISSION_MEASUREMENT_PREVIOUS','null'))
        if kind=='measurement':result=measure(args.project,args.config,run,context,previous)
        else:
            need(kind=='audit','Unknown measurement kind')
            root=Path(args.project).resolve();selection=Path(os.environ['VERIMISSION_AUDIT_SELECTION']).resolve()
            need(selection.is_relative_to(root),'Selection must be within the authorized project')
            result=audit(root,args.config,run,context,selection.relative_to(root).as_posix(),previous)
        root=Path(args.project).resolve();output=Path(os.environ['VERIMISSION_MEASUREMENT_REPORT'])
        if output.is_absolute():
            output=output.resolve();need(output.is_relative_to(root),'Output must remain inside the project')
            output=output.relative_to(root)
        output=closure.evidence_path(root,str(output))
        with output.open('xb') as f:f.write(encoded(result))
        print(json.dumps({'complete':True,'kind':kind,'semantic_truth_authenticated':False}));return 0
    except (ValueError,OSError,KeyError,TypeError,TimeoutError,subprocess.TimeoutExpired) as error:
        print(json.dumps({'complete':False,'error':str(error),'promotion_authorized':False}));return 2

if __name__=='__main__':raise SystemExit(main())
