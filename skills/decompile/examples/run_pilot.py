"""Synthetic pilot for the decompile scheduler. No firmware, disassembler, or hardware.

It builds a synthetic call graph and grade map, runs the read-only closure report, and
checks the scheduling logic (testable-now set and helper leverage). It proves the helper's
arithmetic, not any real reconstruction.
"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/closure.py'
spec = importlib.util.spec_from_file_location('closure_pilot', SCRIPT)
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)


def main():
    callgraph = {'format': 'decompile-callgraph-v1', 'graph': {
        'fn_bind': [], 'fn_leafP': [], 'fn_leafQ': [],
        'fn_undoneHelper': ['fn_leafQ'],
        'fn_recon1': ['fn_bind', 'fn_leafP'],
        'fn_recon3': ['fn_undoneHelper'],
        'fn_big': ['fn_bind', 'fn_undoneHelper'],
    }}
    grades = {'format': 'decompile-grades-v1', 'grades': {
        'fn_bind': 'G4', 'fn_leafP': 'G4', 'fn_leafQ': 'G4',
        'fn_undoneHelper': 'G2', 'fn_recon1': 'G1', 'fn_recon3': 'G1', 'fn_big': 'G1',
    }}

    with tempfile.TemporaryDirectory(prefix='decompile-pilot-') as tmp:
        root = Path(tmp)
        (root / 'callgraph.json').write_text(json.dumps(callgraph), encoding='utf-8')
        (root / 'grades.json').write_text(json.dumps(grades), encoding='utf-8')
        result = closure.build_report(callgraph, grades)

    checks = {
        'recon1 is testable now (closure complete)': 'fn_recon1' in result['testable_now'],
        'undoneHelper is testable now (only callee done)': 'fn_undoneHelper' in result['testable_now'],
        'big is NOT testable (depends on undone helper)': 'fn_big' not in result['testable_now'],
        'top leverage is the undone helper': result['top_leverage'][0]['id'] == 'fn_undoneHelper',
        'no semantic truth claimed': result['semantic_truth_verified'] is False,
        'no promotion authorised': result['promotion_authorized'] is False,
    }
    for label, ok in checks.items():
        print(('PASS' if ok else 'FAIL') + ' - ' + label)
    if not all(checks.values()):
        print('PILOT FAILED')
        return 1
    print('PILOT OK - synthetic scheduling logic verified; no firmware or hardware involved')
    return 0


if __name__ == '__main__':
    sys.exit(main())
