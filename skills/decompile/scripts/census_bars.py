"""Read-only monochrome presentation of the existing declared DisasmLedger grade census."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location('disasm_census_closure', Path(__file__).with_name('closure.py'))
closure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(closure)


def summarize(callgraph, grades):
    """Reuse closure validation/totals; add only the mutually exclusive presentation rows."""
    report = closure.build_report(callgraph, grades)
    _, _, grade, _, _ = closure.normalize(callgraph, grades)
    counts = Counter(grade.values())
    totals = report['totals']
    denominator = totals['nodes']
    rows = [('G1', counts['G1']), ('G2', counts['G2']),
            ('G3', totals['done_g3_plus'] - totals['recon_g4']),
            ('G4-stock', totals['stock_g4']), ('G4-recon', totals['recon_g4']),
            ('G4-ambiguous', len(report['legacy_g4_ambiguous'])), ('ungraded', totals['ungraded'])]
    closure.require(sum(count for _, count in rows) == denominator, 'PRESENTATION', 'Display rows do not partition the existing live census')
    return {'format': 'disasm-census-display-v1', 'denominator': denominator,
            'inventoried_nodes': totals['inventoried_nodes'], 'excluded_g0': totals['excluded_g0'],
            'rows': [{'grade': label, 'count': count, 'percent': 100 * count / denominator if denominator else None}
                     for label, count in rows],
            'declared_compiled_or_compared': totals['done_g3_plus'],
            'inventory_complete_declared': report['inventory_complete_declared'],
            'coverage_applicable': report['coverage_applicable'], 'coverage_indeterminate': report['coverage_indeterminate'],
            'unknown_dependency_count': len(report['unknown_dependencies']),
            'grades_are_declared': report['grades_are_declared'], 'evidence_verified': report['evidence_verified'],
            'semantic_truth_verified': report['semantic_truth_verified'], 'promotion_authorized': report['promotion_authorized'],
            'reconciliation_executed': False}


def bar(count, total, width=30, fill='█', empty='▒'):
    closure.require(type(width) is int and 1 <= width <= 200, 'WIDTH', 'Display width must be 1..200 characters')
    closure.require(type(count) is int and type(total) is int and 0 <= count <= total,
                    'PRESENTATION', 'Count must be within the declared nonnegative denominator')
    filled = round(count * width / total) if total else 0
    return fill * filled + empty * (width - filled)


def render(view, width=30, ascii_only=False):
    if view['format']=='disasm-qualified-census-v1':
        total=view['denominator'];fill,empty=('#','.') if ascii_only else ('█','▒')
        lines=[render(view['declared'],width,ascii_only),'',
               'Current qualified completion (live native engine; closed proof only)']
        labels=[('Declared G3/recon',view['declared']['declared_compiled_or_compared']),
                ('Verified now',view['counts']['verified']),('Pending',view['counts']['pending']),
                ('Stale',view['counts']['stale'])]
        for label,count in labels:
            ratio=f'{count}/{total}' if total else 'N/A'
            lines.append(f'{label:<20} {bar(count,total,width,fill,empty)} {ratio}')
        lines.append('Declared overlaps the evidence rows; verified + pending + stale partition the live universe.')
        lines.append('Historical grades are unchanged. Evidence scope is not universal semantic proof.')
        return '\n'.join(lines)
    # Validate even an all-G0 view; display options never alter the census.
    bar(0, 0, width)
    total = view['denominator']
    fill, empty = ('#', '.') if ascii_only else ('█', '▒')
    lines = ['Declared grade distribution (not verified coverage)',
             f"Live denominator: {total}; inventoried: {view['inventoried_nodes']}; excluded G0: {view['excluded_g0']}"]
    for row in view['rows']:
        percent = f"{row['percent']:.1f}%" if row['percent'] is not None else 'N/A'
        ratio = f"({row['count']}/{total})" if total else '(no live units)'
        lines.append(f"  {row['grade']:<14} {bar(row['count'], total, width, fill, empty)} {percent:>6} {ratio}")
    lines.append(f"G3 + G4-recon declared: {view['declared_compiled_or_compared']}/{total}" if total
                 else 'G3 + G4-recon declared: N/A')
    if not view['coverage_applicable']:
        lines.append('No live units: percentages are N/A.')
    elif view['coverage_indeterminate']:
        lines.append('Inventory/graph coverage: indeterminate; preserve source report warnings.')
    lines += [f"Unresolved dependency units: {view['unknown_dependency_count']}",
              'Percentages rounded independently; bars are visual only.',
              'No grade gates, promotion or reconciliation executed.']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--callgraph', required=True)
    parser.add_argument('--grades', required=True)
    parser.add_argument('--width', type=int, default=30, help='Bar width, 1..200 characters; counts are unchanged')
    parser.add_argument('--ascii', action='store_true', help='Use # and . instead of Unicode blocks')
    parser.add_argument('--json', action='store_true', help='Return the same display data as structured JSON')
    parser.add_argument('--harness', help='Explicit trusted Control 8.4 executor; query live sealed evidence instead of trusting a view file')
    args = parser.parse_args()
    try:
        root = Path(args.project).resolve()
        closure.require(root.is_dir(), 'PATH', 'Project root is missing')
        bar(0, 0, args.width)
        def supplied(value):
            path = Path(value)
            return path if path.is_absolute() else root / path
        view = summarize(closure.load_json(supplied(args.callgraph)), closure.load_json(supplied(args.grades)))
        if args.harness:
            spec=importlib.util.spec_from_file_location('live_qualified_census',Path(__file__).with_name('qualified_census.py'))
            qualified=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualified)
            def bound_input(value):
                path=supplied(value).resolve()
                closure.require(path.is_relative_to(root), 'PATH', 'Integrated inputs must remain inside the project')
                return closure.evidence_path(root,path.relative_to(root).as_posix())
            graph_path=bound_input(args.callgraph);grade_path=bound_input(args.grades)
            native,reader_sha=qualified.query(root,args.harness)
            view=qualified.summarize(closure.load_json(graph_path),closure.load_json(grade_path),native,
                {'path':graph_path.relative_to(root).as_posix(),'sha256':__import__('hashlib').sha256(graph_path.read_bytes()).hexdigest()})
            view['harness_reader_sha256']=reader_sha
        if args.json:
            print(json.dumps({'ok': True, 'result': view}, ensure_ascii=True))
        else:
            if not args.ascii and hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            print(render(view, args.width, args.ascii))
        return 0
    except (closure.ClosureError, OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print(json.dumps({'ok': False, 'code': error.code if isinstance(error, closure.ClosureError) else 'INPUT',
                          'error': str(error)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
