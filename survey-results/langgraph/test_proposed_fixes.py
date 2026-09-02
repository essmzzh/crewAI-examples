import re, os
# (repo, file, state_class)  — all 8 real StateGraph sites
SITES=[
 ("graph_websearch_agent","agent_graph/graph.py","AgentGraphState"),
 ("gemini-fullstack","backend/src/agent/graph.py","OverallState"),
 ("company-research-agent","backend/graph.py","InputState"),
 ("executive-ai-assistant","eaia/cron_graph.py","JobKickoff"),
 ("executive-ai-assistant","eaia/reflection_graphs.py","ReflectionState"),
 ("executive-ai-assistant","eaia/reflection_graphs.py","MultiMemoryInput"),
 ("executive-ai-assistant","eaia/main/graph.py","State"),
 ("fastapi-langgraph-template","app/core/langgraph/graph.py","GraphState"),
]
GENERIC={"agent","graph","main","app","workflow","chain","state","builder","input",
         "output","overall","backend","frontend","src","core","langgraph","entry","default"}

# --- Proposed fix 3: pattern filter "ends in State|Input|Output, or contains Graph"
prop=re.compile(r"(State|Input|Output)$|Graph")
print("PROPOSED STATE-NAME FILTER  (reject if ends State/Input/Output or contains Graph)")
print(f"{'state class':18} {'rejected?':10} {'name if kept':16} verdict")
for _,_,st in SITES:
    rej=bool(prop.search(st))
    kept=re.sub(r"(State|Schema)$","",st) or st
    v=""
    if not rej and kept.lower() in GENERIC: v="LEAK: generic passes"
    elif not rej: v="LEAK: passes through" if st=="JobKickoff" else "passes"
    elif rej and kept.lower() not in GENERIC and st in ("ReflectionState","MultiMemoryInput"):
        v="OVER-FILTER: good name lost"
    else: v="correctly rejected"
    print(f"{st:18} {str(rej):10} {kept:16} {v}")

# --- alternative: strip-then-generic-check
print()
print("ALTERNATIVE  (strip State/Input/Output/Schema/Graph affixes, THEN generic check)")
def strip_then_check(st):
    s=re.sub(r"(State|Schema|Input|Output)$","",st)
    s=re.sub(r"Graph","",s)
    return (s if s and s.lower() not in GENERIC else None)
for _,_,st in SITES:
    print(f"  {st:18} -> {strip_then_check(st)}")

# --- Missing fallback: module file-path stem
print()
print("PROPOSED MODULE-STEM FALLBACK")
seen={}
for repo,f,_ in SITES:
    stem=os.path.splitext(os.path.basename(f))[0]
    cand=re.sub(r"_?graphs?$","",stem) or stem
    if cand.lower() in GENERIC or not cand:
        segs=[p for p in os.path.dirname(f).split("/") if p not in ("src","backend","app","")]
        cand=re.sub(r"_?graphs?$","",segs[-1]) if segs else stem
    ok = bool(cand) and cand.lower() not in GENERIC
    key=(repo,cand)
    dup = key in seen
    seen[key]=1
    print(f"  {repo[:24]:25} {f:34} -> {str(cand):12} {'USABLE' if ok else 'GENERIC — rejected'}"
          + ("   COLLIDES with sibling" if dup and ok else ""))
