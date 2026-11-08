"""Read-only call-graph closure and leverage report for scheduling recompilation-grade work.

It does not disassemble, execute, or grade anything. It consumes a declared call graph and a
declared grade map (produced by other tools) and reports which units are differentially
testable now (their transitive callees are already reconstructed) and which undone helpers
carry the most leverage. Nothing here establishes semantic truth or promotes a grade.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys

GRADES = {'G0', 'G1', 'G2', 'G3', 'G4-stock', 'G4-recon', 'G4'}


class ClosureError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, code, message):
    if not condition:
        raise ClosureError(code, message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def load_json(path):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, 'JSON', 'Duplicate JSON keys refused')
            obj[key] = value
        return obj

    def nonfinite(_):
        raise ClosureError('JSON', 'Nonfinite JSON numbers refused')

    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      object_pairs_hook=unique, parse_constant=nonfinite)


def normalize(callgraph, grades):
    require(isinstance(callgraph, dict) and callgraph.get('format') == 'decompile-callgraph-v1',
            'GRAPH', 'Expected decompile-callgraph-v1')
    require(isinstance(grades, dict) and grades.get('format') == 'decompile-grades-v1',
            'GRADES', 'Expected decompile-grades-v1')
    graph = callgraph.get('graph')
    grademap = grades.get('grades')
    require(isinstance(graph, dict) and graph, 'GRAPH', 'graph must be a non-empty object')
    require(isinstance(grademap, dict), 'GRADES', 'grades must be an object')

    nodes = set()
    edges = {}
    for fn, callees in graph.items():
        require(text(fn), 'GRAPH', 'Function identifiers must be non-empty strings')
        require(callees is None or isinstance(callees, list), 'GRAPH',
                'Callees must be a list or null for unknown adjacency')
        out = []
        for callee in callees or []:
            require(text(callee), 'GRAPH', 'Callee identifiers must be non-empty strings')
            out.append(callee)
            nodes.add(callee)
        edges[fn] = sorted(set(out)) if callees is not None else None
        nodes.add(fn)
    for fn in nodes:
        edges.setdefault(fn, None)

    unknown_calls = callgraph.get('unknown_calls', [])
    require(isinstance(unknown_calls, list) and all(text(fn) for fn in unknown_calls),
            'GRAPH', 'unknown_calls must be a list of function identifiers')
    require(set(unknown_calls) <= nodes, 'GRAPH', 'unknown_calls identifiers must exist in graph')
    inventory_complete = callgraph.get('inventory_complete', False)
    require(type(inventory_complete) is bool, 'GRAPH', 'inventory_complete must be boolean')
    unknown = {fn for fn in nodes if edges[fn] is None} | set(unknown_calls)

    grade = {}
    for fn, value in grademap.items():
        require(text(fn), 'GRADES', 'Graded identifiers must be non-empty strings')
        require(isinstance(value, str) and value in GRADES, 'GRADES',
                'Expected G0, G1, G2, G3, G4-stock, G4-recon, or legacy G4')
        require(fn in nodes, 'GRADES', 'Graded identifier absent from graph: ' + fn)
        grade[fn] = value
    return nodes, edges, grade, unknown, inventory_complete


def is_done(fn, grade):
    return grade.get(fn) in {'G3', 'G4-recon'}


def is_proven(fn, grade):
    return grade.get(fn) == 'G4-recon'


def closure_flags(nodes, edges, grade, unknown):
    """Declared callee closure only, without validating compile/bench evidence.

    Unknown adjacency/indirect calls and unresolved cycles remain closed=False.
    A node's own grade is not part of its callee closure. Iterative O(V+E).
    """
    parents = {fn: [] for fn in nodes}
    for caller in nodes:
        for callee in edges[caller] or []:
            parents[callee].append(caller)

    def calculate(eligible):
        remaining = {fn: len(edges[fn] or []) for fn in nodes}
        closed = {fn: False for fn in nodes}
        queue = deque(fn for fn in nodes if not remaining[fn] and fn not in unknown)
        while queue:
            fn = queue.popleft()
            closed[fn] = True
            if not eligible(fn, grade):
                continue
            for parent in parents[fn]:
                remaining[parent] -= 1
                if remaining[parent] == 0 and parent not in unknown:
                    queue.append(parent)
        return closed

    return calculate(is_done), calculate(is_proven)


def build_report(callgraph, grades, limit=50):
    require(type(limit) is int and limit >= 0, 'INPUT', 'limit must be a non-negative integer')
    nodes, edges, grade, unknown, inventory_complete = normalize(callgraph, grades)
    ft3, ft4 = closure_flags(nodes, edges, grade, unknown)
    live = {fn for fn in nodes if grade.get(fn) != 'G0'}
    ambiguous = sorted(fn for fn in live if grade.get(fn) == 'G4')

    undone = {fn for fn in live if not is_done(fn, grade)}
    ungraded = sorted(fn for fn in live if fn not in grade)

    # testable_now: undone units whose callee-closure is already complete (criterion C1).
    testable_now = sorted(fn for fn in undone if ft3.get(fn))

    # leverage: for each UNDONE node, how many distinct UNDONE callers depend on it (criterion C2).
    undone_callers = {fn: set() for fn in nodes}
    for caller, callees in edges.items():
        if caller in undone:
            for callee in callees or []:
                undone_callers[callee].add(caller)
    leverage = sorted(
        ({'id': fn, 'undone_callers': len(undone_callers[fn]), 'grade': grade.get(fn, 'ungraded'),
          'closure_ready': bool(ft3.get(fn))}
         for fn in undone),
        key=lambda row: (-row['undone_callers'], row['id']))

    return {
        'passed': True,
        'format': 'decompile-closure-report-v2',
        'totals': {
            'nodes': len(live),
            'inventoried_nodes': len(nodes),
            'excluded_g0': len(nodes - live),
            'graded': sum(fn in grade for fn in live),
            'ungraded': len(ungraded),
            'done_g3_plus': sum(1 for fn in live if is_done(fn, grade)),
            'stock_g4': sum(grade.get(fn) == 'G4-stock' for fn in live),
            'recon_g4': sum(is_proven(fn, grade) for fn in live),
            'undone': len(undone),
        },
        'ft_g3_closed': sum(1 for fn in live if ft3.get(fn)),
        'ft_g4_closed': sum(1 for fn in live if ft4.get(fn)),
        'testable_now_count': len(testable_now),
        'testable_now': testable_now[:limit],
        'top_leverage': leverage[:limit],
        'ungraded_sample': ungraded[:limit],
        'unknown_dependencies': sorted(unknown & live),
        'legacy_g4_ambiguous': ambiguous,
        'inventory_complete_declared': inventory_complete,
        'coverage_applicable': bool(live),
        'coverage_indeterminate': bool(ungraded or unknown & live or ambiguous or not inventory_complete),
        'grades_are_declared': True,
        'evidence_verified': False,
        'scope': 'Scheduling aid over declared graph and grades only; no decode, execution, grading, or promotion',
        'semantic_truth_verified': False,
        'promotion_authorized': False,
    }


def manifest_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def export_context(provenance):
    return manifest_digest({'target': provenance['target'], 'producer': provenance['producer']})


def evidence_path(root, relative):
    require(text(relative), 'PATH', 'A project-relative evidence path is required')
    portable = relative.replace('\\', '/')
    part = Path(portable)
    win = PureWindowsPath(relative)
    require(not part.is_absolute() and not win.drive and not win.root and '..' not in part.parts
            and ':' not in portable and '.harness' not in {x.casefold() for x in part.parts},
            'PATH', 'Evidence must stay inside the project and outside harness state')
    path = (root / part).resolve()
    require(path.is_relative_to(root) and '.harness' not in {x.casefold() for x in path.relative_to(root).parts},
            'PATH', 'Evidence resolves outside the authorized project')
    return path


def bound_report(project, graph_file, grade_file, provenance, limit=50):
    """Optional physical provenance for an existing export; no exporter or target interpreter."""
    root = Path(project).resolve()
    require(root.is_dir(), 'PATH', 'Project root is missing')
    required = {'format', 'target', 'callgraph', 'grades', 'producer', 'edges', 'export_context_sha256'}
    require(isinstance(provenance, dict) and set(provenance) == required and
            provenance['format'] == 'decompile-provenance-v1', 'PROVENANCE', 'Use decompile-provenance-v1')
    producer = provenance['producer']
    require(isinstance(producer, dict) and set(producer) == {'name', 'version', 'settings'} and
            text(producer['name']) and text(producer['version']) and isinstance(producer['settings'], dict),
            'PROVENANCE', 'Declare producer name, version and actual settings')
    require(provenance['export_context_sha256'] == export_context(provenance), 'PROVENANCE_STALE',
            'Target or producer context changed since this export declaration; reassess/re-export')
    witnesses = []
    def receipt(value):
        require(isinstance(value, dict) and set(value) == {'path', 'sha256'} and text(value['sha256']),
                'PROVENANCE', 'Evidence receipts need path and SHA-256')
        path = evidence_path(root, value['path'])
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == value['sha256'],
                'PROVENANCE_STALE', 'A declared evidence file is missing or changed')
        witnesses.append((path, value['sha256']))
        return path
    receipt(provenance['target'])
    graph_path, grade_path = receipt(provenance['callgraph']), receipt(provenance['grades'])
    def supplied(value):
        path = Path(value)
        return (path if path.is_absolute() else root / path).resolve()
    require(supplied(graph_file) == graph_path and supplied(grade_file) == grade_path,
            'PROVENANCE', 'Selected graph/grades do not match the bound export files')
    callgraph, grades = load_json(graph_path), load_json(grade_path)
    result = build_report(callgraph, grades, limit)
    all_edges = {(caller, callee) for caller, targets in callgraph['graph'].items() for callee in targets or []}
    rows = provenance['edges']
    require(isinstance(rows, list), 'PROVENANCE', 'Edge provenance must be a list')
    seen, counts = set(), {'inferred': 0, 'resolved': 0, 'observed': 0}
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'caller', 'callee', 'basis', 'evidence'} and
                text(row['caller']) and text(row['callee']) and isinstance(row['basis'], str) and row['basis'] in counts,
                'PROVENANCE', 'Declare existing edge and inferred/resolved/observed origin')
        pair = (row['caller'], row['callee'])
        require(pair in all_edges and pair not in seen and isinstance(row['evidence'], list) and row['evidence'],
                'PROVENANCE', 'Each annotated graph edge needs unique, current evidence')
        seen.add(pair)
        counts[row['basis']] += 1
        for ref in row['evidence']:
            receipt(ref)
    require(all(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == checksum for path, checksum in witnesses),
            'PROVENANCE_STALE', 'An input changed during report construction')
    result['provenance'] = {'manifest_sha256': manifest_digest(provenance),
                            'export_context_sha256': provenance['export_context_sha256'],
                            'target_sha256': provenance['target']['sha256'], 'physical_hashes_match': True,
                            'producer': producer, 'edge_basis_counts': counts,
                            'edge_annotation_coverage': {'annotated': len(seen), 'total': len(all_edges)},
                            'runtime_edges_authenticated': False, 'producer_execution_authenticated': False}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    report = sub.add_parser('report', help='Report testable-now units and helper leverage')
    report.add_argument('--callgraph', required=True, help='decompile-callgraph-v1 JSON (explicit path)')
    report.add_argument('--grades', required=True, help='decompile-grades-v1 JSON (explicit path)')
    report.add_argument('--limit', type=int, default=50)
    report.add_argument('--provenance', help='Optional decompile-provenance-v1 JSON; does not export or promote')
    args = parser.parse_args()
    try:
        root = Path(args.project).resolve()
        require(root.is_dir(), 'PATH', 'Project root is missing')
        require(args.limit >= 0, 'INPUT', 'limit must be non-negative')
        graph_path = Path(args.callgraph)
        grade_path = Path(args.grades)
        if args.provenance:
            provenance_path = Path(args.provenance)
            result = bound_report(root, graph_path, grade_path,
                                  load_json(provenance_path if provenance_path.is_absolute() else root / provenance_path), args.limit)
        else:
            result = build_report(load_json(graph_path if graph_path.is_absolute() else root / graph_path),
                                  load_json(grade_path if grade_path.is_absolute() else root / grade_path), args.limit)
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=True))
        return 0 if result['passed'] else 3
    except (ClosureError, OSError, ValueError, RecursionError) as error:
        code = error.code if isinstance(error, ClosureError) else 'INPUT'
        print(json.dumps({'ok': False, 'code': code, 'error': str(error)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
