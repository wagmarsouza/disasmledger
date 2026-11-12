"""Generic decompilation qualification. Observations are not a second mission ledger."""
import argparse
import importlib.util
import json
import os
from pathlib import Path, PureWindowsPath
import re
import subprocess
import time

def sibling(name):
    spec=importlib.util.spec_from_file_location('qualification_'+name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

c=sibling('qualification_contract');legacy=sibling('completion');closure=legacy.closure

class Qualification:
    ProtocolError=c.ProtocolError
    def __init__(self,project,contract_file,run_id,context):
        self.root=Path(project).resolve(strict=True);self.started=time.monotonic()
        c.need(isinstance(run_id,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',run_id),'Safe fresh run ID required')
        c.need(isinstance(context,str) and re.fullmatch(r'[a-f0-9]{64}',context),'Current command context required')
        self.run_id=run_id;self.command_context=context
        self.contract_ref=self.ref(self.path(contract_file));self.contract=closure.load_json(self.path(contract_file))
        v=self.contract
        c.need(isinstance(v,dict) and set(v)=={'format','id','category','profile','target','universe','callgraph','backend',
              'reviews','unit_manifests','input_patterns','budget_seconds','work_pattern'} and
              v['format']=='decompile-qualification-contract-v1' and c.text(v['id']) and v['category'] in c.CATEGORIES,
              'Use the exact predeclared qualification contract')
        c.need(type(v['budget_seconds']) is int and 1<=v['budget_seconds']<=3600,'Declare a finite qualification budget')
        self.deadline=self.started+min(v['budget_seconds'],float(os.environ.get('VERIMISSION_TIMEOUT',v['budget_seconds'])))
        c.need(isinstance(v['work_pattern'],str) and v['work_pattern'].count('{run}')==1,'A fresh work pattern is required')
        self.work=self.path(v['work_pattern'].replace('{run}',run_id),False)
        c.need(not self.work.exists(),'Preserve existing run evidence; use a fresh run ID')
        self.profile=c.validate_profile(closure.load_json(self.bound(v['profile'])))
        self.target=closure.load_json(self.bound(v['target']));self.universe=closure.load_json(self.bound(v['universe']))
        self.identity=legacy.sibling('generic_existing_identity',legacy.profile_path)
        self.identity.validate_target(self.root,self.target)
        u=self.universe
        c.need(isinstance(u,dict) and set(u)=={'format','units','excluded'} and u['format']=='verimission-universe-v1' and
               isinstance(u['units'],list) and u['units'],'Use the fixed neutral universe')
        self.units={}
        for row in u['units']:
            c.need(isinstance(row,dict) and set(row)=={'id','identity','deliverable','depends_on'} and
                   c.text(row['id']) and c.text(row['identity']) and row['id'] not in self.units and
                   c.names(row['depends_on'],True),'Unique stable units and explicit dependencies required')
            self.path(row['deliverable'],False);self.units[row['id']]=row
        c.need(len({row['identity'] for row in self.units.values()})==len(self.units),'Physical aliases cannot inflate units')
        c.need(all(set(row['depends_on'])<=set(self.units) for row in self.units.values()),'Unknown dependency')
        c.need(isinstance(u['excluded'],list) and all(isinstance(x,dict) and set(x)=={'id','reason'} and
               x['id'] in self.units and c.text(x['reason']) for x in u['excluded']),'Explicit approved exclusion reasons required')
        excluded=[x['id'] for x in u['excluded']];c.need(len(set(excluded))==len(excluded),'Duplicate exclusions')
        self.live=set(self.units)-set(excluded)
        for name in ('reviews','unit_manifests'):
            c.need(isinstance(v[name],dict) and set(v[name])==self.live,'Per-unit inputs must match the entire live universe')
            for value in v[name].values():self.path(value,False)
        self.graph_ref=self.ref(self.path(v['callgraph']))
        nodes,self.edges,_,self.unknown,self.inventory_complete=closure.normalize(
            closure.load_json(self.bound(self.graph_ref)),{'format':'decompile-grades-v1','grades':{}})
        c.need(nodes==set(self.units),'Graph and fixed universe differ')
        modes=[];anchors=set()
        for uid in sorted(self.live):
            path=self.path(v['unit_manifests'][uid],False)
            if not path.is_file():continue
            unit=closure.load_json(path);checked=self.identity.validate_unit(self.root,self.target,unit)
            c.need(unit['id']==uid and self.identity.manifest_digest(checked['identity'])==self.units[uid]['identity'],
                   'Manifest identity differs from the approved physical unit')
            actual=checked['identity'];anchor=tuple(actual[k] for k in ('binary_sha256','segment','address_space','file_offset','isa_mode'))
            c.need(anchor not in anchors,'Boundary variants of one physical entry cannot increase the count')
            anchors.add(anchor);modes.append(unit['isa_mode'])
        c.match_target(self.profile,self.target,modes)
        for ref in self.profile['dependencies']['platform_images'].values():
            self.bound(ref)
            if v['category']=='independent-validated':
                c.need(ref['sha256']!=self.target['sha256'],'The original target image cannot be relabelled as an external platform')
        b=v['backend'];c.need(isinstance(b,dict) and set(b)=={'kind','config'} and b['kind']==self.profile['backend'],
                             'Backend must match the pinned profile; no fallback')
        self.backend_config=closure.load_json(self.bound(b['config']))
        if v['category']=='independent-validated':c.need(self.profile['validation']['method']!='none','Full reconstruction needs semantic validation')
        c.need(c.names(v['input_patterns']),'Declare the relevant input set')
        for pattern in v['input_patterns']:
            c.need(not Path(pattern).is_absolute() and not PureWindowsPath(pattern).drive and
                   '..' not in Path(pattern).parts and ':' not in pattern and
                   '.harness' not in [part.casefold() for part in Path(pattern).parts],'Unsafe input pattern')
        self.before=self.inputs()
        self.context_value={'contract':self.contract_ref,'profile':v['profile'],'backend_config':b['config'],
            'modules':{p.name:legacy.sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
            'identity_helper_sha256':legacy.sha(legacy.profile_path)}
        self.context_ref=None;self.backend=None

    def path(self,value,exists=True):
        result=closure.evidence_path(self.root,value)
        if exists:c.need(result.is_file(),'Required physical input is missing: '+str(value))
        return result
    def ref(self,path):
        p=Path(path).resolve();c.need(p.is_relative_to(self.root),'Evidence must stay inside the project')
        return {'path':p.relative_to(self.root).as_posix(),'sha256':legacy.sha(p)}
    def bound(self,ref):
        c.reference(ref);p=self.path(ref['path']);c.need(legacy.sha(p)==ref['sha256'],'Evidence changed: '+ref['path']);return p
    def remaining(self):
        value=self.deadline-time.monotonic()
        if value<=0:raise TimeoutError('Qualification budget exhausted; no complete observation is authorized')
        return value
    def inputs(self):
        result={}
        for pattern in self.contract['input_patterns']:
            for p in self.root.glob(pattern):
                if p.is_file():
                    name=p.relative_to(self.root).as_posix();result[name]=legacy.sha(self.path(name))
        return result
    def start(self):
        self.remaining();self.work.mkdir(parents=True,exist_ok=False)
        context_path=self.path('qualification-context/'+c.digest(self.context_value)+'.json',False)
        context_path.parent.mkdir(parents=True,exist_ok=True);raw=c.encoded(self.context_value)
        if context_path.exists():c.need(context_path.read_bytes()==raw,'Context artifact was changed')
        else:
            with context_path.open('xb') as stream:stream.write(raw)
        self.context_ref=self.ref(context_path)
        self.backend=sibling('qualification_c').CBackend(self) if self.profile['backend']=='c-source-v1' else sibling('qualification_external').ExternalBackend(self)
    def current(self):
        self.remaining();self.bound(self.contract_ref);self.bound(self.contract['profile']);self.bound(self.contract['backend']['config'])
        c.need(self.inputs()==self.before,'The declared input set changed during verification')
        c.need({p.name:legacy.sha(p) for p in Path(__file__).parent.glob('*.py')}==self.context_value['modules'] and
               legacy.sha(legacy.profile_path)==self.context_value['identity_helper_sha256'],'Verifier implementation changed during verification')
        if self.backend is not None:
            self.backend.context_current() if self.profile['backend']=='c-source-v1' else self.backend.current()
    def bindings(self,uid):
        original=self.units[uid]
        refs={'deliverable':self.ref(self.path(original['deliverable'])),
              'unit_profile':self.ref(self.path(self.contract['unit_manifests'][uid])),
              'recovery_review':self.ref(self.path(self.contract['reviews'][uid])),
              'qualification_contract':self.contract_ref,'qualification_profile':self.contract['profile'],
              'qualification_context':self.context_ref,'target_profile':self.contract['target'],
              'original_binary':self.ref(self.identity.project_file(self.root,self.target['binary'])),
              'universe':self.contract['universe'],'callgraph':self.graph_ref,'backend_config':self.contract['backend']['config']}
        unit=closure.load_json(self.bound(refs['unit_profile']));checked=self.identity.validate_unit(self.root,self.target,unit)
        c.need(unit['id']==uid and self.identity.manifest_digest(checked['identity'])==original['identity'],'Physical unit changed')
        seen=set();todo=list(original['depends_on'])
        while todo:
            dependency=todo.pop()
            if dependency in seen:continue
            seen.add(dependency)
            refs['dependency-source-'+c.digest(dependency)]=self.ref(self.path(self.units[dependency]['deliverable']))
            todo.extend(self.units[dependency]['depends_on'])
        # Direct references let the native live view notice drift without parsing nested JSON.
        for name,ref in self.profile['dependencies']['platform_images'].items():
            self.bound(ref);refs['platform-'+c.digest(name)]=ref
        if self.profile['backend']=='external-v1':
            for field,role in [('witnesses','witnesses'),('negative_candidates','negative_candidate')]:
                ref=self.backend_config[field].get(uid)
                if ref:self.bound(ref);refs[role]=ref
        tools=self.backend_config['tools'].values() if self.profile['backend']=='c-source-v1' else [self.backend_config]
        for tool in tools:
            for name,checksum in tool['files'].items():
                ref={'path':name,'sha256':checksum};self.bound(ref);refs['tool-resource-'+c.digest(name)]=ref
            executable=Path(tool['argv'][0])
            if not executable.is_absolute():
                import shutil
                executable=Path(shutil.which(str(executable)) or self.root/executable)
            executable=executable.resolve()
            if executable.is_relative_to(self.root):
                ref={'path':executable.relative_to(self.root).as_posix(),'sha256':tool['executable_sha256']}
                self.bound(ref);refs['tool-executable-'+c.digest(ref['path'])]=ref
        return refs
    def reviewed(self,uid,refs):
        review=closure.load_json(self.bound(refs['recovery_review']))
        fields={'format','unit','source_sha256','category','representation','reviewer','body_complete',
                'unresolved_operations','dependencies_complete','dependencies','marker_justifications'}
        c.need(isinstance(review,dict) and set(review)==fields and review['format']=='decompile-recovery-review-v1' and
               review['unit']==uid and review['source_sha256']==refs['deliverable']['sha256'],'Recovery review is missing/stale or for another unit')
        c.need(review['category']==self.contract['category'],'Review cannot change the predeclared category')
        c.need(review['reviewer'] in self.profile['reviewers'] and type(review['body_complete']) is bool and
               c.names(review['unresolved_operations'],True) and type(review['dependencies_complete']) is bool and
               c.names(review['dependencies'],True) and isinstance(review['marker_justifications'],dict),'Explicit source-bound reviewer/completeness/dependency evidence required')
        representations={'analysis':'analytical','mechanical-translation':'mechanical','recompilable':'structured','independent-validated':'structured'}
        states={'D-a':'pass','D-b':'pass' if review['representation']==representations[self.contract['category']] else 'fail',
                'D-c':'pass' if review['dependencies_complete'] and set(review['dependencies'])==set(self.units[uid]['depends_on']) and
                       self.inventory_complete and uid not in self.unknown and set(self.edges[uid] or [])==set(self.units[uid]['depends_on']) else 'fail',
                'D-d':'pass' if review['body_complete'] and not review['unresolved_operations'] else 'fail'}
        raw=self.bound(refs['deliverable']).read_bytes();c.need(bool(raw.strip()),'Empty artifact is not an effective recovery')
        markers=[m for m in self.profile['stub_markers'] if m.casefold() in raw.decode('utf-8',errors='replace').casefold()]
        for marker in markers:
            justification=review['marker_justifications'].get(marker)
            if not justification:states['D-d']='fail';continue
            c.need(isinstance(justification,dict) and set(justification)=={'reason','evidence'} and c.text(justification['reason']),
                   'Marker exceptions need a source-bound reason and physical evidence')
            self.bound(justification['evidence']);refs['marker-justification-'+c.digest(marker)]=justification['evidence']
        return states
    def previous(self,ref):
        if not ref:return {}
        packet=closure.load_json(self.bound(ref))
        c.need(packet.get('format')=='verimission-measurement-v1' and packet.get('complete') is True and isinstance(packet.get('units'),list),
               'Previous observations need the canonical complete measurement format')
        rows={r['id']:r for r in packet['units']}
        c.need(len(rows)==len(packet['units']) and set(rows)==self.live,'Previous universe differs or contains duplicates')
        for row in rows.values():
            artifacts=row.get('artifacts',{})
            c.need(artifacts.get('qualification_contract')==self.contract_ref and artifacts.get('qualification_profile')==self.contract['profile'],
                   'Category/profile/contract changed; use explicit authorized mission revision, never silent cache reclassification')
        return rows
    def observe(self,uid,previous=None,force=False):
        criteria={k:'unknown' for k in c.CRITERIA};refs={'qualification_contract':self.contract_ref,
            'qualification_profile':self.contract['profile'],'qualification_context':self.context_ref}
        observed={'executed':False,'healthy_passed':False,'known_bad_rejected':False};error=None
        try:
            refs.update(self.bindings(uid));states=self.reviewed(uid,refs);criteria.update(states)
            if all(states[k]=='pass' for k in ('D-a','D-b','D-d')):
                observed=self.backend.observe(uid,previous,force)
                for role,ref in observed['artifacts'].items():
                    self.bound(ref)
                    c.need(role not in refs or refs[role]==ref,'Adapter cannot replace canonical source/identity/contract bindings')
                    refs[role]=ref
                criteria={k:c.combine(states[k],observed['criteria'][k]) if k in states else observed['criteria'][k] for k in c.CRITERIA}
            for ref in refs.values():self.bound(ref)
        except (TimeoutError,subprocess.TimeoutExpired,c.ProtocolError):raise
        except (ValueError,OSError,KeyError,TypeError) as fault:
            error=str(fault);criteria={k:'unknown' for k in c.CRITERIA}
        for k in set(c.CRITERIA)-c.REQUIRED[self.contract['category']]:criteria[k]='not-applicable'
        assessment=c.verdict(self.contract['category'],criteria)
        receipt={'format':'decompile-qualification-receipt-v1','run_id':self.run_id,'unit':uid,
            'identity':self.units[uid]['identity'],'category':self.contract['category'],'criteria':criteria,
            'assessment':assessment,'executed':observed['executed'],'healthy_passed':observed['healthy_passed'],
            'known_bad_rejected':observed['known_bad_rejected'],'artifacts':refs,'error':error,
            'evidence_scope':{'profile':self.profile['id'],'language':self.profile['language'],
                'method':self.profile['validation']['method'],'assumptions':self.profile['validation']['assumptions'],
                'observables':self.profile['validation']['observables']},
            'semantic_truth_authenticated':False,'promotion_authorized':False}
        path=self.work/(c.digest(uid)[:20]+'.json')
        with path.open('xb') as stream:stream.write(c.encoded(receipt))
        return {'id':uid,'identity':self.units[uid]['identity'],'gates':c.neutral_gates(self.contract['category'],criteria),
                'artifacts':{**refs,'qualification_receipt':self.ref(path)}}
    def all_units(self,previous=None,force_ids=()):
        old=self.previous(previous);self.start()
        rows=[self.observe(uid,old.get(uid),uid in force_ids) for uid in sorted(self.live)]
        eligible=closure.qualified_units({r['id'] for r in rows if all(s=='pass' for s in r['gates'].values())},
                                         {uid:r['depends_on'] for uid,r in self.units.items()})
        self.current()
        for row in rows:
            for ref in row['artifacts'].values():self.bound(ref)
        return rows,sorted(eligible)

def measure(project,contract_file,run_id,context,previous=None):
    qualifier=Qualification(project,contract_file,run_id,context);rows,eligible=qualifier.all_units(previous)
    return {'format':'verimission-measurement-v1','run_id':run_id,'context_sha256':context,
            'universe_sha256':qualifier.contract['universe']['sha256'],'complete':True,'claimed_verified':len(eligible),'units':rows}

def audit(project,contract_file,run_id,context,selection,previous):
    qualifier=Qualification(project,contract_file,run_id,context);plan=closure.load_json(qualifier.path(selection))
    c.need(isinstance(plan,dict) and isinstance(plan.get('units'),list) and len(set(plan['units']))==len(plan['units']) and
           set(plan['units'])<=qualifier.live,'Unknown/duplicate audit selection')
    rows,eligible=qualifier.all_units(previous,plan['units']);mapped={r['id']:r for r in rows};selected=[];controls=True
    for uid in plan['units']:
        row=mapped[uid];proof=closure.load_json(qualifier.bound(row['artifacts']['qualification_receipt']))
        passed=uid in eligible and proof['executed'] and proof['healthy_passed'] and proof['known_bad_rejected']
        controls=controls and passed
        selected.append({'id':uid,'status':'pass' if passed else 'fail','executed':proof['executed'],'artifacts':row['artifacts']})
    control_path=qualifier.work/'audit-controls.json'
    with control_path.open('xb') as stream:stream.write(c.encoded({'selected':plan['units'],'eligible':eligible,'controls_passed':bool(selected) and controls}))
    qualifier.current()
    return {'format':'verimission-measurement-audit-v1','run_id':run_id,'context_sha256':context,'complete':True,
            'plan_id':plan['id'],'recount_ids':eligible,'units':selected,'controls':{
            'healthy_passed':bool(selected) and controls,'known_bad_rejected':bool(selected) and controls,
            'artifacts':{'controls':qualifier.ref(control_path)}}}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',required=True)
    parser.add_argument('--contract',required=True);args=parser.parse_args()
    try:
        kind=os.environ['VERIMISSION_MEASUREMENT_KIND'];run=os.environ['VERIMISSION_MEASUREMENT_RUN_ID'];context=os.environ['VERIMISSION_MEASUREMENT_CONTEXT_SHA256']
        previous=json.loads(os.environ.get('VERIMISSION_MEASUREMENT_PREVIOUS','null'))
        root=Path(args.project).resolve(strict=True)
        if kind=='measurement':value=measure(root,args.contract,run,context,previous)
        else:
            c.need(kind=='audit','Unknown observation kind')
            selection=Path(os.environ['VERIMISSION_AUDIT_SELECTION']).resolve()
            c.need(selection.is_relative_to(root),'Audit selection must stay inside the project')
            value=audit(root,args.contract,run,context,selection.relative_to(root).as_posix(),previous)
        output=Path(os.environ['VERIMISSION_MEASUREMENT_REPORT'])
        if output.is_absolute():
            output=output.resolve();c.need(output.is_relative_to(root),'Output must remain inside the project');output=output.relative_to(root)
        path=closure.evidence_path(root,str(output))
        with path.open('xb') as stream:stream.write(c.encoded(value))
        print(json.dumps({'complete':True,'kind':kind,'promotion_authorized':False}));return 0
    except (ValueError,OSError,KeyError,TypeError,TimeoutError,subprocess.TimeoutExpired) as error:
        print(json.dumps({'complete':False,'error':str(error),'promotion_authorized':False}));return 2

if __name__=='__main__':raise SystemExit(main())
