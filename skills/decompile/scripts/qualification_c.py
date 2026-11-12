"""Adapt the existing finite C verifier; no second compiler, emulator or mission ledger."""
import importlib.util
from pathlib import Path

def sibling(name):
    spec=importlib.util.spec_from_file_location('qualification_c_'+name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

legacy=sibling('completion');contract=sibling('qualification_contract')

class CBackend(legacy.Verifier):
    def __init__(self,owner):
        self.owner=owner
        contract.need(owner.contract['category']=='independent-validated',
                      'The compatibility C backend qualifies independent reconstruction; use an approved category-specific external verifier for other categories')
        super().__init__(owner.root,owner.contract['backend']['config']['path'],owner.run_id,owner.command_context)
        self.deadline=min(self.deadline,owner.deadline)
        contract.need(self.config['target']==owner.contract['target'] and self.config['universe']==owner.contract['universe'] and
                      self.graph_ref==owner.graph_ref,'Backend target/universe/graph differs from the generic contract')
        p=owner.profile
        contract.need(self.config['profile']['execution_kind']==p['validation']['execution_kind'] and
                      set(self.config['profile']['reviewers'])==set(p['reviewers']) and
                      self.config['profile']['allowed_external_calls']==p['dependencies']['allowed_external_calls'] and
                      self.config['profile']['platform_images']==p['dependencies']['platform_images'],
                      'Backend source/execution/platform boundary differs from the pinned target profile')
        contract.need(not (set(self.symbols)&set(p['dependencies']['allowed_external_calls'])),
                      'An inventoried callee cannot be reclassified as an external service')
        contract.need(self.config['units'].keys()==owner.live,'Backend and generic live universe differ')
        for uid,row in self.config['units'].items():
            contract.need(row['unit_manifest']==owner.contract['unit_manifests'][uid],
                          'Backend unit manifest differs from the fixed physical identity')

    def input_state(self,uid):
        state=super().input_state(uid)
        state['refs'].update(self.owner.bindings(uid))
        state['signature']=contract.digest({'legacy_signature':state['signature'],'generic_refs':state['refs']})
        contract.check_witnesses(state['corpus'],self.owner.profile)
        return state

    def execution_result(self,uid,state,image_ref,path,run):
        result=super().execution_result(uid,state,image_ref,path,run)
        packet=legacy.closure.load_json(path)
        required=set(self.owner.profile['validation']['observables'])-{'termination'}
        for case in packet['cases']:
            for role in ('stock','candidate'):
                observed=case[role]
                available=set(observed) if isinstance(observed,dict) else {'return'}
                contract.need(required<=available,'A required semantic observable is absent; matching another value cannot compensate')
        return result

    def assess_receipt(self,uid,state,receipt):
        gates,analysis=super().assess_receipt(uid,state,receipt)
        for role in ('compiled_image','negative_image'):
            contract.check_image(self.bound(receipt['artifacts'][role]).read_bytes(),self.owner.profile)
        return gates,analysis

    def observe(self,uid,previous=None,force=False):
        row=self.unit(uid,previous,force)
        gates=row['gates']
        mapped={'D-a':gates['representation'],'D-b':gates['representation'],'D-c':gates['independence'],
                'D-d':gates['representation'],'D-e':gates['compilation'],
                'D-f':contract.combine(gates['behavior'],gates['controls'])}
        ref=row['artifacts'].get('completion_receipt');executed=False
        if ref:executed=legacy.closure.load_json(self.bound(ref))['run_id']==self.run_id
        return {'criteria':mapped,'artifacts':row['artifacts'],'executed':executed,
                'healthy_passed':gates['controls']=='pass','known_bad_rejected':gates['controls']=='pass'}
