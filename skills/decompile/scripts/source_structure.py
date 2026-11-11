"""C AST observations for an independent source qualification; no semantic/readability oracle."""
import hashlib
import json
import re

def analyze(preprocessed_source,symbol):
    try:
        from pycparser import c_ast,c_parser
    except ImportError:raise ValueError('C AST adapter requires pycparser; legacy decompile commands do not') from None
    try:tree=c_parser.CParser().parse(preprocessed_source)
    except Exception as error:raise ValueError('C AST unavailable: supply compatible preprocessed C or another reviewed adapter') from error
    functions=[n for n in tree.ext if isinstance(n,c_ast.FuncDef) and n.decl.name==symbol]
    if len(functions)!=1:raise ValueError('Exactly one body for the declared unit symbol is required')
    nodes=[]
    def walk(node):
        nodes.append(node)
        for _,child in node.children():walk(child)
    walk(functions[0])
    declarations=[n for n in nodes if isinstance(n,c_ast.Decl)]
    register_names={n.name for n in declarations if n.name and re.fullmatch(r'r(?:[0-9]|1[0-2])',n.name)}
    pointers={n.name for n in declarations if isinstance(n.type,c_ast.PtrDecl) and isinstance(n.type.type,c_ast.FuncDecl)}
    calls=[n for n in nodes if isinstance(n,c_ast.FuncCall)]
    indirect=[str(n.coord) for n in calls if not isinstance(n.name,c_ast.ID) or n.name.name in pointers]
    direct=sorted({n.name.name for n in calls if isinstance(n.name,c_ast.ID) and n.name.name not in pointers})
    branches=[n for n in nodes if isinstance(n,(c_ast.If,c_ast.For,c_ast.While,c_ast.DoWhile,c_ast.Switch))]
    constant_conditions=sum(isinstance(getattr(n,'cond',None),c_ast.Constant) for n in branches)
    gotos=sum(isinstance(n,c_ast.Goto) for n in nodes)
    signals=[]
    if len(register_names)>=4:signals.append('register_bank')
    if gotos:signals.append('goto_control_flow')
    if constant_conditions:signals.append('constant_condition')
    if indirect:signals.append('indirect_call')
    structure=tree_to_value(functions[0])
    return {'format':'disasm-source-structure-v1','symbol':symbol,'has_body':True,'branches':len(branches),
            'gotos':gotos,'direct_calls':direct,'indirect_calls':indirect,'signals':signals,
            'ast_sha256':hashlib.sha256(json.dumps(structure,sort_keys=True).encode()).hexdigest(),
            'semantic_truth_verified':False,'completion_authorized':False}

def tree_to_value(node):
    return {'type':type(node).__name__,'attributes':{n:getattr(node,n) for n in node.attr_names},
            'children':[(name,tree_to_value(child)) for name,child in node.children()]}
