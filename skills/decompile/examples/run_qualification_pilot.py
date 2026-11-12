"""Disposable Decompile3.0 / Control8.4 pilot; optional real host GCC, never real firmware."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/'tests'))
from qualification_fixture import QualificationFixture,sha
from completion_fixture import profile
from run_measurement_pilot import NATIVE_BACKEND

def run(harness,compiler=None):
    spec=importlib.util.spec_from_file_location('qualification_native_harness',Path(harness).resolve())
    engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    with QualificationFixture() as f:
        good='int f(int x){return x+1;}'
        bad='int f(int x){return x+2;}'
        if compiler:
            compiler=str(Path(compiler).resolve(strict=True))
            good="int main(int argc,char **argv){return (argv[1][0]-'0')+1;}"
            bad="int main(int argc,char **argv){return (argv[1][0]-'0')+2;}"
            (f.root/'reference.c').write_text(good)
            built=subprocess.run([compiler,'-std=c99','-O0','reference.c','-o','stock.bin'],cwd=f.root,capture_output=True,timeout=30)
            assert built.returncode==0,built.stderr
            (f.root/'native_backend.py').write_text(NATIVE_BACKEND)
            raw=(f.root/'stock.bin').read_bytes()
            assert raw[:6]==b'\x7fELF\x02\x01' and int.from_bytes(raw[18:20],'little')==62,'This native pilot specifically requires ELF64 x86_64 GCC'
            f.target.update(architecture='x86_64',sha256=sha(f.root/'stock.bin'))
            f.target['segments'][0]['size']=len(raw)
            f.target['analysis_configuration']={'tool':'native GCC synthetic fixture','version':'pinned executable','settings':{}}
            f.unit.update(target_sha256=f.target['sha256'],size=len(raw),isa_mode='native')
            f.config['units']['U1']['symbol']='main'
            f.config['profile']['execution_kind']='process-image'
            f.config['tools']['compiler']={'argv':[compiler,'-std=c99','-O0','{source}','-o','{output}'],
                'preprocess_argv':[compiler,'-std=c99','-E','-P','{source}','-o','{output}'],'executable_sha256':sha(compiler),'files':{}}
            f.config['tools']['executor']={'argv':[sys.executable,'native_backend.py','{stock}','{image}','{witnesses}',
                '{report}','{unit}','{entry}','{run}'],'executable_sha256':sha(sys.executable),
                'files':{'native_backend.py':sha(f.root/'native_backend.py')}}
            f.qprofile['id']='native-gcc-x86_64-pilot'
            f.qprofile['target'].update(architectures=['x86_64'],isa_modes=['native'])
            f.qprofile['build']={'format':'elf','bits':64,'machine':62}
            f.qprofile['validation'].update(execution_kind='process-image',observables=['returncode','stdout_hex','stderr_hex','termination'])
        (f.root/'src/U1.c').write_text(good);(f.root/'negative/U1.c').write_text(bad)
        f.write('target.json',f.target);f.write('units/U1.json',f.unit)
        f.universe['units'][0]['identity']=profile().manifest_digest(profile().validate_unit(f.root,f.target,f.unit)['identity'])
        f.write('universe.json',f.universe)
        f.config.update(target=f.ref('target.json'),universe=f.ref('universe.json'))
        f.review['source_sha256']=f.qreview['source_sha256']=sha(f.root/'src/U1.c')
        f.write('reviews/U1.json',f.review);f.write('reviews/U1.recovery.json',f.qreview);f.save_backend()
        f.contract.update(target=f.ref('target.json'),universe=f.ref('universe.json'))
        f.contract['input_patterns']+=['stock.bin','native_backend.py']
        f.save_profile()
        f.write('grades.json',{'format':'decompile-grades-v1','grades':{'U1':'G4-recon'}})
        protected={name:sha(f.root/name) for name in ('contract.json','profile.json','config.json','tool.py')}
        if compiler:protected['native_backend.py']=sha(f.root/'native_backend.py')
        policy={'schema':1,'universe':f.ref('universe.json'),'criterion':'M','output_pattern':'measurements/{run}.json',
            'required_gates':['D-a','D-b','D-c','D-d','D-e','D-f'],'protected_files':protected,
            'input_patterns':f.contract['input_patterns'],'acceptance_minimum':1,
            'pinned_roles':['qualification_contract','qualification_profile','witnesses','negative_source','verifier_context'],
            'audit':{'criterion':'A','output_pattern':'audits/{run}.json','every_cycles':3,'sample_size':1}}
        criteria=[{'id':cid,'description':'Current six-gate qualification' if cid=='M' else 'Fresh selected audit and exact recount',
            'argv':[sys.executable,str(SKILL/'scripts/qualification.py'),'--project',str(f.root),'--contract','contract.json'],
            'artifacts':list(protected)} for cid in ('M','A')]
        mission={'objective':'Qualify one synthetic unit with a fixed target profile', 'mode':'light',
            'in_scope':['one synthetic unit'],'out_of_scope':['real firmware','universal equivalence'],
            'criteria':criteria,'measurement_policy':policy,'budget':{'max_cycles':10,'max_cycle_seconds':600,
                'max_check_seconds':120,'max_no_progress':10,'max_same_failures':10,'consolidate_every':10}}
        h=engine.Harness(f.root);h.init(mission)
        def start(ids=None):
            review=h.review('completion')
            return h.start({'topic':'completion','task':'qualify fixed category','premise':'current physical evidence',
                'residual':'validate source and closure','review_id':review['review']['id'],'reviewed_claims':list(review['claims']),
                'criteria':ids or ['M'],'approach':{'method':'six generic gates','inputs':'bound source and profile','environment':'synthetic pilot'},
                'reverify_reason':'Revalidate the declared category without weakening the profile'})['cycle']
        def close(cycle):h.close(cycle,'verified','Retain only currently qualified units')
        first=start();checked=h.check(first,'M');assert checked['passed'],checked
        assert h.measurement_report()['counts']['verified']==0
        close(first);assert h.measurement_report()['counts']['verified']==1
        # A headline is not current proof: even the original image is a direct live binding.
        original=(f.root/'stock.bin').read_bytes();(f.root/'stock.bin').write_bytes(original+b'changed')
        assert h.measurement_report()['counts']['stale']==1
        (f.root/'stock.bin').write_bytes(original)
        (f.root/'src/U1.c').write_text(bad)
        assert h.measurement_report()['counts']['verified']==0
        assert h.measurement_report()['counts']['stale']==1
        command=[sys.executable,'-B',str(SKILL/'scripts/census_bars.py'),'--project',str(f.root),
            '--callgraph','callgraph.json','--grades','grades.json','--harness',str(Path(harness).resolve()),'--json']
        shown=subprocess.run(command,capture_output=True,text=True,timeout=30)
        assert shown.returncode==0,shown.stdout+shown.stderr
        assert json.loads(shown.stdout)['result']['counts']['stale']==1
        def reviews():
            f.review['source_sha256']=f.qreview['source_sha256']=sha(f.root/'src/U1.c')
            f.write('reviews/U1.json',f.review);f.write('reviews/U1.recovery.json',f.qreview)
        reviews();second=start();wrong=h.check(second,'M');assert wrong['passed'],wrong
        assert wrong['measurement']['verified_count']==0
        close(second);assert h.measurement_report()['counts']['verified']==0
        (f.root/'src/U1.c').write_text(good);reviews()
        third=start(['M','A']);fixed=h.check(third,'M');assert fixed['passed'],fixed
        assert h.measurement_audit_plan(third)['units']==['U1']
        audit=h.check(third,'A');assert audit['passed'],audit
        close(third);assert h.measurement_report()['counts']['verified']==1
        assert h.validate()['passed'] and h.accept_mission()['accepted']
        with h.state() as state:assert state['cycles'][-1]['measurement_progress']['new_unit_ids']==[]
        return {'passed':True,'version':'decompile-3.0','actual_gcc_and_host_process_execution':bool(compiler),
            'six_generic_gates':True,'close_required':True,'original_binary_drift_stale':True,'source_drift_stale':True,
            'incorrect_candidate_excluded':True,'audit_forced_reexecution':True,'repair_not_new_work':True,
            'live_bars_preserved':True,'final_verified':1,'real_firmware_or_universal_equivalence_tested':False,
            'installed':False,'published':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--harness',required=True)
    parser.add_argument('--compiler',help='Optional approved native ELF64 x86_64 C compiler')
    args=parser.parse_args();print(json.dumps(run(args.harness,args.compiler),indent=2))
