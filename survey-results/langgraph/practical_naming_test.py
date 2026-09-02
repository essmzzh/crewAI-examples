import os
# 8 real sites: repo, file, compile_name(static), manifest_key, compiled_var, builder_var, state_cls
S=[
 ("graph_websearch_agent","agent_graph/graph.py",None,None,"workflow","graph","AgentGraphState"),
 ("gemini-fullstack-langgraph-quickstart","backend/src/agent/graph.py","pro-search-agent","agent","graph","builder","OverallState"),
 ("company-research-agent","backend/graph.py",None,"agent","graph","self.workflow","InputState"),
 ("executive-ai-assistant","eaia/cron_graph.py",None,"cron","graph","graph","JobKickoff"),
 ("executive-ai-assistant","eaia/reflection_graphs.py",None,"general_reflection_graph","general_reflection_graph","general_reflection_graph","ReflectionState"),
 ("executive-ai-assistant","eaia/reflection_graphs.py",None,"multi_reflection_graph","multi_reflection_graph","multi_reflection_graph","MultiMemoryInput"),
 ("executive-ai-assistant","eaia/main/graph.py",None,"main","graph","graph_builder","State"),
 ("fastapi-langgraph-agent-production-ready-template","app/core/langgraph/graph.py",None,None,"self._graph","graph_builder","GraphState"),
]
print("RAW SIGNAL VALUES — verbatim, no stripping, no prose\n")
print(f"{'repo/file':56} {'compile(name=)':18} {'manifest':26} {'compiled var':16} {'module stem':14}")
for r,f,cn,mk,cv,bv,st in S:
    print(f"{(r[:26]+'/'+os.path.basename(f)):56} {str(cn):18} {str(mk):26} {cv:16} {os.path.splitext(os.path.basename(f))[0]:14}")

print("\n\nDECLARED-ONLY COVERAGE (the two signals with author intent)")
d=sum(1 for x in S if x[2] or x[3])
print(f"  compile(name=) static : {sum(1 for x in S if x[2])}/8")
print(f"  langgraph.json key    : {sum(1 for x in S if x[3])}/8")
print(f"  either (declared)     : {d}/8   -> {8-d}/8 have NO declared name at all")

print("\n\nOPTION A — declared name, always qualified by repo (no heuristics at all)")
seen={}
for r,f,cn,mk,cv,bv,st in S:
    local = cn or mk
    src = "compile_name" if cn else ("manifest_key" if mk else None)
    if not local:
        local, src = cv.replace("self.",""), "graph_variable"
    key=(r,local)
    if key in seen:
        local=f"{local}@{os.path.splitext(os.path.basename(f))[0]}"; src+="+module"
    seen[key]=1
    print(f"  {r}/{local:28} [{src}]")

print("\n\nOPTION B — same, but unqualified when the declared name is already distinctive")
GENERIC={"agent","graph","main","app","workflow","builder","state","default"}
seen={}
for r,f,cn,mk,cv,bv,st in S:
    local = cn or mk
    src = "compile_name" if cn else ("manifest_key" if mk else None)
    if not local: local,src = cv.replace("self.",""), "graph_variable"
    name = local if local.lower() not in GENERIC and (cn or mk) else f"{r}/{local}"
    key=(r,name)
    if key in seen: name=f"{name}@{os.path.splitext(os.path.basename(f))[0]}"
    seen[key]=1
    print(f"  {name:70} [{src}]")
