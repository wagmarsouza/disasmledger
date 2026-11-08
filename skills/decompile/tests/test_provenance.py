import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/closure.py'
spec = importlib.util.spec_from_file_location('closure_provenance', SCRIPT)
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='disasm-provenance-')
        self.root = Path(self.temp.name)
        self.graph = {'format': 'decompile-callgraph-v1', 'inventory_complete': True,
                      'graph': {'caller': ['leaf'], 'leaf': []}, 'unknown_calls': ['caller']}
        self.grades = {'format': 'decompile-grades-v1', 'grades': {'caller': 'G2', 'leaf': 'G3'}}
        self.refs = {'target': self.write('target.dat', b'synthetic target'),
                     'callgraph': self.write('graph.json', json.dumps(self.graph).encode()),
                     'grades': self.write('grades.json', json.dumps(self.grades).encode())}
        proof = self.write('edge.txt', b'declared analysis receipt, not an actual firmware trace')
        self.provenance = {'format': 'decompile-provenance-v1', **self.refs,
                           'producer': {'name': 'fixture-exporter', 'version': 'test-only', 'settings': {'base': 4096}},
                           'edges': [{'caller': 'caller', 'callee': 'leaf', 'basis': 'inferred', 'evidence': [proof]}]}
        self.provenance['export_context_sha256'] = closure.export_context(self.provenance)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, raw):
        (self.root / name).write_bytes(raw)
        return {'path': name, 'sha256': hashlib.sha256(raw).hexdigest()}

    def report(self, provenance=None):
        return closure.bound_report(self.root, 'graph.json', 'grades.json', provenance or self.provenance)

    def reject(self, code, operation):
        with self.assertRaises(closure.ClosureError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_bound_report_keeps_unknown_edges_and_grade_ceiling(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = self.report()
        self.assertEqual(result['unknown_dependencies'], ['caller'])
        self.assertEqual(result['testable_now'], [])
        self.assertFalse(result['evidence_verified'])
        self.assertFalse(result['promotion_authorized'])
        self.assertEqual(result['provenance']['edge_basis_counts'], {'inferred': 1, 'resolved': 0, 'observed': 0})
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_changed_target_invalidates_cached_export_binding(self):
        (self.root / 'target.dat').write_bytes(b'new target')
        self.reject('PROVENANCE_STALE', self.report)

    def test_changed_graph_or_grades_or_edge_evidence_refused(self):
        for field in ('callgraph', 'grades'):
            old = (self.root / self.refs[field]['path']).read_bytes()
            (self.root / self.refs[field]['path']).write_bytes(old + b' ')
            self.reject('PROVENANCE_STALE', self.report)
            (self.root / self.refs[field]['path']).write_bytes(old)
        (self.root / 'edge.txt').write_text('changed receipt')
        self.reject('PROVENANCE_STALE', self.report)

    def test_wrong_cli_graph_cannot_borrow_another_binding(self):
        self.write('other.json', json.dumps(self.graph).encode())
        self.reject('PROVENANCE', lambda: closure.bound_report(self.root, 'other.json', 'grades.json', self.provenance))

    def test_producer_version_and_settings_are_part_of_fingerprint(self):
        before = self.report()['provenance']['manifest_sha256']
        self.provenance['producer']['settings']['base'] = 8192
        self.reject('PROVENANCE_STALE', self.report)
        # An explicit new declaration changes the receipt identity; it is not proof of a new export.
        self.provenance['export_context_sha256'] = closure.export_context(self.provenance)
        after = self.report()['provenance']['manifest_sha256']
        self.assertNotEqual(before, after)

    def test_unknown_edge_origin_cannot_be_silently_upgraded(self):
        self.provenance['edges'][0]['basis'] = 'proven'
        self.reject('PROVENANCE', self.report)

    def test_observed_edge_is_still_not_runtime_authentication(self):
        self.provenance['edges'][0]['basis'] = 'observed'
        result = self.report()
        self.assertEqual(result['provenance']['edge_basis_counts']['observed'], 1)
        self.assertFalse(result['provenance']['runtime_edges_authenticated'])
        self.assertEqual(result['unknown_dependencies'], ['caller'])

    def test_annotations_must_refer_to_real_graph_edges(self):
        self.provenance['edges'][0]['callee'] = 'not-in-graph'
        self.reject('PROVENANCE', self.report)

    def test_annotation_coverage_is_explicit_not_assumed(self):
        self.provenance['edges'] = []
        result = self.report()['provenance']
        self.assertEqual(result['edge_annotation_coverage'], {'annotated': 0, 'total': 1})

    def test_evidence_path_escape_and_harness_store_refused(self):
        for path in ('../outside.txt', '.harness/state.yaml', 'C:\\other\\evidence.txt'):
            bad = copy.deepcopy(self.provenance)
            bad['edges'][0]['evidence'][0]['path'] = path
            self.reject('PATH', lambda: self.report(bad))

    def test_duplicate_annotations_refused(self):
        self.provenance['edges'].append(copy.deepcopy(self.provenance['edges'][0]))
        self.reject('PROVENANCE', self.report)

    def test_missing_evidence_cannot_support_declared_origin(self):
        self.provenance['edges'][0]['evidence'] = []
        self.reject('PROVENANCE', self.report)

    def test_opt_in_cli_and_old_cli_both_work(self):
        (self.root / 'provenance.json').write_text(json.dumps(self.provenance))
        args = [sys.executable, '-B', str(SCRIPT), '--project', str(self.root), 'report',
                '--callgraph', 'graph.json', '--grades', 'grades.json']
        old = subprocess.run(args, capture_output=True, text=True, timeout=10)
        new = subprocess.run(args + ['--provenance', 'provenance.json'], capture_output=True, text=True, timeout=10)
        self.assertEqual(old.returncode, 0, old.stdout)
        self.assertNotIn('provenance', json.loads(old.stdout)['result'])
        self.assertEqual(new.returncode, 0, new.stdout)
        self.assertTrue(json.loads(new.stdout)['result']['provenance']['physical_hashes_match'])


if __name__ == '__main__':
    unittest.main()
