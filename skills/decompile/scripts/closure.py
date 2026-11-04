"""Read-only call-graph closure and leverage report for scheduling recompilation-grade work.

It does not disassemble, execute, or grade anything. It consumes a declared call graph and a
declared grade map (produced by other tools) and reports which units are differentially
testable now (their transitive callees are already reconstructed) and which undone helpers
carry the most leverage. Nothing here establishes semantic truth or promotes a grade.
"""
import argparse
import json
from pathlib import Path
import sys

GRADES = {'G0': 0, 'G1': 1, 'G2': 2, 'G3': 3, 'G4': 4}
DONE_MIN = GRADES['G3']  # "done" = compiles or bench-confirmed (G3+)


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
        require(isinstance(callees, list), 'GRAPH', 'Callees must be a list')
        out = []
        for callee in callees:
            require(text(callee), 'GRAPH', 'Callee identifiers must be non-empty strings')
            out.append(callee)
            nodes.add(callee)
        edges[fn] = out
        nodes.add(fn)
    for fn in nodes:
        edges.setdefault(fn, [])

    grade = {}
    for fn, value in grademap.items():
        require(text(fn), 'GRADES', 'Graded identifiers must be non-empty strings')
        require(value in GRADES, 'GRADES', 'Grade must be one of G0, G1, G2, G3, G4')
        grade[fn] = value
    return nodes, edges, grade


def is_done(fn, grade):
    value = grade.get(fn)
    return value is not None and GRADES[value] >= DONE_MIN


def is_proven(fn, grade):
    return grade.get(fn) == 'G4'


def closure_flags(nodes, edges, grade):
    """ft3[fn]: the transitive callee-closure of fn is fully G3+ (links and runs without stub).
    ft4[fn]: the transitive callee-closure is fully G4 (every callee bench-confirmed).
    A cycle whose closure is not yet established resolves to False; never loops forever.
    fn's own grade is not part of its callee-closure."""
    ft3, ft4 = {}, {}

    def visit(fn, want_proven, stack):
        cache = ft4 if want_proven else ft3
        if fn in cache:
            return cache[fn]
        if fn in stack:
            return False
        stack = stack | {fn}
        ok = True
        for callee in edges.get(fn, ()):
            callee_done = is_proven(callee, grade) if want_proven else is_done(callee, grade)
            if not callee_done or not visit(callee, want_proven, stack):
                ok = False
                break
        cache[fn] = ok
        return ok

    for fn in nodes:
        visit(fn, False, set())
        visit(fn, True, set())
    return ft3, ft4


def build_report(callgraph, grades, limit=50):
    nodes, edges, grade = normalize(callgraph, grades)
    ft3, ft4 = closure_flags(nodes, edges, grade)

    undone = {fn for fn in nodes if not is_done(fn, grade)}
    ungraded = sorted(fn for fn in nodes if fn not in grade)

    # testable_now: undone units whose callee-closure is already complete (criterion C1).
    testable_now = sorted(fn for fn in undone if ft3.get(fn))

    # leverage: for each UNDONE node, how many distinct UNDONE callers depend on it (criterion C2).
    undone_callers = {fn: set() for fn in nodes}
    for caller, callees in edges.items():
        if caller in undone:
            for callee in callees:
                undone_callers[callee].add(caller)
    leverage = sorted(
        ({'id': fn, 'undone_callers': len(undone_callers[fn]), 'grade': grade.get(fn, 'ungraded'),
          'closure_ready': bool(ft3.get(fn))}
         for fn in undone),
        key=lambda row: (-row['undone_callers'], row['id']))

    return {
        'passed': True,
        'format': 'decompile-closure-report-v1',
        'totals': {
            'nodes': len(nodes),
            'graded': len(grade),
            'ungraded': len(ungraded),
            'done_g3_plus': sum(1 for fn in nodes if is_done(fn, grade)),
            'proven_g4': sum(1 for fn in nodes if is_proven(fn, grade)),
            'undone': len(undone),
        },
        'ft_g3_closed': sum(1 for fn in nodes if ft3.get(fn)),
        'ft_g4_closed': sum(1 for fn in nodes if ft4.get(fn)),
        'testable_now_count': len(testable_now),
        'testable_now': testable_now[:limit],
        'top_leverage': leverage[:limit],
        'ungraded_sample': ungraded[:limit],
        'coverage_indeterminate': bool(ungraded),
        'scope': 'Scheduling aid over declared graph and grades only; no decode, execution, grading, or promotion',
        'semantic_truth_verified': False,
        'promotion_authorized': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    report = sub.add_parser('report', help='Report testable-now units and helper leverage')
    report.add_argument('--callgraph', required=True, help='decompile-callgraph-v1 JSON (explicit path)')
    report.add_argument('--grades', required=True, help='decompile-grades-v1 JSON (explicit path)')
    report.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()
    try:
        root = Path(args.project).resolve()
        require(root.is_dir(), 'PATH', 'Project root is missing')
        require(args.limit >= 0, 'INPUT', 'limit must be non-negative')
        result = build_report(load_json(args.callgraph), load_json(args.grades), args.limit)
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=True))
        return 0 if result['passed'] else 3
    except (ClosureError, OSError, ValueError, RecursionError) as error:
        code = error.code if isinstance(error, ClosureError) else 'INPUT'
        print(json.dumps({'ok': False, 'code': code, 'error': str(error)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
