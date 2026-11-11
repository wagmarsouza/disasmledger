"""Disposable protocol pilot; --compiler adds actual native compilation/process execution."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/'tests'))
from completion_fixture import Fixture,profile,sha

NATIVE_BACKEND='''import hashlib,json,subprocess,sys
from pathlib import Path
stock,image,corpus,output,unit,entry,run=sys.argv[1:]
def ref(path):return {'path':Path(path).resolve().relative_to(Path.cwd()).as_posix(),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
image_ref=ref(image);rows=[]
for case in json.loads(Path(corpus).read_text())['cases']:
 a=subprocess.run([stock,str(case['input'])],capture_output=True,timeout=3)
 b=subprocess.run([image,str(case['input'])],capture_output=True,timeout=3)
 assert ref(image)==image_ref
 def observation(p):return {'returncode':p.returncode,'stdout_hex':p.stdout.hex(),'stderr_hex':p.stderr.hex()}
 rows.append({'id':case['id'],'stock':observation(a),'candidate':observation(b),'stock_status':'returned' if a.returncode>=0 else 'fault',
              'candidate_status':'returned' if b.returncode>=0 else 'fault','reset':True,
              'execution':[{'role':'candidate','image':image_ref,'pc':None}]})
result={'format':'disasm-execution-v1','unit':unit,'entry':entry,'run_id':run,'image':image_ref,'stock':ref(stock),
        'witnesses':ref(corpus),'complete':True,'cases':rows}
with Path(output).open('x') as f:json.dump(result,f)
'''

def run(harness,compiler=None):
    s=importlib.util.spec_from_file_location('pilot_native_metric_engine',Path(harness).resolve())
    h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
    with Fixture() as f:
        good_source='int f(int x){return x+1;}'
        bad_source='int f(int x){return x+2;}'
        if compiler:
            compiler=str(Path(compiler).resolve(strict=True))
            good_source="int main(int argc,char **argv){return (argv[1][0]-'0')+1;}"
            bad_source="int main(int argc,char **argv){return (argv[1][0]-'0')+2;}"
            (f.root/'reference.c').write_text(good_source)
            p=subprocess.run([compiler,'-std=c99','-O0',str(f.root/'reference.c'),'-o',str(f.root/'stock.bin')],capture_output=True,timeout=30)
            assert p.returncode==0,p.stderr
            (f.root/'native_backend.py').write_text(NATIVE_BACKEND)
            f.target['sha256']=sha(f.root/'stock.bin');f.target['segments'][0]['size']=(f.root/'stock.bin').stat().st_size
            f.target['architecture']='native synthetic executable'
            f.target['analysis_configuration']={'tool':'native GCC pilot','version':'actual executable hash pinned','settings':{}}
            f.unit.update(target_sha256=f.target['sha256'],size=f.target['segments'][0]['size'],isa_mode='native')
            f.config['units']['U1']['symbol']='main'
            f.config['profile']['execution_kind']='process-image'
            f.config['tools']['compiler']={'argv':[compiler,'-std=c99','-O0','{source}','-o','{output}'],
                'preprocess_argv':[compiler,'-std=c99','-E','-P','{source}','-o','{output}'],
                'executable_sha256':sha(compiler),'files':{}}
            f.config['tools']['executor']={'argv':[sys.executable,'native_backend.py','{stock}','{image}','{witnesses}',
                '{report}','{unit}','{entry}','{run}'],'executable_sha256':sha(sys.executable),
                'files':{'native_backend.py':sha(f.root/'native_backend.py')}}
        (f.root/'src/U1.c').write_text(good_source);(f.root/'negative/U1.c').write_text(bad_source)
        f.write('target.json',f.target);f.write('units/U1.json',f.unit)
        f.universe['units'][0]['identity']=profile().manifest_digest(profile().validate_unit(f.root,f.target,f.unit)['identity'])
        f.write('universe.json',f.universe)
        f.config.update(target=f.ref('target.json'),universe=f.ref('universe.json'))
        f.review['source_sha256']=sha(f.root/'src/U1.c');f.write('reviews/U1.json',f.review);f.save()
        f.write('grades.json',{'format':'decompile-grades-v1','grades':{'U1':'G4-recon'}})
        script=SKILL/'scripts/completion.py'
        protected={'config.json':sha(f.root/'config.json'),'tool.py':sha(f.root/'tool.py')}
        if compiler:protected['native_backend.py']=sha(f.root/'native_backend.py')
        policy={'schema':1,'universe':f.ref('universe.json'),'criterion':'M','output_pattern':'measurements/{run}.json',
            'required_gates':['representation','compilation','behavior','independence','controls'],
            'protected_files':protected,'input_patterns':['src/*.c','negative/*.c','reviews/*.json','witnesses/*.json',
             'units/*.json','config.json','target.json','callgraph.json','universe.json','stock.bin'],
            'acceptance_minimum':1,'pinned_roles':['witnesses','negative_source','verifier_context'],
            'audit':{'criterion':'A','output_pattern':'audits/{run}.json','every_cycles':3,'sample_size':1}}
        mission={'objective':'Qualify one synthetic reconstruction without inflating its completion',
            'mode':'light','in_scope':['one synthetic unit'],'out_of_scope':['real firmware','universal equivalence'],
            'criteria':[{'id':cid,'description':'evidence-qualified count' if cid=='M' else 'independent recount/audit',
                'argv':[sys.executable,str(script),'--project',str(f.root),'--config','config.json'],
                'artifacts':list(protected)} for cid in ('M','A')],
            'measurement_policy':policy,'budget':{'max_cycles':10,'max_cycle_seconds':600,'max_check_seconds':120,
             'max_no_progress':10,'max_same_failures':10,'consolidate_every':10}}
        f.h=h.Harness(f.root);f.h.init(mission)
        def start(criteria=None):
            review=f.h.review('completion')
            return f.h.start({'topic':'completion','task':'qualify unit','premise':'actual reconstruction evidence',
                'residual':'test current source','review_id':review['review']['id'],'reviewed_claims':list(review['claims']),
                'criteria':criteria or ['M'],'approach':{'method':'bounded native verifier','inputs':'current source','environment':'synthetic pilot'},
                'reverify_reason':'Revalidate actual source under the approved profile'})['cycle']
        def close(cycle):return f.h.close(cycle,'verified','Retain only currently qualified evidence')
        first=start();check=f.h.check(first,'M');assert check['passed'],check
        pending=f.h.measurement_report();assert pending['counts']['verified']==0
        close(first);assert f.h.measurement_report()['counts']['verified']==1
        (f.root/'src/U1.c').write_text(bad_source)
        stale=f.h.measurement_report();assert stale['counts']['stale']==1 and stale['counts']['verified']==0
        command=[sys.executable,'-B',str(SKILL/'scripts/census_bars.py'),'--project',str(f.root),
            '--callgraph','callgraph.json','--grades','grades.json','--harness',str(Path(harness).resolve()),'--json']
        shown=subprocess.run(command,capture_output=True,text=True,timeout=30)
        assert shown.returncode==0,shown.stdout+shown.stderr
        view=json.loads(shown.stdout)['result'];assert view['counts']['stale']==1
        f.review['source_sha256']=sha(f.root/'src/U1.c');f.write('reviews/U1.json',f.review)
        second=start();wrong=f.h.check(second,'M');assert wrong['passed'],wrong
        assert wrong['measurement']['verified_count']==0
        close(second);assert f.h.measurement_report()['counts']['verified']==0
        (f.root/'src/U1.c').write_text(good_source)
        f.review['source_sha256']=sha(f.root/'src/U1.c');f.write('reviews/U1.json',f.review)
        third=start(['M','A']);fixed=f.h.check(third,'M');assert fixed['passed'],fixed
        plan=f.h.measurement_audit_plan(third);assert plan['units']==['U1']
        audit=f.h.check(third,'A');assert audit['passed'],audit
        close(third);final=f.h.measurement_report()
        assert final['counts']['verified']==1 and f.h.validate()['passed'] and f.h.accept_mission()['accepted']
        with f.h.state() as state:assert state['cycles'][-1]['measurement_progress']['new_unit_ids']==[]
        return {'passed':True,'real_compiler_used':bool(compiler),'actual_process_image_execution':bool(compiler),
            'active_check_not_counted':True,'source_drift_invalidated':True,'bad_reconstruction_not_counted':True,
            'live_bars_preserved_stale_status':True,'audit_forced_reexecution':True,'repair_revalidation_not_new_work':True,
            'final_verified':1,'firmware_or_universal_semantics_verified':False,'installed':False,'published':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--harness',required=True)
    parser.add_argument('--compiler',help='Explicit native C compiler for the real synthetic pilot')
    args=parser.parse_args();print(json.dumps(run(args.harness,args.compiler),indent=2))
