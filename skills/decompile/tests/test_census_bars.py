import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/census_bars.py'
spec = importlib.util.spec_from_file_location('census_bars_test', SCRIPT)
bars = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bars)


class CensusBarsTests(unittest.TestCase):
    def setUp(self):
        self.graph = {'format': 'decompile-callgraph-v1', 'inventory_complete': True,
                      'graph': {key: [] for key in ('raw', 'model', 'compile', 'stock', 'recon', 'legacy', 'missing', 'excluded')}}
        self.grades = {'format': 'decompile-grades-v1', 'grades': {'raw': 'G1', 'model': 'G2', 'compile': 'G3',
                       'stock': 'G4-stock', 'recon': 'G4-recon', 'legacy': 'G4', 'excluded': 'G0'}}

    def view(self):
        return bars.summarize(self.graph, self.grades)

    def test_stock_and_recon_are_separate_nonoverlapping_rows(self):
        view = self.view()
        counts = {row['grade']: row['count'] for row in view['rows']}
        self.assertEqual(counts, {'G1': 1, 'G2': 1, 'G3': 1, 'G4-stock': 1, 'G4-recon': 1, 'G4-ambiguous': 1, 'ungraded': 1})
        self.assertEqual(sum(counts.values()), 7)
        self.assertEqual(view['declared_compiled_or_compared'], 2)

    def test_denominator_and_summary_reuse_existing_closure_totals(self):
        report = bars.closure.build_report(self.graph, self.grades)
        view = self.view()
        self.assertEqual(view['denominator'], report['totals']['nodes'])
        self.assertEqual(view['declared_compiled_or_compared'], report['totals']['done_g3_plus'])
        self.assertEqual(view['excluded_g0'], report['totals']['excluded_g0'])
        self.assertEqual(view['coverage_indeterminate'], report['coverage_indeterminate'])

    def test_stock_alone_does_not_count_as_reconstruction(self):
        graph = {'format': 'decompile-callgraph-v1', 'inventory_complete': True, 'graph': {'stock': []}}
        view = bars.summarize(graph, {'format': 'decompile-grades-v1', 'grades': {'stock': 'G4-stock'}})
        self.assertEqual(view['declared_compiled_or_compared'], 0)
        self.assertEqual(next(row for row in view['rows'] if row['grade'] == 'G4-stock')['percent'], 100.0)

    def test_g0_excluded_from_live_denominator(self):
        view = self.view()
        self.assertEqual((view['inventoried_nodes'], view['excluded_g0'], view['denominator']), (8, 1, 7))
        self.assertAlmostEqual(view['rows'][0]['percent'], 100 / 7)

    def test_all_g0_is_not_applicable_not_fake_zero_coverage(self):
        graph = {'format': 'decompile-callgraph-v1', 'graph': {'excluded': []}}
        view = bars.summarize(graph, {'format': 'decompile-grades-v1', 'grades': {'excluded': 'G0'}})
        self.assertTrue(all(row['percent'] is None for row in view['rows']))
        text = bars.render(view)
        self.assertIn('N/A', text)
        self.assertNotIn('0.0%', text)

    def test_legacy_g4_is_not_defaulted_to_stock(self):
        view = self.view()
        rows = {row['grade']: row['count'] for row in view['rows']}
        self.assertEqual(rows['G4-ambiguous'], 1)
        self.assertEqual(rows['G4-stock'], 1)
        self.assertTrue(view['coverage_indeterminate'])

    def test_missing_grade_and_unknown_dependencies_remain_explicit(self):
        self.graph['unknown_calls'] = ['raw']
        view = self.view()
        self.assertEqual(view['unknown_dependency_count'], 1)
        self.assertEqual(next(row for row in view['rows'] if row['grade'] == 'ungraded')['count'], 1)
        self.assertIn('indeterminate', bars.render(view))

    def test_incomplete_inventory_warning_is_not_hidden(self):
        self.graph.pop('inventory_complete')
        self.assertFalse(self.view()['inventory_complete_declared'])
        self.assertIn('indeterminate', bars.render(self.view()))

    def test_visual_rounding_does_not_change_counts_or_percentages(self):
        view = self.view()
        before = copy.deepcopy(view)
        short = bars.render(view, width=3, ascii_only=True)
        wide = bars.render(view, width=40)
        self.assertIn('(1/7)', short)
        self.assertIn('(1/7)', wide)
        self.assertEqual(view, before)
        self.assertEqual(len(bars.bar(1, 7, 3, '#', '.')), 3)

    def test_invalid_width_or_counts_refused_not_silently_clamped(self):
        for width in (0, -1, True, 201):
            with self.assertRaises(bars.closure.ClosureError):
                bars.render(self.view(), width=width)
        with self.assertRaises(bars.closure.ClosureError):
            bars.bar(8, 7, 30, '#', '.')

    def test_input_graph_and_grades_are_not_mutated(self):
        before = copy.deepcopy((self.graph, self.grades))
        self.view()
        self.assertEqual((self.graph, self.grades), before)

    def test_no_semantic_truth_or_reconciliation_is_claimed(self):
        view = self.view()
        self.assertFalse(view['semantic_truth_verified'])
        self.assertFalse(view['promotion_authorized'])
        self.assertFalse(view['reconciliation_executed'])
        self.assertIn('not verified coverage', bars.render(view))

    def test_cli_is_read_only_and_ascii_fallback_works(self):
        with tempfile.TemporaryDirectory(prefix='census-bars-') as folder:
            root = Path(folder)
            (root / 'graph.json').write_text(json.dumps(self.graph))
            (root / 'grades.json').write_text(json.dumps(self.grades))
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            args = [sys.executable, '-B', str(SCRIPT), '--project', str(root), '--callgraph', 'graph.json', '--grades', 'grades.json']
            run = subprocess.run(args + ['--ascii', '--width', '12'], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('G4-stock', run.stdout)
            self.assertIn('G4-recon', run.stdout)
            self.assertNotIn('\x1b', run.stdout)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            structured = subprocess.run(args + ['--json'], capture_output=True, text=True, timeout=10)
            self.assertEqual(structured.returncode, 0, structured.stdout)
            self.assertEqual(json.loads(structured.stdout)['result']['denominator'], 7)
            overridden = subprocess.run(args + ['--total', '999'], capture_output=True, text=True, timeout=10)
            self.assertEqual(overridden.returncode, 2)

    def test_invalid_source_grades_rejected_by_existing_validator(self):
        self.grades['grades']['raw'] = 'invented'
        with self.assertRaises(bars.closure.ClosureError):
            self.view()


if __name__ == '__main__':
    unittest.main()
