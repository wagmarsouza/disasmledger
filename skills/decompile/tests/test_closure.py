import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/closure.py'
spec = importlib.util.spec_from_file_location('closure_test', SCRIPT)
closure = importlib.util.module_from_spec(spec)
if SCRIPT.exists():
    spec.loader.exec_module(closure)


def graph(mapping):
    return {'format': 'decompile-callgraph-v1', 'graph': mapping}


def grades(mapping):
    return {'format': 'decompile-grades-v1', 'grades': mapping}


class ClosureTests(unittest.TestCase):
    def setUp(self):
        # Mirrors the shipped templates.
        self.graph = graph({
            'fn_bind': [], 'fn_getA': [], 'fn_leafP': [], 'fn_leafQ': [],
            'fn_undoneHelper': ['fn_leafQ'],
            'fn_recon1': ['fn_bind', 'fn_leafP'],
            'fn_recon2': ['fn_bind'],
            'fn_recon3': ['fn_undoneHelper'],
            'fn_big': ['fn_bind', 'fn_undoneHelper'],
        })
        self.grades = grades({
            'fn_bind': 'G4', 'fn_getA': 'G3', 'fn_leafP': 'G4', 'fn_leafQ': 'G4',
            'fn_undoneHelper': 'G2', 'fn_recon1': 'G1', 'fn_recon2': 'G2',
            'fn_recon3': 'G1', 'fn_big': 'G1',
        })

    def reject(self, code, call):
        with self.assertRaises(closure.ClosureError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_testable_now_requires_closed_callee_closure(self):
        result = closure.build_report(self.graph, self.grades)
        # recon1/recon2 have fully-done callees; undoneHelper's only callee (leafQ) is done.
        self.assertEqual(result['testable_now'], ['fn_recon1', 'fn_recon2', 'fn_undoneHelper'])
        # big and recon3 depend on undoneHelper (not done) -> not testable yet.
        self.assertNotIn('fn_big', result['testable_now'])
        self.assertNotIn('fn_recon3', result['testable_now'])

    def test_leverage_ranks_undone_helpers_by_undone_callers(self):
        result = closure.build_report(self.graph, self.grades)
        top = result['top_leverage'][0]
        self.assertEqual(top['id'], 'fn_undoneHelper')      # called by big and recon3
        self.assertEqual(top['undone_callers'], 2)
        self.assertTrue(top['closure_ready'])               # also testable now
        # fn_bind is high fan-in but DONE, so it is never a leverage target to reconstruct.
        self.assertNotIn('fn_bind', [row['id'] for row in result['top_leverage']])

    def test_closure_counts_and_totals(self):
        result = closure.build_report(self.graph, self.grades)
        self.assertEqual(result['ft_g3_closed'], 7)
        self.assertEqual(result['ft_g4_closed'], 7)
        self.assertEqual(result['totals']['done_g3_plus'], 4)
        self.assertEqual(result['totals']['undone'], 5)
        self.assertFalse(result['coverage_indeterminate'])

    def test_passed_never_implies_semantics_or_promotion(self):
        result = closure.build_report(self.graph, self.grades)
        self.assertTrue(result['passed'])
        self.assertFalse(result['semantic_truth_verified'])
        self.assertFalse(result['promotion_authorized'])

    def test_cycle_among_undone_units_is_not_closed_and_terminates(self):
        g = graph({'fn_a': ['fn_b'], 'fn_b': ['fn_a']})
        gr = grades({'fn_a': 'G1', 'fn_b': 'G2'})
        result = closure.build_report(g, gr)
        self.assertEqual(result['testable_now'], [])        # neither closure can be certified
        self.assertEqual(result['ft_g3_closed'], 0)

    def test_ungraded_callee_blocks_closure_and_flags_indeterminate(self):
        g = graph({'fn_root': ['fn_unknown']})
        gr = grades({'fn_root': 'G1'})                      # fn_unknown absent from grades
        result = closure.build_report(g, gr)
        self.assertTrue(result['coverage_indeterminate'])
        self.assertIn('fn_unknown', result['ungraded_sample'])
        self.assertNotIn('fn_root', result['testable_now'])  # depends on an ungraded callee

    def test_leaf_done_closure_is_g4_closed(self):
        g = graph({'fn_leaf': []})
        result = closure.build_report(g, grades({'fn_leaf': 'G4'}))
        self.assertEqual(result['ft_g4_closed'], 1)

    def test_rejects_wrong_formats_and_bad_grades(self):
        self.reject('GRAPH', lambda: closure.build_report({'format': 'x', 'graph': {}}, self.grades))
        self.reject('GRADES', lambda: closure.build_report(self.graph, {'format': 'y', 'grades': {}}))
        self.reject('GRADES', lambda: closure.build_report(self.graph, grades({'fn_bind': 'G9'})))
        self.reject('GRAPH', lambda: closure.build_report(graph({'fn_a': 'not-a-list'}), self.grades))

    def test_json_loader_refuses_duplicate_keys_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as tmp:
            dup = Path(tmp) / 'dup.json'
            dup.write_text('{"a":1,"a":2}', encoding='utf-8')
            self.reject('JSON', lambda: closure.load_json(dup))
            nan = Path(tmp) / 'nan.json'
            nan.write_text('{"x":NaN}', encoding='utf-8')
            self.reject('JSON', lambda: closure.load_json(nan))

    def test_cli_is_read_only_and_reports(self):
        with tempfile.TemporaryDirectory(prefix='decompile-closure-') as tmp:
            root = Path(tmp)
            (root / 'callgraph.json').write_text(json.dumps(self.graph), encoding='utf-8')
            (root / 'grades.json').write_text(json.dumps(self.grades), encoding='utf-8')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            run = subprocess.run(
                [sys.executable, '-B', str(SCRIPT), '--project', str(root),
                 'report', '--callgraph', str(root / 'callgraph.json'), '--grades', str(root / 'grades.json')],
                capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            payload = json.loads(run.stdout)
            self.assertTrue(payload['ok'])
            self.assertEqual(payload['result']['top_leverage'][0]['id'], 'fn_undoneHelper')
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
