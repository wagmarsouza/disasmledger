"""Execute an explicitly pinned target verifier; never import self-reported counts."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

def sibling(name):
    spec=importlib.util.spec_from_file_location('qualification_external_'+name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

c=sibling('qualification_contract');closure=sibling('closure')

class ExternalBackend:
    def __init__(self,owner):
        self.owner=owner;self.config=owner.backend_config;self.packet=None;self.requests={}
        v=self.config
        c.need(isinstance(v,dict) and set(v)=={'format','argv','executable_sha256','files','entrypoints','witnesses','negative_candidates','timeout_seconds'} and
               v['format']=='decompile-external-verifier-v1','Use the exact external verifier recipe')
        c.need(isinstance(v['entrypoints'],dict) and set(v['entrypoints'])==owner.live and
               all(c.text(x) for x in v['entrypoints'].values()) and len(set(v['entrypoints'].values()))==len(v['entrypoints']),
               'Declare unambiguous target-specific entrypoints for the entire live inventory')
        boundary=set(owner.profile['dependencies']['allowed_external_calls'])
        c.need(not boundary.intersection(set(v['entrypoints'].values())|owner.live),
               'An inventoried callee cannot be renamed into an external service')
        c.need(type(v['timeout_seconds']) is int and 1<=v['timeout_seconds']<=1800,'A finite adapter timeout is required')
        for field,required in [('witnesses',owner.profile['validation']['method']=='differential'),
                               ('negative_candidates',owner.contract['category']=='independent-validated')]:
            c.need(isinstance(v[field],dict) and set(v[field])==(owner.live if required else set()),
                   'Freeze the required witness/known-bad inputs before executing the verifier')
            for ref in v[field].values():owner.bound(ref)
        self.tool()

    def tool(self):
        v=self.config;argv=v['argv']
        c.need(isinstance(argv,list) and argv and all(c.text(x) for x in argv) and isinstance(v['files'],dict),
               'An explicit verifier argv and complete static resource set are required')
        exe=Path(argv[0]) if Path(argv[0]).is_absolute() else Path(shutil.which(argv[0]) or self.owner.root/argv[0])
        exe=exe.resolve();c.need(exe.is_file(),'Approved verifier executable is missing')
        import hashlib
        c.need(hashlib.sha256(exe.read_bytes()).hexdigest()==v['executable_sha256'],'Approved verifier executable changed')
        for name,expected in v['files'].items():self.owner.bound({'path':name,'sha256':expected})
        for arg in argv[1:]:
            candidate=Path(arg) if Path(arg).is_absolute() else self.owner.root/arg
            if candidate.is_file():
                resolved=candidate.resolve();c.need(resolved.is_relative_to(self.owner.root),'Static argument files must be project-bound')
                c.need(resolved.relative_to(self.owner.root).as_posix() in v['files'],'A static verifier argument was omitted from the pinned files')
        return [str(exe),*argv[1:]]

    def current(self):self.tool()

    def prepare(self):
        if self.packet is not None:return
        o=self.owner;rows=[]
        for uid in sorted(o.live):
            refs={};ready=False
            try:
                refs=o.bindings(uid);states=o.reviewed(uid,refs)
                ready=all(states[k]=='pass' for k in ('D-a','D-b','D-d'))
            except (ValueError,OSError,KeyError,TypeError):pass
            row={'id':uid,'identity':o.units[uid]['identity'],'entrypoint':self.config['entrypoints'][uid],
                 'depends_on':o.units[uid]['depends_on'],'ready':ready,'artifacts':refs}
            self.requests[uid]=row;rows.append(row)
        request={'format':'decompile-adapter-request-v1','run_id':o.run_id,'command_context_sha256':o.command_context,
            'category':o.contract['category'],'profile':o.profile,'profile_ref':o.contract['profile'],
            'contract_ref':o.contract_ref,'target_ref':o.contract['target'],'universe_ref':o.contract['universe'],
            'original_binary':o.ref(o.identity.project_file(o.root,o.target['binary'])),
            'criteria':list(c.CRITERIA),'required_criteria':sorted(c.REQUIRED[o.contract['category']]),'units':rows}
        source=o.work/'adapter-request.json';output=o.work/'adapter-observation.json'
        with source.open('xb') as stream:stream.write(c.encoded(request))
        argv=self.tool()
        try:
            result=subprocess.run(argv,cwd=o.root,shell=False,capture_output=True,
                timeout=min(o.remaining(),self.config['timeout_seconds']),
                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','DECOMPILE_QUALIFICATION_REQUEST':str(source),
                     'DECOMPILE_QUALIFICATION_REPORT':str(output)})
        except subprocess.TimeoutExpired as error:
            for name,raw in [('stdout',error.stdout or b''),('stderr',error.stderr or b'')]:
                with (o.work/('adapter.'+name)).open('xb') as stream:stream.write(raw)
            raise
        for name,raw in [('stdout',result.stdout),('stderr',result.stderr)]:
            with (o.work/('adapter.'+name)).open('xb') as stream:stream.write(raw)
        self.tool();o.remaining()
        try:
            c.need(result.returncode==0 and output.is_file(),'External verifier did not produce a complete successful observation')
            value=closure.load_json(output)
            c.need(isinstance(value,dict) and set(value)=={'format','run_id','command_context_sha256','category','method','complete','units'} and
                   value['format']=='decompile-adapter-observation-v1','External verifiers emit observations, never their own counters')
            c.need(value['run_id']==o.run_id and value['command_context_sha256']==o.command_context and
                   value['category']==o.contract['category'] and value['method']==o.profile['validation']['method'] and
                   value['complete'] is True and isinstance(value['units'],list),'Stale/incomplete/mixed-category adapter output')
            mapped={}
            for row in value['units']:
                c.need(isinstance(row,dict) and set(row)=={'id','identity','category','source_sha256','criteria','artifacts','validation'} and
                       row['id'] in o.live and row['id'] not in mapped,'Adapter omitted, duplicated or substituted an inventory unit')
                uid=row['id'];expected=self.requests[uid]
                c.need(row['identity']==expected['identity'] and row['category']==o.contract['category'] and
                       row['source_sha256']==expected['artifacts'].get('deliverable',{}).get('sha256'),
                       'Adapter proof belongs to another physical source/unit/category')
                c.verdict(o.contract['category'],row['criteria'])
                c.need(isinstance(row['artifacts'],dict) and all(c.text(k) for k in row['artifacts']),'Named physical adapter evidence required')
                for ref in row['artifacts'].values():o.bound(ref)
                v=row['validation']
                c.need(isinstance(v,dict) and set(v)=={'verdict','healthy_control','known_bad_control','executed','case_ids','observables','scenarios'} and
                       v['verdict'] in ('matched','equivalent','diverged','unknown','not-applicable') and
                       v['healthy_control'] in ('pass','fail','unknown') and v['known_bad_control'] in ('rejected','missed','unknown') and
                       type(v['executed']) is bool and all(c.names(v[k],True) for k in ('case_ids','observables','scenarios')),
                       'Explicit execution, verdict, controls and exact scope are required')
                mapped[uid]=row
            c.need(set(mapped)==o.live,'The adapter must report every live unit exactly once')
            self.packet=mapped;self.output_ref=o.ref(output);self.request_ref=o.ref(source)
        except (ValueError,OSError,KeyError,TypeError) as error:
            raise o.ProtocolError(str(error)) from None

    def observe(self,uid,previous=None,force=False):
        self.prepare();o=self.owner;row=self.packet[uid];criteria=dict(row['criteria']);refs=dict(row['artifacts'])
        v=row['validation'];category=o.contract['category'];profile=o.profile['validation']
        refs.update(adapter_observation=self.output_ref,adapter_request=self.request_ref,
                    adapter_stdout=o.ref(o.work/'adapter.stdout'),adapter_stderr=o.ref(o.work/'adapter.stderr'))
        c.need(v['executed'],'This external protocol requires fresh verifier execution; cached declarations cannot impersonate an audit')
        if 'D-e' in c.REQUIRED[category]:
            artifact=refs['constructed_artifact'];o.bound(artifact);binding=closure.load_json(o.bound(refs['build_binding']))
            c.need(isinstance(binding,dict) and set(binding)=={'format','unit','run_id','source_sha256','artifact_sha256','profile_sha256','exit_code'} and
                   binding['format']=='decompile-build-binding-v1' and binding['unit']==uid and binding['run_id']==o.run_id and
                   binding['source_sha256']==row['source_sha256'] and binding['artifact_sha256']==artifact['sha256'] and
                   binding['profile_sha256']==o.contract['profile']['sha256'] and type(binding['exit_code']) is int and binding['exit_code']==0,
                   'Construction proof is stale, failed or unbound to the actual source/artifact/profile')
            if o.profile['build']['format']=='elf':c.check_image(o.bound(artifact).read_bytes(),o.profile)
        healthy=False;bad=False
        if category=='independent-validated':
            method=profile['method'];expected='matched' if method=='differential' else 'equivalent'
            proof=closure.load_json(o.bound(refs['validation_context']));o.bound(refs['proof_certificate'])
            negative=refs['negative_candidate'];o.bound(negative)
            c.need(negative==self.config['negative_candidates'][uid],'The verifier replaced the preapproved known-bad input')
            c.need(negative['sha256'] not in (row['source_sha256'],refs['constructed_artifact']['sha256']),
                   'A known-bad control cannot be the same source/artifact as the healthy candidate')
            expected_fields={'format','unit','run_id','command_context_sha256','original_sha256','candidate_sha256',
                             'constructed_sha256','profile_sha256','method','verdict','assumptions','observables'}
            c.need(isinstance(proof,dict) and set(proof)==expected_fields and proof['format']=='decompile-validation-context-v1' and
                   proof['unit']==uid and proof['run_id']==o.run_id and proof['command_context_sha256']==o.command_context and
                   proof['original_sha256']==o.target['sha256'] and proof['candidate_sha256']==row['source_sha256'] and
                   proof['constructed_sha256']==refs['constructed_artifact']['sha256'] and proof['profile_sha256']==o.contract['profile']['sha256'] and
                   proof['method']==method and proof['assumptions']==profile['assumptions'] and proof['observables']==profile['observables'],
                   'Semantic evidence must bind both original and candidate under the predeclared method, assumptions and observables')
            c.need(set(v['observables'])==set(profile['observables']),'A required observable cannot be omitted or replaced')
            healthy=v['healthy_control']=='pass';bad=v['known_bad_control']=='rejected'
            controls=closure.load_json(o.bound(refs['control_evidence']))
            expected_controls={'format':'decompile-control-binding-v1','unit':uid,'run_id':o.run_id,
                'command_context_sha256':o.command_context,'original_sha256':o.target['sha256'],
                'candidate_sha256':row['source_sha256'],'constructed_sha256':refs['constructed_artifact']['sha256'],
                'negative_sha256':negative['sha256'],'profile_sha256':o.contract['profile']['sha256'],
                'healthy_passed':healthy,'known_bad_rejected':bad}
            c.need(controls==expected_controls,'Control evidence is stale or unbound to the original/candidate/approved negative')
            valid=proof['verdict']==expected and v['verdict']==expected and healthy and bad
            if method=='differential':
                c.need(refs['witnesses']==self.config['witnesses'][uid],'The verifier replaced the predeclared witness corpus')
                corpus=closure.load_json(o.bound(refs['witnesses']));cases=c.check_witnesses(corpus,o.profile)
                c.need(set(v['case_ids'])=={case['id'] for case in cases} and
                       set(profile['required_scenarios'])<=set(v['scenarios']),'Executed witnesses/scenario obligations are incomplete')
            criteria['D-f']=c.combine(criteria['D-f'],'pass' if valid else 'fail')
        return {'criteria':criteria,'artifacts':refs,'executed':v['executed'],
                'healthy_passed':healthy,'known_bad_rejected':bad}
