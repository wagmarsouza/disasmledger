"""Declared grades and live engine-qualified evidence must never be conflated."""
import importlib.util
from pathlib import Path
import unittest

def load(name):
    p=Path(__file__).resolve().parents[1]/'scripts'/(name+'.py')
    s=importlib.util.spec_from_file_location('qualified_'+name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def data():
    graph={'format':'decompile-callgraph-v1','graph':{'a':[],'b':[],'c':[]},'unknown_calls':[],'inventory_complete':True}
    grades={'format':'decompile-grades-v1','grades':{'a':'G4-recon','b':'G4-stock','c':'G3'}}
    ref={'path':'graph.json','sha256':'a'*64}
    metric={'format':'verimission-measurement-view-v1','applicable':True,
        'units':[{'id':u,'identity':'id:'+u,'deliverable':u+'.c','status':s,'depends_on':[],
                  'artifacts':{'callgraph':ref}} for u,s in [('a','verified'),('b','pending'),('c','stale')]],
        'counts':{'verified':1,'pending':1,'stale':1,'excluded':0},'denominator':3,'inventory_total':3,
        'source':{'mission_hash':'b'*64,'revision':4,'cycle':1,'check_id':'check'},'runs_commands':False}
    return graph,grades,metric,ref

class QualifiedCensusTests(unittest.TestCase):
    def test_declared_and_verified_pending_stale_are_separate(self):
        g,d,m,ref=data();v=load('qualified_census').summarize(g,d,m,ref)
        self.assertEqual(v['counts'],{'verified':1,'pending':1,'stale':1,'excluded':0})
        self.assertEqual(v['declared']['declared_compiled_or_compared'],2)
        text=load('census_bars').render(v,20,True)
        self.assertIn('Current qualified',text);self.assertIn('Pending',text);self.assertIn('Stale',text)
        self.assertIn('G4-stock',text);self.assertIn('G4-recon',text)
    def test_mismatched_scalar_cannot_inflate_rows(self):
        g,d,m,ref=data();m['counts']['verified']=3
        with self.assertRaises(ValueError):load('qualified_census').summarize(g,d,m,ref)
    def test_g0_edit_cannot_shrink_the_authoritative_denominator(self):
        g,d,m,ref=data();d['grades']['b']='G0'
        with self.assertRaises(ValueError):load('qualified_census').summarize(g,d,m,ref)
    def test_wrong_graph_cannot_borrow_a_verified_unit(self):
        g,d,m,ref=data();ref={'path':'other.json','sha256':'d'*64}
        with self.assertRaises(ValueError):load('qualified_census').summarize(g,d,m,ref)
    def test_unknown_calls_do_not_become_qualified_closure(self):
        g,d,m,ref=data();g['unknown_calls']=['a']
        with self.assertRaises(ValueError):load('qualified_census').summarize(g,d,m,ref)
    def test_duplicate_row_or_different_inventory_refused(self):
        for fault in ('duplicate','missing'):
            g,d,m,ref=data()
            if fault=='duplicate':m['units'].append(m['units'][0])
            else:m['units'].pop()
            with self.subTest(fault=fault),self.assertRaises(ValueError):load('qualified_census').summarize(g,d,m,ref)
    def test_unadopted_policy_is_not_silently_displayed_as_verified(self):
        g,d,m,ref=data();m['applicable']=False
        with self.assertRaises(ValueError):load('qualified_census').summarize(g,d,m,ref)

if __name__=='__main__':unittest.main()
