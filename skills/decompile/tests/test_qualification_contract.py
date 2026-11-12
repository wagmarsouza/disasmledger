"""Generic criteria remain strict when target-specific details change."""
import copy
import importlib.util
from pathlib import Path
import unittest

def module():
    path=Path(__file__).resolve().parents[1]/'scripts/qualification_contract.py'
    spec=importlib.util.spec_from_file_location('generic_contract_test',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def target_profile():
    return {'format':'decompile-target-profile-v1','id':'synthetic-c-protocol',
        'target':{'architectures':['synthetic-protocol'],'endianness':'little','address_unit_bytes':1,'isa_modes':['synthetic']},
        'language':'c','backend':'c-source-v1','reviewers':['independent-review-fixture'],
        'dependencies':{'allowed_external_calls':[],'platform_images':{}},
        'build':{'format':'synthetic','bits':None,'machine':None},
        'validation':{'method':'differential','execution_kind':'pc-trace','min_cases':2,
                      'observables':['return','termination'],'required_scenarios':[],'assumptions':[]},
        'stub_markers':['halt_baddata','Could not recover']}

class QualificationContractTests(unittest.TestCase):
    def setUp(self):self.m=module()
    def test_fixed_categories_do_not_relax_the_reconstructed_counter(self):
        for category in self.m.CATEGORIES:
            statuses={k:('pass' if k in self.m.REQUIRED[category] else 'not-applicable') for k in self.m.CRITERIA}
            result=self.m.verdict(category,statuses)
            self.assertTrue(result['category_satisfied'])
            self.assertEqual(result['reconstructed_eligible'],category=='independent-validated')
    def test_one_failure_or_na_cannot_be_compensated_by_other_passes(self):
        for key in ('D-c','D-e','D-f'):
            for status in ('fail','unknown','not-applicable'):
                gates={k:'pass' for k in self.m.CRITERIA};gates[key]=status
                with self.subTest(key=key,status=status):
                    result=self.m.verdict('independent-validated',gates)
                    self.assertFalse(result['reconstructed_eligible']);self.assertFalse(result['category_satisfied'])
    def test_profile_is_target_specific_but_has_no_fixed_path_or_compiler_name(self):
        p=target_profile();self.assertEqual(self.m.validate_profile(p)['id'],p['id'])
        p['id']='arm-thumb';p['target'].update(architectures=['ARMv7E-M'],isa_modes=['thumb'])
        p['build']={'format':'elf','bits':32,'machine':40}
        self.m.validate_profile(p)
    def test_duplicate_or_ambiguous_profile_settings_are_refused(self):
        for field,value in [('reviewers',[]),('backend','guess'),('language',''),('extra',True)]:
            p=target_profile();p[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.m.validate_profile(p)
        p=target_profile();p['target']['architectures'].append('synthetic-protocol')
        with self.assertRaises(ValueError):self.m.validate_profile(p)
    def test_zero_tests_cannot_be_differential_validation(self):
        p=target_profile();p['validation']['min_cases']=0
        with self.assertRaises(ValueError):self.m.validate_profile(p)
    def test_no_arbitrary_50_or_60_vector_universal_threshold(self):
        for cases in (2,7,60,256):
            p=target_profile();p['validation']['min_cases']=cases;self.m.validate_profile(p)
    def test_formal_profile_needs_external_verifier_not_a_c_rename(self):
        p=target_profile();p['validation'].update(method='formal-equivalence',execution_kind='adapter',min_cases=0)
        with self.assertRaises(ValueError):self.m.validate_profile(p)
        p.update(language='llvm-ir',backend='external-v1');p['build']['format']='adapter-validated'
        self.m.validate_profile(p)
    def test_target_mismatch_cannot_silently_choose_a_weaker_profile(self):
        p=target_profile();target={'architecture':'ARM','endianness':'little','address_unit_bytes':1}
        with self.assertRaises(ValueError):self.m.match_target(p,target,['thumb'])
    def test_valid_elf_build_does_not_accept_another_architecture(self):
        p=target_profile();p['build']={'format':'elf','bits':64,'machine':62}
        image=bytearray(64);image[:6]=b'\x7fELF\x02\x01';image[18:20]=(62).to_bytes(2,'little')
        self.m.check_image(bytes(image),p)
        image[18:20]=(40).to_bytes(2,'little')
        with self.assertRaises(ValueError):self.m.check_image(bytes(image),p)
    def test_same_input_relabelled_as_multiple_witnesses_does_not_pass(self):
        p=target_profile();corpus={'cases':[{'id':'a','input':0},{'id':'b','input':0}]}
        with self.assertRaises(ValueError):self.m.check_witnesses(corpus,p)
    def test_input_scenarios_are_obligations_not_claimed_branch_coverage(self):
        p=target_profile();p['validation']['required_scenarios']=['boundary','normal']
        corpus={'cases':[{'id':'a','input':0,'scenario':'normal'},{'id':'b','input':1,'scenario':'normal'}]}
        with self.assertRaises(ValueError):self.m.check_witnesses(corpus,p)
        corpus['cases'][1]['scenario']='boundary';self.m.check_witnesses(corpus,p)
    def test_legitimate_data_address_goto_or_linear_source_is_not_a_universal_ban(self):
        p=target_profile();self.assertNotIn('goto',p['stub_markers']);self.m.validate_profile(p)

if __name__=='__main__':unittest.main()
