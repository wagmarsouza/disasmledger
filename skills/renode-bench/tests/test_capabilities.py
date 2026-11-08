import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/executor_capabilities.py'
spec = importlib.util.spec_from_file_location('executor_capabilities_test', SCRIPT)
caps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(caps)
DIFFERENTIAL = SCRIPT.with_name('differential.py')
other = importlib.util.spec_from_file_location('differential_caps_test', DIFFERENTIAL)
diff = importlib.util.module_from_spec(other)
other.loader.exec_module(diff)


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='disasm-capabilities-')
        self.root = Path(self.temp.name)
        self.target = b'synthetic image; not executable firmware'
        (self.root / 'target.dat').write_bytes(self.target)
        self.target_hash = hashlib.sha256(self.target).hexdigest()
        proof = b'synthetic capability fixture, not an emulator test'
        (self.root / 'capability.txt').write_bytes(proof)
        self.receipt = {'path': 'capability.txt', 'sha256': hashlib.sha256(proof).hexdigest()}
        self.manifest = {'format': 'bench-executor-capabilities-v1', 'target_sha256': self.target_hash,
                         'executor': {'name': 'Unicorn', 'version': 'fixture-only', 'cpu_model': 'declared-model',
                                      'configuration': {'vfp_enabled': True}},
                         'capabilities': {'cold-invoke': {'status': 'supported', 'reason': 'Synthetic support declaration', 'evidence': [self.receipt]},
                                          'vfp': {'status': 'supported', 'reason': 'Synthetic configured feature', 'evidence': [self.receipt]},
                                          'mmio': {'status': 'unknown', 'reason': 'Not tested', 'evidence': []}}}
        self.request = {'format': 'bench-requirements-v1', 'target': {'path': 'target.dat', 'sha256': self.target_hash},
                        'unit_id': 'synthetic-leaf', 'required_features': ['cold-invoke', 'vfp']}
        self.manifest['assessment_context_sha256'] = caps.context_digest(self.manifest)

    def tearDown(self):
        self.temp.cleanup()

    def assess(self, manifest=None, request=None):
        return caps.assess(self.root, manifest or self.manifest, request or self.request)

    def reject(self, code, call):
        with self.assertRaises(caps.CapabilityError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def context(self):
        return {'project': self.root, 'manifest': self.manifest, 'requirements': self.request}

    def run_diff(self, invoke, context=None):
        cases = [{'regs': {0: 1}, 'expect': {'reg0': 2}}, {'regs': {0: 2}, 'expect': {'reg0': 3}}]
        return diff.differential('fixture', cases, invoke, blob=b'fixture-only', print_report=False,
                                 executor_context=context or self.context())

    def test_configured_unicorn_vfp_is_eligible_without_brand_rules(self):
        result = self.assess()
        self.assertTrue(result['eligible'])
        self.assertFalse(result['runtime_capability_authenticated'])
        self.assertFalse(result['execution_authorized'])

    def test_renode_name_does_not_make_unknown_feature_supported(self):
        self.manifest['executor']['name'] = 'Renode'
        self.manifest['assessment_context_sha256'] = caps.context_digest(self.manifest)
        self.request['required_features'].append('mmio')
        result = self.assess()
        self.assertFalse(result['eligible'])
        self.assertEqual(result['unknown'], ['mmio'])
        self.assertFalse(result['automatic_fallback'])

    def test_unsupported_and_missing_features_have_distinct_reasons(self):
        self.manifest['capabilities']['vfp']['status'] = 'unsupported'
        self.request['required_features'].append('boot-state')
        result = self.assess()
        self.assertEqual(result['unsupported'], ['vfp'])
        self.assertEqual(result['unknown'], ['boot-state'])

    def test_changed_evidence_invalidates_assessment(self):
        (self.root / 'capability.txt').write_text('changed')
        self.reject('CAPABILITY_STALE', self.assess)

    def test_changed_target_or_wrong_target_binding_refused(self):
        self.manifest['target_sha256'] = '0' * 64
        self.manifest['assessment_context_sha256'] = caps.context_digest(self.manifest)
        self.reject('IDENTITY', self.assess)
        self.manifest['target_sha256'] = self.target_hash
        self.manifest['assessment_context_sha256'] = caps.context_digest(self.manifest)
        (self.root / 'target.dat').write_bytes(b'another image')
        self.reject('IDENTITY', self.assess)

    def test_configuration_and_version_change_fingerprint(self):
        before = self.assess()['manifest_sha256']
        self.manifest['executor']['configuration']['vfp_enabled'] = False
        self.reject('CAPABILITY_STALE', self.assess)
        self.manifest['assessment_context_sha256'] = caps.context_digest(self.manifest)
        self.assertNotEqual(before, self.assess()['manifest_sha256'])

    def test_supported_feature_needs_current_evidence(self):
        self.manifest['capabilities']['vfp']['evidence'] = []
        self.reject('CAPABILITY', self.assess)

    def test_unknown_cannot_be_truthy_boolean_support(self):
        self.manifest['capabilities']['vfp']['status'] = True
        self.reject('CAPABILITY', self.assess)

    def test_empty_or_duplicate_requirements_refused(self):
        for features in ([], ['cold-invoke', 'cold-invoke']):
            self.request['required_features'] = features
            self.reject('REQUIREMENTS', self.assess)

    def test_parent_escape_and_state_as_evidence_refused(self):
        for path in ('../proof.txt', '.harness/state.yaml', 'C:\\other\\proof.txt'):
            bad = copy.deepcopy(self.manifest)
            bad['capabilities']['vfp']['evidence'][0]['path'] = path
            self.reject('PATH', lambda: self.assess(bad))

    def test_contextual_differential_reuses_gate_and_preserves_bool(self):
        calls = []
        def invoke(**kwargs):
            calls.append(kwargs['regs'][0])
            return {'reg0': kwargs['regs'][0] + 1}
        self.assertIs(self.run_diff(invoke), True)
        self.assertEqual(calls, [1, 2])

    def test_unknown_capability_prevents_compile_and_invocation(self):
        self.request['required_features'].append('mmio')
        def forbidden(**_):
            self.fail('Ineligible context must not invoke the bench')
        with self.assertRaises(diff.DifferentialError) as caught:
            diff.differential('no-run', [{'expect': {'reg0': 1}}, {'expect': {'reg0': 2}}], forbidden,
                              cpp_src='not compiled', print_report=False, executor_context=self.context())
        self.assertEqual(caught.exception.code, 'CAPABILITY')

    def test_context_drift_during_run_cannot_return_a_success(self):
        def invoke(**kwargs):
            (self.root / 'capability.txt').write_text('changed during invocation')
            return {'reg0': kwargs['regs'][0] + 1}
        with self.assertRaises(diff.DifferentialError) as caught:
            self.run_diff(invoke)
        self.assertEqual(caught.exception.code, 'CAPABILITY_STALE')

    def test_cli_assessment_does_not_dispatch_an_executor(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))
        (self.root / 'request.json').write_text(json.dumps(self.request))
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        args = [sys.executable, '-B', str(SCRIPT), '--project', str(self.root), 'assess', '--manifest', 'manifest.json', '--requirements', 'request.json']
        run = subprocess.run(args, capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertTrue(json.loads(run.stdout)['result']['eligible'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_duplicate_json_keys_and_nonfinite_numbers_refused(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}'):
            path = self.root / 'bad.json'
            path.write_text(raw)
            self.reject('INPUT', lambda: caps.load_json(path))


if __name__ == '__main__':
    unittest.main()
