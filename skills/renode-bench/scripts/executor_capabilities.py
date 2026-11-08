"""Read-only, declared executor-capability eligibility; never starts an emulator or grants authority."""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys


class CapabilityError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def require(condition, code, message):
    if not condition:
        raise CapabilityError(code, message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def digest(value):
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, RecursionError):
        raise CapabilityError('INPUT', 'Manifest must contain finite JSON data') from None
    return hashlib.sha256(raw).hexdigest()


def context_digest(manifest):
    return digest({'target_sha256': manifest['target_sha256'], 'executor': manifest['executor']})


def load_json(path):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'INPUT', 'Duplicate JSON keys refused')
            result[key] = value
        return result
    def invalid(_):
        raise CapabilityError('INPUT', 'Non-finite numbers refused')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs, parse_constant=invalid)


def evidence_path(root, value):
    require(text(value), 'PATH', 'Evidence needs a project-relative path')
    portable = value.replace('\\', '/')
    part, win = Path(portable), PureWindowsPath(value)
    require(not part.is_absolute() and not win.drive and not win.root and '..' not in part.parts and ':' not in portable
            and '.harness' not in {p.casefold() for p in part.parts}, 'PATH', 'Evidence cannot leave the project or use harness state')
    path = (root / part).resolve()
    require(path.is_relative_to(root) and '.harness' not in {p.casefold() for p in path.relative_to(root).parts},
            'PATH', 'Evidence resolves outside the project')
    return path


def assess(project, manifest, requirements):
    root = Path(project).resolve()
    require(root.is_dir(), 'PATH', 'Project root is missing')
    require(isinstance(manifest, dict) and set(manifest) == {'format', 'target_sha256', 'executor', 'capabilities', 'assessment_context_sha256'}
            and manifest['format'] == 'bench-executor-capabilities-v1', 'CAPABILITY', 'Use bench-executor-capabilities-v1')
    require(isinstance(requirements, dict) and set(requirements) == {'format', 'target', 'unit_id', 'required_features'}
            and requirements['format'] == 'bench-requirements-v1' and text(requirements['unit_id']),
            'REQUIREMENTS', 'Use bench-requirements-v1 with a stable unit ID')
    executor = manifest['executor']
    require(isinstance(executor, dict) and set(executor) == {'name', 'version', 'cpu_model', 'configuration'} and
            all(text(executor[key]) for key in ('name', 'version', 'cpu_model')) and isinstance(executor['configuration'], dict),
            'CAPABILITY', 'Declare executor version, CPU model and configuration')
    require(manifest['assessment_context_sha256'] == context_digest(manifest), 'CAPABILITY_STALE',
            'Target or executor context changed; reassess capabilities instead of reusing an old declaration')
    witnesses = []
    def receipt(ref, code):
        require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'} and text(ref['sha256']),
                code, 'Evidence needs path and SHA-256')
        path = evidence_path(root, ref['path'])
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == ref['sha256'], code,
                'A target or capability evidence file is missing or changed')
        witnesses.append((path, ref['sha256']))
        return ref['sha256']
    target_sha = receipt(requirements['target'], 'IDENTITY')
    require(manifest['target_sha256'] == target_sha, 'IDENTITY', 'Executor declaration is for a different binary')
    features = requirements['required_features']
    require(isinstance(features, list) and features and all(text(x) for x in features) and len(set(features)) == len(features),
            'REQUIREMENTS', 'Explicitly declare unique required features; do not assume a pure-logic default')
    capabilities = manifest['capabilities']
    require(isinstance(capabilities, dict) and all(text(x) for x in capabilities), 'CAPABILITY', 'Capabilities must be named records')
    for name, row in capabilities.items():
        require(isinstance(row, dict) and set(row) == {'status', 'reason', 'evidence'} and
                isinstance(row['status'], str) and row['status'] in {'supported', 'unsupported', 'unknown'} and
                text(row['reason']) and isinstance(row['evidence'], list), 'CAPABILITY', 'Each capability needs status, reason and evidence list')
        require(row['status'] != 'supported' or row['evidence'], 'CAPABILITY', 'Supported capabilities need current evidence')
        for ref in row['evidence']:
            receipt(ref, 'CAPABILITY_STALE')
    unsupported = sorted(name for name in features if capabilities.get(name, {}).get('status') == 'unsupported')
    unknown = sorted(name for name in features if capabilities.get(name, {}).get('status', 'unknown') == 'unknown')
    require(all(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == checksum for path, checksum in witnesses),
            'CAPABILITY_STALE', 'An input changed during capability assessment')
    return {'format': 'bench-capability-assessment-v1', 'eligible': not unsupported and not unknown,
            'unit_id': requirements['unit_id'], 'target_sha256': target_sha, 'executor': executor,
            'manifest_sha256': digest(manifest), 'requirements_sha256': digest(requirements),
            'assessment_context_sha256': manifest['assessment_context_sha256'],
            'required_features': features, 'unsupported': unsupported, 'unknown': unknown,
            'reasons': {name: capabilities.get(name, {}).get('reason', 'No capability declared') for name in features},
            'physical_hashes_match': True, 'runtime_capability_authenticated': False,
            'execution_authorized': False, 'automatic_fallback': False,
            'next': 'Manually review eligibility, authority and evidence before invocation or selecting another executor'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    command = parser.add_subparsers(dest='command', required=True).add_parser('assess')
    command.add_argument('--manifest', required=True)
    command.add_argument('--requirements', required=True)
    args = parser.parse_args()
    root = Path(args.project).resolve()
    def supplied(value):
        path = Path(value)
        return path if path.is_absolute() else root / path
    try:
        result = assess(root, load_json(supplied(args.manifest)), load_json(supplied(args.requirements)))
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=True))
        return 0 if result['eligible'] else 2
    except (CapabilityError, OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        code = error.code if isinstance(error, CapabilityError) else 'INPUT'
        print(json.dumps({'ok': False, 'code': code, 'error': str(error)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
