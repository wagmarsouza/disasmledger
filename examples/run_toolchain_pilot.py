"""Synthetic integration of existing closure scheduling and optional executor preflight.

No ARM compiler, angr, emulator, firmware or installed agent skill is used.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    closure = load('pilot_closure', 'skills/decompile/scripts/closure.py')
    caps = load('pilot_capabilities', 'skills/renode-bench/scripts/executor_capabilities.py')
    diff = load('pilot_differential', 'skills/renode-bench/scripts/differential.py')
    with tempfile.TemporaryDirectory(prefix='disasm-toolchain-pilot-') as folder:
        root = Path(folder)
        def write(name, data):
            raw = data if isinstance(data, bytes) else json.dumps(data).encode('utf-8')
            (root / name).write_bytes(raw)
            return {'path': name, 'sha256': hashlib.sha256(raw).hexdigest()}
        target = write('target.dat', b'synthetic identity; never executed')
        proof = write('receipt.txt', b'synthetic fixture, not a real engine capability test')
        graph = write('graph.json', {'format': 'decompile-callgraph-v1', 'graph': {'caller': ['leaf'], 'leaf': []},
                                     'unknown_calls': ['caller'], 'inventory_complete': False})
        grades = write('grades.json', {'format': 'decompile-grades-v1', 'grades': {'caller': 'G2', 'leaf': 'G3'}})
        provenance = {'format': 'decompile-provenance-v1', 'target': target, 'callgraph': graph, 'grades': grades,
                      'producer': {'name': 'synthetic-exporter', 'version': 'fixture-only', 'settings': {}},
                      'edges': [{'caller': 'caller', 'callee': 'leaf', 'basis': 'inferred', 'evidence': [proof]}]}
        provenance['export_context_sha256'] = closure.export_context(provenance)
        scheduled = closure.bound_report(root, graph['path'], grades['path'], provenance)
        assert scheduled['unknown_dependencies'] == ['caller'] and not scheduled['testable_now']
        manifest = {'format': 'bench-executor-capabilities-v1', 'target_sha256': target['sha256'],
                    'executor': {'name': 'synthetic-Unicorn', 'version': 'fixture-only', 'cpu_model': 'fixture',
                                 'configuration': {'initial_state': 'synthetic-cold'}},
                    'capabilities': {'cold-invoke': {'status': 'supported', 'reason': 'Synthetic declaration', 'evidence': [proof]},
                                     'mmio': {'status': 'unknown', 'reason': 'No evidence', 'evidence': []}}}
        manifest['assessment_context_sha256'] = caps.context_digest(manifest)
        request = {'format': 'bench-requirements-v1', 'target': target, 'unit_id': 'synthetic-mmio-unit',
                   'required_features': ['cold-invoke', 'mmio']}
        calls = []
        def invoke(**kwargs):
            calls.append(kwargs['regs'][0])
            return {'reg0': kwargs['regs'][0] + 1}
        cases = [{'regs': {0: 1}, 'expect': {'reg0': 2}}, {'regs': {0: 2}, 'expect': {'reg0': 3}}]
        context = {'project': root, 'manifest': manifest, 'requirements': request}
        try:
            diff.differential('refused', cases, invoke, blob=b'not-executed', print_report=False, executor_context=context)
            raise AssertionError('Unknown MMIO must refuse preflight')
        except diff.DifferentialError as error:
            assert error.code == 'CAPABILITY' and not calls
        # A separate unit/case, not removal of a failed requirement from the first unit.
        context = {'project': root, 'manifest': manifest,
                   'requirements': {'format': 'bench-requirements-v1', 'target': target,
                                    'unit_id': 'synthetic-cpu-only-unit', 'required_features': ['cold-invoke']}}
        assert diff.differential('fixture', cases, invoke, blob=b'not-executed', print_report=False, executor_context=context)
        assert calls == [1, 2]
        original = (root / 'target.dat').read_bytes()
        (root / 'target.dat').write_bytes(original + b'changed')
        try:
            closure.bound_report(root, graph['path'], grades['path'], provenance)
            raise AssertionError('Changed target must invalidate provenance')
        except closure.ClosureError as error:
            assert error.code == 'PROVENANCE_STALE'
        result = {'unknown_graph_edges_preserved': True, 'unknown_capability_prevents_invocation': True,
                  'synthetic_contextual_comparison_matched': True, 'changed_target_invalidates_export': True,
                  'real_engine_tested': False, 'semantic_truth_verified': False, 'installed': False, 'published': False}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
