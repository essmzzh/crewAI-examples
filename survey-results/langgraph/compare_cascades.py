import re, os
GENERIC={"agent","graph","main","app","workflow","chain","state","builder","input",
         "output","overall","backend","frontend","src","core","langgraph","entry","default","lang"}
# site: compile_name(static?), manifest_key, state_class, file, repo_identity, n_graphs_in_repo
S=[
 ("graph_websearch_agent",None,None,"AgentGraphState","agent_graph/graph.py","Custom WebSearch Agent",1),
 ("gemini-fullstack","pro-search-agent","agent","OverallState","backend/src/agent/graph.py","Gemini Fullstack",1),
 ("company-research-agent",None,"agent","InputState","backend/graph.py","Agentic Company Researcher",1),
 ("executive-ai-assistant",None,"cron","JobKickoff","eaia/cron_graph.py","Executive AI Assistant",4),
 ("executive-ai-assistant",None,"general_reflection_graph","ReflectionState","eaia/reflection_graphs.py","Executive AI Assistant",4),
 ("executive-ai-assistant",None,"multi_reflection_graph","MultiMemoryInput","eaia/reflection_graphs.py","Executive AI Assistant",4),
 ("executive-ai-assistant",None,"main","State","eaia/main/graph.py","Executive AI Assistant",4),
 ("fastapi-langgraph-template","<dynamic f-string>",None,"GraphState","app/core/langgraph/graph.py","FastAPI LangGraph Template",1),
]
def ok(n): return bool(n) and n.strip().lower() not in GENERIC and len(n.strip())>2
def title(s): 
    s=re.sub(r"(?<=[a-z0-9])(?=[A-Z])"," ",str(s)).replace("_"," ").replace("-"," ")
    return " ".join(w if w.isupper() else w.capitalize() for w in s.split())
def state_alt(st):
    s=re.sub(r"(State|Schema|Input|Output)$","",st); s=re.sub(r"Graph","",s)
    return s if ok(s) else None
def modstem(f):
    stem=os.path.splitext(os.path.basename(f))[0]
    c=re.sub(r"_?graphs?$","",stem) or stem
    if not ok(c):
        segs=[p for p in os.path.dirname(f).split("/") if p not in ("src","backend","app","")]
        c=re.sub(r"(?<=.)_?graphs?$","",segs[-1]) if segs else stem
    return c if ok(c) else None

print(f"{'site':44} {'YOUR FIXED CASCADE':30} {'+ REPO IDENTITY':34}")
print("-"*112)
a_named=b_named=0; a_seen={}; b_seen={}
for repo,cn,mk,st,f,ident,n in S:
    # A: compile -> manifest -> state(alt filter) -> module stem
    A=None
    for c in ((title(cn) if cn and not cn.startswith("<") else None),
              title(mk) if mk else None, state_alt(st), title(modstem(f)) if modstem(f) else None):
        if ok(c): A=c; break
    if A and (repo,A) in a_seen: A=f"{A} (dup)"
    if A: a_seen[(repo,A)]=1; a_named+=1
    # B: same, but repo identity inserted after manifest; qualifier when n>1
    B=None; src=None
    for c,s_ in (((title(cn) if cn and not cn.startswith("<") else None),"compile"),
                 (title(mk) if mk else None,"manifest"),
                 (ident if n==1 else None,"repo"),
                 (state_alt(st),"state"),(title(modstem(f)) if modstem(f) else None,"module")):
        if ok(c): B=c; src=s_; break
    if B is None and n>1: B=ident; src="repo"
    if n>1 and src!="compile":
        disc=next((c for c in (title(mk) if mk else None, state_alt(st),
                               title(modstem(f)) if modstem(f) else None) if ok(c)),None)
        B=f"{ident}: {re.sub(r' Graphs?$','',disc)}" if disc else ident
    if B and (repo,B) in b_seen: B=f"{B} (dup)"
    if B: b_seen[(repo,B)]=1; b_named+=1
    print(f"{(repo[:22]+'/'+os.path.basename(f))[:43]:44} {str(A):30} {str(B):34}")
print("-"*112)
print(f"{'named':44} {str(a_named)+'/8':30} {str(b_named)+'/8':34}")
print(f"{'generic or missing':44} {str(8-a_named)+'/8':30} {str(8-b_named)+'/8':34}")
