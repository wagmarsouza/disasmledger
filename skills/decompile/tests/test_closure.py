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
    return {'format': 'decompile-callgraph-v1', 'inventory_complete': True, 'graph': mapping}


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
            'fn_bind': 'G4-recon', 'fn_getA': 'G3', 'fn_leafP': 'G4-recon', 'fn_leafQ': 'G4-recon',
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
        result = closure.build_report(g, grades({'fn_leaf': 'G4-recon'}))
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


class RegressionTests(unittest.TestCase):
    def report(self, mapping, grading, **extra):
        data = graph(mapping)
        data.update(inventory_complete=True, **extra)
        return closure.build_report(data, grades(grading))

    def test_stock_observation_does_not_close_reconstruction_dependency(self):
        r = self.report({'caller': ['helper'], 'helper': []},
                        {'caller': 'G2', 'helper': 'G4-stock'})
        self.assertNotIn('caller', r['testable_now'])
        self.assertEqual(r['totals']['done_g3_plus'], 0)
        self.assertEqual(r['totals']['stock_g4'], 1)

    def test_reconstructed_witness_closes_dependency_but_is_not_verified_here(self):
        r = self.report({'caller': ['helper'], 'helper': []},
                        {'caller': 'G2', 'helper': 'G4-recon'})
        self.assertIn('caller', r['testable_now'])
        self.assertEqual(r['totals']['recon_g4'], 1)
        self.assertFalse(r['evidence_verified'])
        self.assertFalse(r['semantic_truth_verified'])

    def test_legacy_g4_is_flagged_and_does_not_prove_reconstruction(self):
        r = self.report({'caller': ['helper'], 'helper': []},
                        {'caller': 'G1', 'helper': 'G4'})
        self.assertNotIn('caller', r['testable_now'])
        self.assertEqual(r['legacy_g4_ambiguous'], ['helper'])
        self.assertTrue(r['coverage_indeterminate'])

    def test_g0_excluded_from_live_denominator_and_queue(self):
        r = self.report({'invalid': [], 'real': []}, {'invalid': 'G0', 'real': 'G1'})
        self.assertEqual(r['totals']['nodes'], 1)
        self.assertEqual(r['totals']['excluded_g0'], 1)
        self.assertEqual(r['totals']['graded'], 1)
        self.assertEqual(r['testable_now'], ['real'])

    def test_reference_to_g0_blocks_caller(self):
        r = self.report({'caller': ['invalid'], 'invalid': []},
                        {'caller': 'G1', 'invalid': 'G0'})
        self.assertNotIn('caller', r['testable_now'])

    def test_orphan_grade_rejected(self):
        with self.assertRaises(closure.ClosureError) as caught:
            self.report({'real': []}, {'real': 'G1', 'outside': 'G3'})
        self.assertEqual(caught.exception.code, 'GRADES')

    def test_missing_adjacency_blocks_even_graded_callee(self):
        r = self.report({'caller': ['helper']}, {'caller': 'G1', 'helper': 'G3'})
        self.assertNotIn('caller', r['testable_now'])
        self.assertTrue(r['coverage_indeterminate'])
        self.assertEqual(r['unknown_dependencies'], ['helper'])

    def test_explicit_unknown_adjacency_blocks(self):
        r = self.report({'caller': ['helper'], 'helper': None},
                        {'caller': 'G1', 'helper': 'G3'})
        self.assertNotIn('caller', r['testable_now'])

    def test_unresolved_indirect_calls_propagate_to_callers(self):
        r = self.report({'caller': ['dispatch'], 'dispatch': []},
                        {'caller': 'G1', 'dispatch': 'G3'}, unknown_calls=['dispatch'])
        self.assertNotIn('caller', r['testable_now'])
        self.assertTrue(r['coverage_indeterminate'])

    def test_unspecified_inventory_is_indeterminate(self):
        data = graph({'leaf': []})
        del data['inventory_complete']
        r = closure.build_report(data, grades({'leaf': 'G3'}))
        self.assertTrue(r['coverage_indeterminate'])

    def test_cycles_remain_unresolved_even_with_declared_recon_grades(self):
        r = self.report({'a': ['b'], 'b': ['a']}, {'a': 'G4-recon', 'b': 'G4-recon'})
        self.assertEqual(r['ft_g4_closed'], 0)

    def test_duplicate_edges_do_not_change_closure_or_leverage(self):
        r = self.report({'a': ['b', 'b'], 'b': []}, {'a': 'G1', 'b': 'G3'})
        self.assertIn('a', r['testable_now'])

    def test_discarded_only_inventory_is_not_applicable(self):
        r = self.report({'a': []}, {'a': 'G0'})
        self.assertFalse(r['coverage_applicable'])
        self.assertEqual(r['totals']['nodes'], 0)
        self.assertEqual(r['testable_now'], [])

    def test_invalid_completeness_and_unknown_call_metadata_rejected(self):
        for extra in ({'inventory_complete': 'yes'}, {'unknown_calls': ['outside']},
                      {'unknown_calls': 'a'}):
            data = graph({'a': []})
            data.update(extra)
            with self.assertRaises(closure.ClosureError):
                closure.build_report(data, grades({'a': 'G3'}))

    def test_deep_chain_is_supported_without_python_recursion(self):
        n = 2500
        g = {str(i): [str(i + 1)] for i in range(n - 1)}
        g[str(n - 1)] = []
        gr = {str(i): 'G3' for i in range(1, n)}
        gr['0'] = 'G1'
        self.assertIn('0', self.report(g, gr)['testable_now'])

    def test_malformed_grade_value_is_structurally_rejected(self):
        with self.assertRaises(closure.ClosureError):
            self.report({'leaf': []}, {'leaf': []})

    def test_limit_is_validated_for_library_call(self):
        with self.assertRaises(closure.ClosureError):
            closure.build_report(graph({'a': []}), grades({'a': 'G1'}), limit=-1)

    def test_retracted_callee_blocks_after_grade_downgrade(self):
        before = self.report({'a': ['b'], 'b': []}, {'a': 'G1', 'b': 'G4-recon'})
        after = self.report({'a': ['b'], 'b': []}, {'a': 'G1', 'b': 'G2'})
        self.assertIn('a', before['testable_now'])
        self.assertNotIn('a', after['testable_now'])

    def test_relative_cli_inputs_resolve_under_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'g.json').write_text(json.dumps(graph({'a': []})), encoding='utf-8')
            (root / 'r.json').write_text(json.dumps(grades({'a': 'G1'})), encoding='utf-8')
            run = subprocess.run([sys.executable, '-B', str(SCRIPT), '--project', str(root),
                                  'report', '--callgraph', 'g.json', '--grades', 'r.json'],
                                 cwd=SCRIPT.parent, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
