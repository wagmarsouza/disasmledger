"""Tool-neutral D-a..D-f contracts. Categories never downgrade themselves to obtain a pass."""
import hashlib
import json

CRITERIA=('D-a','D-b','D-c','D-d','D-e','D-f')
CATEGORIES=('analysis','mechanical-translation','recompilable','independent-validated')
REQUIRED={
    'analysis':{'D-a','D-b','D-d'},
    'mechanical-translation':{'D-a','D-b','D-d','D-e'},
    'recompilable':{'D-a','D-b','D-d','D-e'},
    'independent-validated':set(CRITERIA)}
STATUSES={'pass','fail','unknown','not-applicable'}

class ProtocolError(ValueError):
    """Malformed whole observations cannot be concealed as a valid zero-count measurement."""

def need(condition,message):
    if not condition:raise ValueError(message)
def text(value):return isinstance(value,str) and bool(value.strip())
def encoded(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def names(value,empty=False):
    return isinstance(value,list) and (empty or bool(value)) and all(text(v) for v in value) and len(set(value))==len(value)
def reference(value):
    need(isinstance(value,dict) and set(value)=={'path','sha256'} and text(value['path']) and
         isinstance(value['sha256'],str) and len(value['sha256'])==64 and
         all(c in '0123456789abcdef' for c in value['sha256']),'A physical path/SHA256 reference is required')

def verdict(category,criteria):
    need(category in CATEGORIES,'Declare the category before evaluation; no automatic fallback')
    need(isinstance(criteria,dict) and set(criteria)==set(CRITERIA) and all(v in STATUSES for v in criteria.values()),
         'Every generic criterion needs an explicit, non-compensating status')
    satisfied=all(criteria[k]=='pass' for k in REQUIRED[category])
    return {'category':category,'category_satisfied':satisfied,
            'reconstructed_eligible':category=='independent-validated' and satisfied,
            'automatic_reclassification':False}

def neutral_gates(category,criteria):
    value=verdict(category,criteria)
    gates={k:('unknown' if s=='not-applicable' else s) for k,s in criteria.items()}
    if not value['reconstructed_eligible'] and all(s=='pass' for s in gates.values()):gates['D-f']='unknown'
    return gates

def validate_profile(value):
    fields={'format','id','target','language','backend','reviewers','dependencies','build','validation','stub_markers'}
    need(isinstance(value,dict) and set(value)==fields and value['format']=='decompile-target-profile-v1',
         'Use the exact target profile schema; unknown fields cannot relax a gate')
    need(text(value['id']) and text(value['language']) and value['backend'] in ('c-source-v1','external-v1'),
         'Declare profile identity, language and supported backend')
    t=value['target']
    need(isinstance(t,dict) and set(t)=={'architectures','endianness','address_unit_bytes','isa_modes'} and
         names(t['architectures']) and names(t['isa_modes']) and t['endianness'] in ('little','big','mixed') and
         type(t['address_unit_bytes']) is int and t['address_unit_bytes']>0,'Explicit, unambiguous target constraints required')
    need(names(value['reviewers']) and names(value['stub_markers'],True),'Approved reviewer names and explicit marker policy required')
    d=value['dependencies']
    need(isinstance(d,dict) and set(d)=={'allowed_external_calls','platform_images'} and
         names(d['allowed_external_calls'],True) and isinstance(d['platform_images'],dict),
         'Freeze the external/platform boundary before verification')
    for name,ref in d['platform_images'].items():need(text(name),'Name every platform image');reference(ref)
    b=value['build']
    need(isinstance(b,dict) and set(b)=={'format','bits','machine'} and b['format'] in ('elf','adapter-validated','synthetic'),
         'Declare target construction constraints')
    if b['format']=='elf':
        need(b['bits'] in (32,64) and type(b['bits']) is int and type(b['machine']) is int and b['machine']>0,
             'ELF profile needs exact class and machine')
    else:need(b['bits'] is None and b['machine'] is None,'Non-ELF format cannot claim an ELF machine check')
    v=value['validation']
    need(isinstance(v,dict) and set(v)=={'method','execution_kind','min_cases','observables','required_scenarios','assumptions'} and
         v['method'] in ('differential','symbolic-equivalence','formal-equivalence','none') and
         v['execution_kind'] in ('pc-trace','process-image','adapter') and type(v['min_cases']) is int and
         names(v['observables'],True) and names(v['required_scenarios'],True) and names(v['assumptions'],True),
         'Declare the actual validation method, assumptions and scope')
    if v['method']=='differential':
        need(v['min_cases']>=2 and names(v['observables']) and 'termination' in v['observables'],
             'Differential validation needs finite discriminating inputs and termination observations')
    else:
        need(v['min_cases']==0 and not v['required_scenarios'],'Non-differential methods do not claim a vector count')
        if v['method']!='none':need(names(v['observables']),'Equivalence over no observables is not behavioral validation')
    if value['backend']=='c-source-v1':
        need(value['language']=='c' and v['method']=='differential' and
             v['execution_kind'] in ('pc-trace','process-image') and b['format'] in ('elf','synthetic'),
             'The built-in C adapter cannot impersonate a C++/IR parser or formal prover')
    if v['method']=='none':need(not v['observables'],'Analytical-only profiles do not claim observed execution')
    return value

def match_target(profile,target,isa_modes):
    t=profile['target']
    need(target.get('architecture') in t['architectures'] and target.get('endianness')==t['endianness'] and
         target.get('address_unit_bytes')==t['address_unit_bytes'] and set(isa_modes)<=set(t['isa_modes']),
         'The target/ISA differs from the approved profile; do not choose another profile automatically')
    if profile['build']['format']=='synthetic':
        need(target.get('architecture')=='synthetic-protocol','Synthetic protocol image checks cannot qualify a real target')

def check_image(data,profile):
    b=profile['build']
    if b['format']=='synthetic':return
    need(b['format']=='elf','This build format requires an approved external verifier')
    need(len(data)>=20 and data[:4]==b'\x7fELF' and data[4] in (1,2) and data[5] in (1,2),'Expected an actual ELF header')
    endian='little' if data[5]==1 else 'big'
    need((32 if data[4]==1 else 64)==b['bits'] and endian==profile['target']['endianness'] and
         int.from_bytes(data[18:20],endian)==b['machine'],'Compiled image class/endianness/machine differs from target profile')

def check_witnesses(corpus,profile):
    cases=corpus.get('cases') if isinstance(corpus,dict) else None
    need(isinstance(cases,list) and len(cases)>=profile['validation']['min_cases'],'Required witness cases are missing')
    need(all(isinstance(c,dict) and text(c.get('id')) and 'input' in c for c in cases),'Witnesses need stable IDs and actual inputs')
    need(len({c['id'] for c in cases})==len(cases) and len({digest(c['input']) for c in cases})>=profile['validation']['min_cases'],
         'Renaming/duplicating the same input cannot inflate witness diversity')
    need(set(profile['validation']['required_scenarios'])<={c.get('scenario') for c in cases},
         'A profile input-scenario obligation was omitted; scenario labels do not prove branch coverage')
    return cases

def combine(*statuses):
    need(statuses and all(s in STATUSES for s in statuses),'Unknown criterion status')
    if 'fail' in statuses:return 'fail'
    if 'unknown' in statuses:return 'unknown'
    if 'not-applicable' in statuses:return 'not-applicable'
    return 'pass'
