"""Read-only bridge to current engine authority. Snapshots/grades are never promoted."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

def sibling(name):
    s=importlib.util.spec_from_file_location('qualified_view_'+name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

closure=sibling('closure')

def query(project,harness):
    root=Path(project).resolve(strict=True);script=Path(harness).resolve(strict=True)
    try:
        result=subprocess.run([sys.executable,'-B',str(script),'--project',str(root),'measurement-report'],
            shell=False,capture_output=True,text=True,encoding='utf-8',timeout=120)
    except subprocess.TimeoutExpired:
        raise ValueError('Live measurement query timed out; no fallback to declared grades') from None
    if result.returncode:raise ValueError('Native engine refused current measurement view; no fallback to declared grades')
    value=json.loads(result.stdout)
    if value.get('ok') is not True:raise ValueError('Native engine did not provide a current view')
    return value['result'],hashlib.sha256(script.read_bytes()).hexdigest()

def summarize(callgraph,grades,measurement,graph_reference):
    legacy=sibling('census_bars').summarize(callgraph,grades)
    need=closure.require
    need(isinstance(measurement,dict) and measurement.get('format')=='verimission-measurement-view-v1' and
         measurement.get('applicable') is True and measurement.get('runs_commands') is False,
         'MEASUREMENT','Use the live native measurement policy/view')
    nodes,edges,grade,unknown,_=closure.normalize(callgraph,grades)
    rows=measurement.get('units');need(isinstance(rows,list),'MEASUREMENT','Unit evidence statuses required')
    ids=[u['id'] for u in rows]
    need(len(set(ids))==len(ids) and set(ids)==nodes,'MEASUREMENT','Graph and native universe differ; duplicate rows refused')
    counts=Counter()
    for unit in rows:
        uid=unit['id'];status=unit['status']
        need(status in ('verified','pending','stale','excluded'),'MEASUREMENT','Unknown evidence status')
        counts[status]+=1
        need((status=='excluded')==(grade.get(uid)=='G0'),'MEASUREMENT','Declared G0 differs from fixed approved exclusions')
        if status=='verified':
            need(uid not in unknown and set(edges[uid] or [])==set(unit['depends_on']),
                 'MEASUREMENT','Qualified unit has contradictory/unknown call closure')
            need(unit.get('artifacts',{}).get('callgraph')==graph_reference,'MEASUREMENT','Qualified proof belongs to another graph snapshot')
    actual={s:counts[s] for s in ('verified','pending','stale','excluded')}
    need(all(type(v) is int and v>=0 for v in measurement['counts'].values()) and measurement['counts']==actual,
         'MEASUREMENT','Reported counts do not match individual evidence statuses')
    total=counts['verified']+counts['pending']+counts['stale']
    need(type(measurement.get('denominator')) is int and measurement['denominator']==total and
         measurement.get('inventory_total')==len(nodes),'MEASUREMENT','Native denominator is inconsistent')
    return {'format':'disasm-qualified-census-v1','declared':legacy,'counts':actual,'denominator':total,
            'units':rows,'source':measurement['source'],'live_native_view':True,
            'semantic_truth_verified':False,'grade_promotion_performed':False,'reconciliation_executed':False}
