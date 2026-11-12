"""Synthetic target profiles only; no real firmware/toolchain correctness claim."""
from completion_fixture import Fixture,load,sha
from test_qualification_contract import target_profile

class QualificationFixture(Fixture):
    def __enter__(self):
        super().__enter__()
        self.qprofile=target_profile();self.write('profile.json',self.qprofile)
        self.qreview={'format':'decompile-recovery-review-v1','unit':'U1','source_sha256':sha(self.root/'src/U1.c'),
            'category':'independent-validated','representation':'structured','reviewer':'independent-review-fixture',
            'body_complete':True,'unresolved_operations':[],'dependencies_complete':True,'dependencies':[],
            'marker_justifications':{}}
        self.write('reviews/U1.recovery.json',self.qreview)
        self.contract={'format':'decompile-qualification-contract-v1','id':'synthetic-mission',
            'category':'independent-validated','profile':self.ref('profile.json'),'target':self.ref('target.json'),
            'universe':self.ref('universe.json'),'callgraph':'callgraph.json',
            'backend':{'kind':'c-source-v1','config':self.ref('config.json')},
            'reviews':{'U1':'reviews/U1.recovery.json'},'unit_manifests':{'U1':'units/U1.json'},
            'input_patterns':['src/*.c','reviews/*.json','witnesses/*.json','negative/*.c','units/*.json',
                              'tool.py','target.json','universe.json','callgraph.json','profile.json','config.json','contract.json'],
            'budget_seconds':120,'work_pattern':'qualification/{run}'}
        self.save_contract();return self
    def save_contract(self):self.write('contract.json',self.contract)
    def save_profile(self):
        self.write('profile.json',self.qprofile);self.contract['profile']=self.ref('profile.json');self.save_contract()
    def save_backend(self):
        self.save();self.contract['backend']['config']=self.ref('config.json');self.save_contract()
    def qmeasure(self,previous=None,run='qualification-run'):
        return load('qualification').measure(self.root,'contract.json',run,'a'*64,previous)

