"""Explicit integration with an unmodified local VeriMission 8.2, using synthetic data only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/decompile/scripts'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_refusal(module, code, action):
    try:
        action()
    except module.Refusal as error:
        assert error.code == code, (error.code, code)
        return
    raise AssertionError('Expected native refusal: ' + code)


def scenario(harness, adapter, name):
    with tempfile.TemporaryDirectory(prefix='disasm-native82-' + name + '-') as folder:
        root = Path(folder)
        for child in ('tools', 'grades', 'cycles', 'exports', 'notes'):
            (root / child).mkdir()
        for filename in ('closure.py', 'verimission_adapter.py'):
            shutil.copyfile(SCRIPTS / filename, root / 'tools' / filename)
        # This criterion only verifies frozen bundles. It never exports or reconciles anything.
        worker = """from pathlib import Path
import sys
from verimission_adapter import verify_bundle, closure
root = Path.cwd()
contract = closure.load_json(root / 'contract.json')
for cycle in range(int(sys.argv[1]) + 1):
    data = closure.load_json(root / 'cycles' / ('cycle-%d.json' % cycle))
    verify_bundle(root, contract, data, 'exports/cycle-%d' % cycle)
"""
        (root / 'tools/check_bundles.py').write_text(worker, encoding='utf-8')
        def write(relative, value):
            raw = value if isinstance(value, bytes) else (json.dumps(value, sort_keys=True) + '\n').encode()
            (root / relative).write_bytes(raw)
            return {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}
        target = write('target.dat', b'synthetic declared target; never executed')
        proof = write('proof.txt', b'synthetic receipt for conversion tests; not true compiler/bench evidence')
        graph = write('graph.json', {'format': 'decompile-callgraph-v1', 'inventory_complete': True,
                                     'graph': {'A': [], 'B': [], 'excluded': []}})
        contract = {'format': 'disasm-verimission-contract-v1', 'target': target, 'projection': 'reconstruction-v1',
                    'scope': 'Three synthetic inventory IDs, one declared G0 exclusion', 'anchor': 0,
                    'units': ['A', 'B', 'excluded'], 'excluded_g0': ['excluded']}
        write('contract.json', contract)
        loss_case = name == 'possible_loss'
        def export(cid, live_grade, closed_grade, before=None, kind='progress', receipt=True):
            live = {'A': live_grade, 'B': 'G4-stock', 'excluded': 'G0'}
            closed = {'A': closed_grade, 'B': 'G4-stock', 'excluded': 'G0'}
            data = {'format': 'disasm-cycle-snapshot-v1', 'cycle': cid, 'callgraph': graph,
                    'live': write('grades/live-%d.json' % cid, {'format': 'decompile-grades-v1', 'grades': live}),
                    'closed': write('grades/closed-%d.json' % cid, {'format': 'decompile-grades-v1', 'grades': closed}),
                    'transitions': [], 'facts_recorded': ['fact-fixture'] if loss_case and cid < 2 else [],
                    'facts_used': ['fact-fixture'] if loss_case and cid < 2 else []}
            if before is not None and receipt:
                data['transitions'] = [{'id': 'A', 'from': before, 'to': closed_grade, 'kind': kind,
                                        'reason': 'Synthetic transition fixture, not an actual grade gate', 'evidence': [proof]}]
            write('cycles/cycle-%d.json' % cid, data)
            adapter.export_bundle(root, contract, data, 'exports/cycle-%d' % cid)
            return data
        regression = name in {'justified_retraction', 'unexplained_regression'}
        baseline_grade, first_grade, second_grade = ('G2', 'G3', 'G2') if regression else ('G1', 'G2', 'G3')
        export(0, baseline_grade, baseline_grade)
        baseline = json.loads((root / 'exports/cycle-0/receipt.json').read_text())
        assert baseline['projection_notes']['closed']['stock_only'] == ['B']
        (root / 'governing.md').write_text('KEEP_EVIDENCE: never inflate a grade.\n'
            '<!-- objectives -->\nVerify a bounded adapter fixture.\n<!-- /objectives -->\n'
            '<!-- scenario -->\nSynthetic declarations, no real target.\n<!-- /scenario -->\n', encoding='utf-8')
        common = ['target.dat', 'graph.json', 'proof.txt', 'contract.json', 'tools/closure.py',
                  'tools/verimission_adapter.py', 'tools/check_bundles.py']
        def artifacts(through):
            return common + [path for n in range(through + 1) for path in
                             ['cycles/cycle-%d.json' % n, 'grades/live-%d.json' % n, 'grades/closed-%d.json' % n,
                              'exports/cycle-%d/observation.json' % n, 'exports/cycle-%d/receipt.json' % n]]
        h = harness.Harness(root)
        h.init({'objective': 'Verify adapter and native reconciliation, without claiming firmware correctness', 'mode': 'light',
                'in_scope': ['synthetic conversion and read-only consistency checks'], 'out_of_scope': ['real firmware', 'installation'],
                'criteria': [{'id': 'C%d' % n, 'description': 'Frozen adapter sources and bundles through cycle %d' % n,
                              'argv': [sys.executable, '-B', 'tools/check_bundles.py', str(n)], 'artifacts': artifacts(n)} for n in (1, 2)],
                'budget': {'consolidate_every': 2},
                'periodic_review': {'notes_pattern': 'notes/cycle-{cycle}.md', 'digest_pattern': 'digest-{start}-{end}.json',
                    'governing_file': 'governing.md', 'invariant_markers': ['KEEP_EVIDENCE'],
                    'mutable_sections': {'objectives': {'begin': '<!-- objectives -->', 'end': '<!-- /objectives -->'},
                                         'scenario': {'begin': '<!-- scenario -->', 'end': '<!-- /scenario -->'}},
                    'baseline': 'exports/cycle-0/observation.json', 'observation_pattern': 'exports/cycle-{cycle}/observation.json',
                    'inventory': baseline['inventory_policy']}})
        with h.state() as state:
            initial_mission = state['mission_hash']
        for cid in (1, 2):
            reviewed = h.review('adapter')['review']
            assert h.start({'topic': 'adapter', 'task': 'verify-fixture', 'premise': 'Source binding is current',
                'residual': 'Run conversion preflight; native review remains separate', 'review_id': reviewed['id'],
                'reviewed_claims': [], 'criteria': ['C%d' % cid],
                'approach': {'method': 'frozen adapter verifier', 'inputs': 'cycle snapshot and receipts', 'environment': 'synthetic local'}})['cycle'] == cid
            grade = first_grade if cid == 1 else second_grade
            mismatch = name == 'live_close_mismatch' and cid == 2
            current = export(cid, 'G3' if mismatch else grade, first_grade if mismatch else grade,
                             before=baseline_grade if cid == 1 else first_grade,
                             kind='retraction' if regression and cid == 2 else 'progress',
                             receipt=not (cid == 2 and name in {'unmarked_promotion', 'unexplained_regression', 'live_close_mismatch'}))
            (root / 'notes' / ('cycle-%d.md' % cid)).write_text(
                'Cycle %d: frozen synthetic declarations were converted; this is not evidence of firmware correctness.\n' % cid,
                encoding='utf-8')
            assert h.check(cid, 'C%d' % cid)['passed']
            if cid == 1:
                h.close(cid, 'verified', 'Next bounded fixture')
        if name == 'source_drift':
            path = root / 'grades/closed-2.json'
            path.write_bytes(path.read_bytes() + b' ')
            try:
                adapter.verify_bundle(root, contract, current, 'exports/cycle-2')
                raise AssertionError('Source drift must refuse preflight')
            except adapter.AdapterError as error:
                assert error.code == 'SOURCE_STALE'
            require_refusal(harness, 'STALE_ARTIFACT', lambda: h.close(2, 'verified', 'No stale closure'))
            return {'source_drift_blocks_verified_close': True}
        expected_flag = {'unmarked_promotion': 'unmarked_promotions', 'unexplained_regression': 'unexplained_regression',
                         'live_close_mismatch': 'live_close_mismatch'}.get(name)
        if expected_flag:
            require_refusal(harness, 'RECONCILIATION_FAILED', lambda: h.digest(2))
            with h.state() as state:
                packet = next(iter(state['digests'].values()))['packet']
                assert expected_flag in {issue['kind'] for issue in packet['reconciliation']['issues']}
                assert state['cycles'][-1]['status'] == 'active'
            require_refusal(harness, 'RECONCILIATION_FAILED', lambda: h.close(2, 'verified', 'No inconsistent closure'))
            return {name + '_blocked_by_native_reconciler': True}
        require_refusal(harness, 'PERIODIC_REVIEW_REQUIRED', lambda: h.close(2, 'verified', 'Reread still required'))
        digest = h.digest(2)
        assert digest['reconciliation']['passed'] and digest['reconciliation']['declared_total'] == 2
        if regression:
            last = digest['reconciliation']['cycles'][-1]
            assert last['metric_deltas']['declared_compiled_or_compared'] == -1
            assert last['justified_retractions'] == ['A']
        proposal = digest['review_template']
        proposal['reason'] = 'Synthetic physical reread retained bounded claims and reviewed all declarations.'
        for row in proposal['reread']:
            raw = (root / 'notes' / ('cycle-%d.md' % row['cycle'])).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row['sha256']
            row['finding'] = raw.decode().strip()
        if loss_case:
            require_refusal(harness, 'LOSS_REVIEW_REQUIRED', lambda: h.close(2, 'verified', 'Explain possible loss', review_input=proposal))
            assert [row['id'] for row in proposal['loss_acknowledgements']] == ['fact-fixture']
            for row in proposal['loss_acknowledgements']:
                row['reason'] = 'Synthetic finding: absent use is a review signal, not proof of forgetting; retain applicability limits.'
        assert h.close(2, 'verified', 'Continue within scope', review_input=proposal)['status'] == 'verified'
        assert h.validate()['passed']
        with h.state() as state:
            assert state['mission_hash'] == initial_mission and not state['claims']
            assert state['consolidations'][-1]['through_cycle'] == 2
        return {name + '_native_close_and_review_passed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', required=True, type=Path, help='Explicit path to the original local VeriMission 8.2 scripts/harness.py')
    args = parser.parse_args()
    harness = load('native_verimission82_adapter_pilot', args.harness.resolve())
    assert harness.VERSION == '8.2', 'This pilot targets the 8.2 observation contract'
    adapter = load('native_adapter_pilot', SCRIPTS / 'verimission_adapter.py')
    results = {}
    for name in ('success', 'unmarked_promotion', 'justified_retraction', 'unexplained_regression',
                 'live_close_mismatch', 'possible_loss', 'source_drift'):
        results.update(scenario(harness, adapter, name))
    results.update({'native_reconciler_reused': True, 'native_harness_sha256': hashlib.sha256(args.harness.read_bytes()).hexdigest(),
                    'semantic_truth_verified': False, 'real_target_executed': False, 'installed': False, 'published': False})
    print(json.dumps(results, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
