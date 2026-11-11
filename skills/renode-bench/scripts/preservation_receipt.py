"""Optional finite witness export; no harness dependency, promotion or emulator dispatch."""
import hashlib
import json
from pathlib import Path
import re


def encoded(value):
    return json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode()


class Recorder:
    def __init__(self, config, cases):
        required={'project','output','unit','run_id','context_sha256','references','reset','reset_policy'}
        if not isinstance(config,dict) or set(config)!=required: raise ValueError('Use the exact preservation context')
        self.config=config; self.root=Path(config['project']).resolve(strict=True)
        if not callable(config['reset']) or not config['reset_policy'].strip(): raise ValueError('Explicit reset callable/policy required')
        if not all(isinstance(config[k],str) and config[k].strip() for k in ('unit','run_id','context_sha256')):
            raise ValueError('Unit and current run/context required')
        if not re.fullmatch('[a-f0-9]{64}',config['context_sha256']): raise ValueError('Invalid context hash')
        self.output=self.path(config['output'],exists=False)
        if self.output.exists(): raise ValueError('Never overwrite a witness result')
        if not isinstance(config['references'],dict) or not {'stock','witnesses'}<=set(config['references']):
            raise ValueError('Stock image and original witness corpus must be physically bound')
        self.check_references()
        names=[case.get('name') for case in cases]
        if not all(isinstance(x,str) and x.strip() for x in names) or len(set(names))!=len(names):
            raise ValueError('Each witness needs a unique stable name')
        corpus=json.loads(self.path(config['references']['witnesses']['path']).read_text(encoding='utf-8'))
        if encoded(corpus)!=encoded(cases): raise ValueError('In-memory witnesses differ from the bound corpus')
        self.cases=cases

    def path(self,relative,exists=True):
        if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('Use paths inside the authorized project')
        path=(self.root/relative).resolve(strict=exists)
        if not path.is_relative_to(self.root) or '.harness' in path.relative_to(self.root).parts:
            raise ValueError('Evidence/output path leaves the project or enters the store')
        if exists and not path.is_file(): raise ValueError('A physical reference file is required')
        return path

    def check_references(self):
        for ref in self.config['references'].values():
            if not isinstance(ref,dict) or set(ref)!={'path','sha256'}: raise ValueError('Reference requires path and SHA-256')
            if hashlib.sha256(self.path(ref['path']).read_bytes()).hexdigest()!=ref['sha256']:
                raise ValueError('Stock, corpus or executor reference changed')

    def reset(self):
        self.check_references()
        self.config['reset']()

    def finish(self,rows):
        self.check_references()
        output=[]
        for case, (name,got,expected,match) in zip(self.cases,rows):
            output.append({'id':self.config['unit']+'::'+name,'status':'pass' if match else 'fail',
                           'raw_status':'differential:witness-match' if match else 'differential:witness-mismatch',
                           'observed':got,'contract':{'references':self.config['references'],
                           'witness_sha256':hashlib.sha256(encoded(case)).hexdigest(),
                           'reset_policy':self.config['reset_policy']}})
        document={'format':'verimission-results-v1','run_id':self.config['run_id'],
                  'context_sha256':self.config['context_sha256'],'complete':len(rows)==len(self.cases),'cases':output}
        raw=encoded(document)
        with self.output.open('xb') as stream: stream.write(raw)
