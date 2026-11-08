import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verimission_adapter.py'
spec = importlib.util.spec_from_file_location('verimission_adapter_test', SCRIPT)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='disasm-bridge-')
        self.root = Path(self.temp.name)
        (self.root / 'exports').mkdir()
        target = self.write('target.dat', b'synthetic bytes; no target execution')
        graph = self.write('graph.json', {'format': 'decompile-callgraph-v1', 'inventory_complete': True,
                                        'graph': {'A': [], 'B': [], 'discarded': []}})
        self.live = {'A': 'G2', 'B': 'G4-stock', 'discarded': 'G0'}
        self.closed = dict(self.live)
        self.contract = {'format': 'disasm-verimission-contract-v1', 'target': target,
                         'projection': 'reconstruction-v1', 'scope': 'Synthetic declared inventory', 'anchor': 0,
                         'units': ['A', 'B', 'discarded'], 'excluded_g0': ['discarded']}
        self.cycle = {'format': 'disasm-cycle-snapshot-v1', 'cycle': 1, 'callgraph': graph,
                      'live': self.grade_file('live.json', self.live), 'closed': self.grade_file('closed.json', self.closed),
                      'transitions': [], 'facts_recorded': ['fact-a'], 'facts_used': ['fact-a']}
        self.proof = self.write('evidence.txt', b'synthetic gate receipt, not a true compiler or emulator test')

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        raw = value if isinstance(value, bytes) else (json.dumps(value, sort_keys=True) + '\n').encode()
        (self.root / name).write_bytes(raw)
        return {'path': name, 'sha256': hashlib.sha256(raw).hexdigest()}

    def grade_file(self, name, grades):
        return self.write(name, {'format': 'decompile-grades-v1', 'grades': grades})

    def refresh_grades(self):
        self.cycle['live'] = self.grade_file('live.json', self.live)
        self.cycle['closed'] = self.grade_file('closed.json', self.closed)

    def build(self):
        return adapter.build_bundle(self.root, self.contract, self.cycle)

    def export(self):
        return adapter.export_bundle(self.root, self.contract, self.cycle, 'exports/cycle-1')

    def reject(self, code, operation):
        with self.assertRaises(adapter.AdapterError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def transition(self, before='G2', after='G3', **extra):
        return {'id': 'A', 'from': before, 'to': after, 'kind': 'progress', 'reason': 'Synthetic declared gate',
                'evidence': [self.proof], **extra}

    def test_projection_preserves_stock_without_promoting_reconstruction(self):
        packet = self.build()
        self.assertEqual(packet['observation']['closed'], {'A': 'G2', 'B': 'ungraded'})
        self.assertEqual(packet['receipt']['raw_grades']['closed'], self.closed)
        self.assertEqual(packet['receipt']['projection_notes']['closed']['stock_only'], ['B'])
        self.assertFalse(packet['receipt']['reconciliation_executed'])
        self.assertFalse(packet['receipt']['promotion_authorized'])

    def test_legacy_ambiguous_grade_is_ungraded_and_reported(self):
        self.closed['B'] = 'G4'
        self.refresh_grades()
        packet = self.build()
        self.assertEqual(packet['observation']['closed']['B'], 'ungraded')
        self.assertEqual(packet['receipt']['projection_notes']['closed']['legacy_g4_ambiguous'], ['B'])

    def test_g0_exclusion_is_fixed_and_explicit_in_policy(self):
        packet = self.build()
        self.assertEqual(packet['receipt']['inventory_policy']['total'], 2)
        self.assertEqual(packet['receipt']['excluded_g0'], ['discarded'])
        self.assertEqual(packet['receipt']['inventory_policy']['categories'], ['ungraded', 'G1', 'G2', 'G3', 'G4-recon'])

    def test_new_g0_classification_requires_new_epoch_not_silent_shrinking(self):
        self.closed['A'] = 'G0'
        self.refresh_grades()
        self.reject('EPOCH_REQUIRED', self.build)

    def test_reactivated_g0_requires_new_epoch(self):
        self.live['discarded'] = self.closed['discarded'] = 'G1'
        self.refresh_grades()
        self.reject('EPOCH_REQUIRED', self.build)

    def test_graph_universe_change_is_not_silently_dropped(self):
        self.cycle['callgraph'] = self.write('graph.json', {'format': 'decompile-callgraph-v1', 'inventory_complete': True,
                                                          'graph': {'A': [], 'B': [], 'discarded': [], 'new': []}})
        self.reject('EPOCH_REQUIRED', self.build)

    def test_incomplete_inventory_cannot_create_coverage_policy(self):
        graph = {'format': 'decompile-callgraph-v1', 'graph': {'A': [], 'B': [], 'discarded': []}}
        self.cycle['callgraph'] = self.write('graph.json', graph)
        self.reject('INVENTORY_INCOMPLETE', self.build)

    def test_all_excluded_is_not_fabricated_zero_over_zero_inventory(self):
        self.contract['excluded_g0'] = self.contract['units'][:]
        self.reject('EMPTY_INVENTORY', self.build)

    def test_missing_grade_remains_ungraded(self):
        self.closed.pop('B')
        self.refresh_grades()
        packet = self.build()
        self.assertEqual(packet['observation']['closed']['B'], 'ungraded')
        self.assertEqual(packet['receipt']['projection_notes']['closed']['missing_grade'], ['B'])

    def test_live_closed_mismatch_is_preserved_for_native_reconciler(self):
        self.closed['A'] = 'G3'
        self.refresh_grades()
        observation = self.build()['observation']
        self.assertEqual(observation['live']['A'], 'G2')
        self.assertEqual(observation['closed']['A'], 'G3')

    def test_unmarked_change_is_not_auto_receipted(self):
        self.closed['A'] = self.live['A'] = 'G3'
        self.refresh_grades()
        self.assertEqual(self.build()['observation']['transitions'], [])

    def test_transition_kind_and_claim_are_not_invented_or_repaired(self):
        self.cycle['transitions'] = [self.transition(kind='retraction', claim_id='claim-a')]
        row = self.build()['observation']['transitions'][0]
        self.assertEqual(row['kind'], 'retraction')
        self.assertEqual(row['claim_id'], 'claim-a')
        self.assertEqual(row['evidence'], [self.proof])

    def test_nonprojected_transition_is_retained_in_receipt_not_counted_as_progress(self):
        self.cycle['transitions'] = [self.transition(before='G4-stock', after='G4', id='B')]
        packet = self.build()
        self.assertEqual(packet['observation']['transitions'], [])
        self.assertEqual(packet['receipt']['unprojected_transitions'], self.cycle['transitions'])

    def test_duplicate_receipts_or_excluded_transitions_refused(self):
        self.cycle['transitions'] = [self.transition(), self.transition()]
        self.reject('TRANSITION', self.build)
        self.cycle['transitions'] = [self.transition(id='discarded', before='G0')]
        self.reject('TRANSITION', self.build)

    def test_baseline_cannot_claim_transitions(self):
        self.cycle['cycle'] = 0
        self.cycle['transitions'] = [self.transition()]
        self.reject('BASELINE', self.build)

    def test_source_hashes_and_evidence_are_checked(self):
        self.cycle['transitions'] = [self.transition()]
        (self.root / 'evidence.txt').write_bytes(b'changed')
        self.reject('SOURCE_STALE', self.build)

    def test_source_paths_cannot_escape_or_reference_harness_store(self):
        for path in ('../target.dat', 'C:\\outside\\target.dat', '.harness/state.yaml'):
            self.contract['target']['path'] = path
            self.reject('PATH', self.build)

    def test_native_observation_has_only_supported_fields(self):
        fields = set(self.build()['observation'])
        self.assertEqual(fields, {'cycle', 'live', 'closed', 'transitions', 'facts_recorded', 'facts_used'})

    def test_facts_are_passthrough_labels_not_declared_true(self):
        self.cycle['facts_used'] = []
        packet = self.build()
        self.assertEqual(packet['observation']['facts_recorded'], ['fact-a'])
        self.assertEqual(packet['observation']['facts_used'], [])
        self.assertFalse(packet['receipt']['semantic_truth_verified'])

    def test_verify_reads_sources_without_rewriting_them(self):
        self.export()
        before = self.snapshot()
        report = adapter.verify_bundle(self.root, self.contract, self.cycle, 'exports/cycle-1')
        self.assertTrue(report['sources_current'])
        self.assertFalse(report['reconciliation_executed'])
        self.assertEqual(before, self.snapshot())

    def test_changed_raw_source_invalidates_export_even_without_grade_change(self):
        self.export()
        path = self.root / 'closed.json'
        path.write_bytes(path.read_bytes() + b' ')
        self.reject('SOURCE_STALE', lambda: adapter.verify_bundle(self.root, self.contract, self.cycle, 'exports/cycle-1'))

    def test_tampered_observation_or_receipt_is_not_accepted(self):
        self.export()
        observation = self.root / 'exports/cycle-1/observation.json'
        original = observation.read_bytes()
        observation.write_bytes(original + b' ')
        self.reject('BUNDLE_STALE', lambda: adapter.verify_bundle(self.root, self.contract, self.cycle, 'exports/cycle-1'))
        observation.write_bytes(original)
        (self.root / 'exports/cycle-1/receipt.json').write_text('{}')
        self.reject('BUNDLE_STALE', lambda: adapter.verify_bundle(self.root, self.contract, self.cycle, 'exports/cycle-1'))

    def test_existing_bundle_is_never_overwritten(self):
        self.export()
        before = self.snapshot()
        self.reject('OUTPUT_EXISTS', self.export)
        self.assertEqual(before, self.snapshot())

    def test_unknown_contract_fields_and_bad_cycle_types_refused(self):
        self.contract['automatic_promotion'] = True
        self.reject('CONTRACT', self.build)
        self.contract.pop('automatic_promotion')
        self.cycle['cycle'] = True
        self.reject('CYCLE', self.build)

    def test_cli_export_then_verify_with_real_files(self):
        self.write('contract.json', self.contract)
        self.write('cycle.json', self.cycle)
        base = [sys.executable, '-B', str(SCRIPT), '--project', str(self.root)]
        exported = subprocess.run(base + ['export', '--contract', 'contract.json', '--input', 'cycle.json', '--bundle', 'exports/cli'],
                                  capture_output=True, text=True, timeout=10)
        self.assertEqual(exported.returncode, 0, exported.stdout)
        checked = subprocess.run(base + ['verify', '--contract', 'contract.json', '--input', 'cycle.json', '--bundle', 'exports/cli'],
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stdout)
        self.assertFalse(json.loads(checked.stdout)['result']['reconciliation_executed'])

    def bind_graph_provenance(self, target=None):
        provenance = {'format': 'decompile-provenance-v1', 'target': target or self.contract['target'],
                      'callgraph': self.cycle['callgraph'], 'grades': self.cycle['closed'],
                      'producer': {'name': 'synthetic-exporter', 'version': 'fixture-only', 'settings': {}}, 'edges': []}
        provenance['export_context_sha256'] = adapter.closure.export_context(provenance)
        self.cycle['provenance'] = self.write('provenance.json', provenance)

    def test_optional_graph_provenance_reuses_existing_binding(self):
        self.bind_graph_provenance()
        result = self.build()['receipt']['graph_provenance']
        self.assertTrue(result['physical_hashes_match'])
        self.assertFalse(result['runtime_edges_authenticated'])

    def test_provenance_for_another_target_is_not_silently_reused(self):
        self.bind_graph_provenance(self.write('another-target.dat', b'a different synthetic target'))
        self.reject('IDENTITY', self.build)

    def test_wrong_grade_file_in_provenance_is_refused_by_existing_helper(self):
        self.bind_graph_provenance()
        data = adapter.closure.load_json(self.root / 'provenance.json')
        data['grades'] = self.cycle['live']
        self.cycle['provenance'] = self.write('provenance.json', data)
        self.reject('PROVENANCE', self.build)


if __name__ == '__main__':
    unittest.main()
