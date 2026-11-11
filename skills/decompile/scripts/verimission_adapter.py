"""Translate declared DisasmLedger snapshots to native VeriMission 8.2 observations.

No reconciler, harness store, grade promotion, mission revision or scheduler is implemented here.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location('disasm_bridge_closure', Path(__file__).with_name('closure.py'))
closure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(closure)
AdapterError = closure.ClosureError
require, text = closure.require, closure.text
VERSION = '0.1.0-dev'
CATEGORIES = ['ungraded', 'G1', 'G2', 'G3', 'G4-recon']


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def unique_ids(value, code):
    require(isinstance(value, list) and all(text(x) for x in value) and len(set(value)) == len(value),
            code, 'Use a list of unique nonempty identifiers')
    return value


def category(grade):
    require(isinstance(grade, str) and grade in closure.GRADES | {'ungraded'}, 'TRANSITION', 'Unknown declared grade')
    require(grade != 'G0', 'EPOCH_REQUIRED', 'G0 membership is fixed by this epoch contract')
    return 'ungraded' if grade in {'ungraded', 'G4-stock', 'G4'} else grade


def build_bundle(project, contract, cycle):
    root = Path(project).resolve()
    require(root.is_dir(), 'PATH', 'Project root is missing')
    fields = {'format', 'target', 'projection', 'scope', 'anchor', 'units', 'excluded_g0'}
    require(isinstance(contract, dict) and set(contract) == fields and contract['format'] == 'disasm-verimission-contract-v1'
            and contract['projection'] == 'reconstruction-v1' and text(contract['scope'])
            and type(contract['anchor']) is int and contract['anchor'] >= 0, 'CONTRACT', 'Use the fixed-epoch reconstruction contract')
    units = set(unique_ids(contract['units'], 'CONTRACT'))
    excluded = set(unique_ids(contract['excluded_g0'], 'CONTRACT'))
    require(excluded <= units, 'CONTRACT', 'G0 exclusions must be declared unit IDs')
    active = units - excluded
    require(active, 'EMPTY_INVENTORY', 'No live units in this epoch; use notes-only review instead of a fabricated 0/0 policy')
    required = {'format', 'cycle', 'callgraph', 'live', 'closed', 'transitions'}
    require(isinstance(cycle, dict) and required <= set(cycle) <= required | {'facts_recorded', 'facts_used', 'provenance'} and
            cycle['format'] == 'disasm-cycle-snapshot-v1' and type(cycle['cycle']) is int and cycle['cycle'] >= contract['anchor'],
            'CYCLE', 'Use a structured snapshot at or after the declared epoch anchor')
    sources = {}
    def read(ref):
        require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'} and text(ref['sha256']),
                'SOURCE', 'Sources need project-relative path/SHA-256 receipts')
        path = closure.evidence_path(root, ref['path'])
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == ref['sha256'],
                'SOURCE_STALE', 'A declared source is missing or changed')
        sources[path.relative_to(root).as_posix()] = ref['sha256']
        return path
    read(contract['target'])
    graph = closure.load_json(read(cycle['callgraph']))
    live = closure.load_json(read(cycle['live']))
    closed = closure.load_json(read(cycle['closed']))
    graph_provenance = None
    if 'provenance' in cycle:
        provenance = closure.load_json(read(cycle['provenance']))
        report = closure.bound_report(root, cycle['callgraph']['path'], cycle['closed']['path'], provenance)
        graph_provenance = report['provenance']
        require(graph_provenance['target_sha256'] == contract['target']['sha256'],
                'IDENTITY', 'Graph provenance is bound to a different target')
        # Reuse the existing validator; only collect its physical dependencies for mission artifacts.
        for ref in [provenance['target'], provenance['callgraph'], provenance['grades']]:
            read(ref)
        for edge in provenance['edges']:
            for ref in edge['evidence']:
                read(ref)
    nodes, _, live_grades, _, complete = closure.normalize(graph, live)
    closure.normalize(graph, closed)
    closed_grades = closed['grades']
    require(nodes == units, 'EPOCH_REQUIRED', 'Graph unit universe changed; review a new explicit epoch instead of dropping/adding IDs')
    require(complete, 'INVENTORY_INCOMPLETE', 'A declared complete scoped inventory is required for a fixed denominator')
    notes = {}
    def project_grades(label, grades):
        require({identifier for identifier, grade in grades.items() if grade == 'G0'} == excluded,
                'EPOCH_REQUIRED', 'Declared G0 membership changed or is missing; no silent denominator edits')
        notes[label] = {'stock_only': sorted(key for key in active if grades.get(key) == 'G4-stock'),
                        'legacy_g4_ambiguous': sorted(key for key in active if grades.get(key) == 'G4'),
                        'missing_grade': sorted(active - set(grades))}
        return {key: category(grades.get(key, 'ungraded')) for key in sorted(active)}
    observation = {'cycle': cycle['cycle'], 'live': project_grades('live', live_grades),
                   'closed': project_grades('closed', closed_grades), 'transitions': [],
                   'facts_recorded': unique_ids(cycle.get('facts_recorded', []), 'CYCLE'),
                   'facts_used': unique_ids(cycle.get('facts_used', []), 'CYCLE')}
    transitions = cycle['transitions']
    require(isinstance(transitions, list), 'TRANSITION', 'Transitions must be a list')
    require(cycle['cycle'] != contract['anchor'] or not transitions, 'BASELINE', 'The epoch baseline cannot claim cycle transitions')
    seen, unprojected = set(), []
    for row in transitions:
        mandatory = {'id', 'from', 'to', 'kind', 'reason', 'evidence'}
        require(isinstance(row, dict) and mandatory <= set(row) <= mandatory | {'claim_id'} and text(row['id']) and
                row['id'] in active and row['id'] not in seen and row['kind'] in ('progress', 'retraction') and
                text(row['reason']) and isinstance(row['evidence'], list) and row['evidence'] and
                ('claim_id' not in row or text(row['claim_id'])), 'TRANSITION', 'Use unique active-unit transition declarations and current evidence')
        seen.add(row['id'])
        refs = []
        for ref in row['evidence']:
            read(ref)
            refs.append({'path': ref['path'].replace('\\', '/'), 'sha256': ref['sha256']})
        old, new = category(row['from']), category(row['to'])
        if old == new:
            unprojected.append(row)
        else:
            observation['transitions'].append({**row, 'from': old, 'to': new, 'evidence': refs})
    # No comparison with prior cycles or accounting math: the native reconciler owns both.
    require(all((root / path).is_file() and hashlib.sha256((root / path).read_bytes()).hexdigest() == checksum
                for path, checksum in sources.items()), 'SOURCE_STALE', 'A source changed during conversion')
    receipt = {'format': 'disasm-verimission-export-v1', 'adapter_version': VERSION,
               'implementation': {'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                  'closure_sha256': hashlib.sha256(Path(closure.__file__).read_bytes()).hexdigest()},
               'contract_sha256': closure.manifest_digest(contract), 'cycle_input_sha256': closure.manifest_digest(cycle),
               'cycle': cycle['cycle'], 'anchor': contract['anchor'], 'scope': contract['scope'],
               'target_sha256': contract['target']['sha256'], 'projection': contract['projection'],
               'excluded_g0': sorted(excluded), 'raw_grades': {'live': live_grades, 'closed': closed_grades},
               'projection_notes': notes, 'unprojected_transitions': unprojected, 'graph_provenance': graph_provenance,
               'inventory_policy': {'categories': CATEGORIES[:], 'total': len(active),
                                    'monotonic': {'declared_compiled_or_compared': ['G3', 'G4-recon'],
                                                  'declared_compared': ['G4-recon']}},
               'sources': [{'path': path, 'sha256': checksum} for path, checksum in sorted(sources.items())],
               'observation_sha256': hashlib.sha256(encoded(observation)).hexdigest(),
               'grades_are_declared': True, 'inventory_completeness_authenticated': False,
               'reconciliation_executed': False, 'semantic_truth_verified': False, 'promotion_authorized': False}
    return {'observation': observation, 'receipt': receipt}


def export_bundle(project, contract, cycle, bundle):
    root = Path(project).resolve()
    packet = build_bundle(root, contract, cycle)
    destination = closure.evidence_path(root, bundle)
    require(not destination.exists() and not destination.is_symlink(), 'OUTPUT_EXISTS', 'Existing bundle preserved; choose a new directory')
    require(destination.parent.is_dir(), 'PATH', 'Create the authorized bundle parent before exporting')
    try:
        destination.mkdir()  # Exclusive directory reservation; no replacement of existing artifacts.
    except FileExistsError:
        raise AdapterError('OUTPUT_EXISTS', 'Another writer reserved this bundle; existing output preserved') from None
    for name in ('observation', 'receipt'):
        with (destination / (name + '.json')).open('xb') as stream:
            stream.write(encoded(packet[name]))
    return {'bundle': destination.relative_to(root).as_posix(), 'observation_sha256': packet['receipt']['observation_sha256'],
            'sources_current': True, 'reconciliation_executed': False, 'promotion_authorized': False}


def verify_bundle(project, contract, cycle, bundle):
    root = Path(project).resolve()
    expected = build_bundle(root, contract, cycle)
    directory = closure.evidence_path(root, bundle)
    for name in ('observation', 'receipt'):
        path = closure.evidence_path(root, (directory.relative_to(root) / (name + '.json')).as_posix())
        require(path.is_file() and path.read_bytes() == encoded(expected[name]),
                'BUNDLE_STALE', 'Incomplete, edited or stale bundle; inspect actual sources instead of replacing history')
    return {'sources_current': True, 'cycle': cycle['cycle'], 'observation_sha256': expected['receipt']['observation_sha256'],
            'reconciliation_executed': False, 'semantic_truth_verified': False, 'promotion_authorized': False}


def preservation_report(project, graph_file, grade_file, results_file):
    """Read-only witness freshness view; never a replacement for native 8.3 check execution."""
    root=Path(project).resolve(strict=True)
    paths=[closure.evidence_path(root,relative) for relative in (graph_file,grade_file,results_file)]
    hashes={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    graph,grades,report=[closure.load_json(path) for path in paths]
    nodes,_,grade,_,_=closure.normalize(graph,grades)
    require(isinstance(report,dict) and set(report)=={'format','run_id','context_sha256','complete','cases'} and
            report['format']=='verimission-results-v1' and report['complete'] is True and isinstance(report['cases'],list),
            'PRESERVATION','Expected a complete neutral witness result')
    json.dumps(report,allow_nan=False)
    groups={}; seen=set()
    for row in report['cases']:
        require(isinstance(row,dict) and text(row.get('id')) and row['id'] not in seen and '::' in row['id'],
                'PRESERVATION','Unique UNIT::witness identifiers required')
        seen.add(row['id']); unit,name=row['id'].split('::',1)
        require(unit in nodes,'PRESERVATION','Witness unit is absent from the declared graph')
        contract=row.get('contract',{})
        require(isinstance(contract,dict) and set(contract)=={'references','witness_sha256','reset_policy'} and text(contract['reset_policy']),
                'PRESERVATION','Reference-bound witness/reset contract required')
        references=contract['references']
        require(isinstance(references,dict) and {'stock','witnesses'}<=set(references), 'PRESERVATION','Stock/corpus references required')
        for ref in references.values():
            require(isinstance(ref,dict) and set(ref)=={'path','sha256'},'PRESERVATION','Expected a physical reference binding')
            path=closure.evidence_path(root,ref['path'])
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            require(actual==ref['sha256'],'PRESERVATION','Witness, stock or context source changed')
            hashes[ref['path']]=actual
        corpus=closure.load_json(closure.evidence_path(root,references['witnesses']['path']))
        require(isinstance(corpus,list),'PRESERVATION','Witness corpus must be a list')
        witness=[case for case in corpus if isinstance(case,dict) and case.get('name')==name]
        require(len(witness)==1 and hashlib.sha256(json.dumps(witness[0],sort_keys=True,allow_nan=False,
                separators=(',',':')).encode()).hexdigest()==contract['witness_sha256'],
                'PRESERVATION','Case is not the declared physical witness')
        groups.setdefault(unit,[]).append(row)
    require(groups,'PRESERVATION','An empty witness view is not preservation evidence')
    units=[]
    for unit,rows in sorted(groups.items()):
        historical=grade.get(unit,'ungraded')
        status='witness_match_observed' if all(r.get('status')=='pass' for r in rows) else 'needs_revalidation'
        if historical=='G4-stock': status='stock_only_no_reconstruction_claim'
        elif historical in {'G0','G4','ungraded'}: status='needs_revalidation'
        units.append({'unit':unit,'historical_grade':historical,'evidence_status':status,
                      'cases':[row['id'] for row in rows]})
    require(all(hashlib.sha256(closure.evidence_path(root,path).read_bytes()).hexdigest()==sha for path,sha in hashes.items()),
            'PRESERVATION','Source changed during freshness view')
    return {'format':'disasm-preservation-view-v1','units':units,'physical_sources':hashes,
            'promotion_authorized':False,'semantic_truth_verified':False,'reconciliation_executed':False,
            'limit':'Declared reference freshness and witness statuses only; use the native 8.3 engine for run binding, preservation gates and audit.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    preservation=commands.add_parser('preservation-report')
    preservation.add_argument('--callgraph',required=True)
    preservation.add_argument('--grades',required=True)
    preservation.add_argument('--results',required=True)
    for name in ('export', 'verify'):
        command = commands.add_parser(name)
        command.add_argument('--contract', required=True)
        command.add_argument('--input', required=True, help='Frozen disasm-cycle-snapshot-v1 JSON')
        command.add_argument('--bundle', required=True, help='Project-relative bundle directory; new for export')
    args = parser.parse_args()
    try:
        root = Path(args.project).resolve()
        if args.command=='preservation-report':
            result=preservation_report(root,args.callgraph,args.grades,args.results)
            print(json.dumps({'ok':True,'result':result},ensure_ascii=True))
            return 0
        contract = closure.load_json(closure.evidence_path(root, args.contract))
        cycle = closure.load_json(closure.evidence_path(root, args.input))
        result = (export_bundle if args.command == 'export' else verify_bundle)(root, contract, cycle, args.bundle)
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=True))
        return 0
    except (AdapterError, OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        code = error.code if isinstance(error, AdapterError) else 'INPUT'
        print(json.dumps({'ok': False, 'code': code, 'error': str(error)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
