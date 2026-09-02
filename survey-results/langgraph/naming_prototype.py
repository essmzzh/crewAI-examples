import ast, os, re
from collections import Counter, defaultdict
REPOS={"graph_websearch_agent":"/workspace/essmzzh/graph_websearch_agent",
 "gemini-fullstack":"/workspace/essmzzh/gemini-fullstack-langgraph-quickstart",
 "company-research-agent":"/workspace/essmzzh/company-research-agent",
 "executive-ai-assistant":"/workspace/langchain-ai/executive-ai-assistant"}
SKIP={".venv","__pycache__",".git","node_modules"}
GENERIC={"run","main","agent","node","call","execute","invoke","process","handler",
         "func","step","start","end","wrapper","fn","graph","workflow","chain","app"}
INFRA={"AIMessage","ToolMessage","HumanMessage","SystemMessage","UUID","Send","Command",
       "ChatOpenAI","ChatAnthropic","ChatGoogleGenerativeAI","ChatVertexAI","AzureChatOpenAI",
       "LLM","Client","Path","Field","BaseModel","Config","RunnableConfig","Ollama"}
NOISE=re.compile(r"^(langgraph\s+node\s+that\s+|node\s+that\s+|this\s+(node|function)\s+)",re.I)
SUFFIX=re.compile(r"(_node|_agent|node|agent|_tool|tool)$",re.I)

def pyf(r):
    for dp,dn,fn in os.walk(r):
        dn[:]=[d for d in dn if d not in SKIP]
        for f in sorted(fn):
            if f.endswith(".py"): yield os.path.join(dp,f)

def titleize(s):
    s=re.sub(r"(?<=[a-z0-9])(?=[A-Z])"," ",s).replace("_"," ")
    return " ".join(w if w.isupper() else w.capitalize() for w in s.split())

def collect():
    rows=[]
    for corpus,root in REPOS.items():
        trees={}
        for p in pyf(root):
            try: trees[os.path.relpath(p,root)]=ast.parse(open(p,"rb").read())
            except Exception: pass
        alldocs={}
        for rel,t in trees.items():
            for nd in ast.walk(t):
                if isinstance(nd,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    d=ast.get_docstring(nd)
                    if d: alldocs.setdefault(nd.name, d.strip().split("\n")[0])
        for rel,t in trees.items():
            funcs={nd.name:nd for nd in ast.walk(t) if isinstance(nd,(ast.FunctionDef,ast.AsyncFunctionDef))}
            imports={}
            for nd in ast.walk(t):
                if isinstance(nd,ast.ImportFrom):
                    for a in nd.names: imports[a.asname or a.name]=nd.module
            for nd in ast.walk(t):
                if not(isinstance(nd,ast.Call) and isinstance(nd.func,ast.Attribute) and nd.func.attr=="add_node"): continue
                a=nd.args
                exp=a[0].value if a and isinstance(a[0],ast.Constant) and isinstance(a[0].value,str) else None
                tgt=a[1] if len(a)>1 else (a[0] if len(a)==1 and not isinstance(a[0],ast.Constant) else None)
                cal=tgt.id if isinstance(tgt,ast.Name) else (tgt.attr if isinstance(tgt,ast.Attribute) else None)
                cls=[]
                body=funcs.get(cal) or (tgt if isinstance(tgt,ast.Lambda) else None)
                if body is not None:
                    for s in ast.walk(body):
                        if isinstance(s,ast.Call):
                            f=s.func; nm=f.id if isinstance(f,ast.Name) else getattr(f,"attr",None)
                            if nm and nm[:1].isupper(): cls.append(nm)
                if isinstance(tgt,ast.Attribute) and isinstance(tgt.value,ast.Attribute):
                    at=tgt.value.attr
                    for s in ast.walk(t):
                        if isinstance(s,ast.Assign):
                            for x in s.targets:
                                if isinstance(x,ast.Attribute) and x.attr==at and isinstance(s.value,ast.Call):
                                    f=s.value.func; nm=f.id if isinstance(f,ast.Name) else getattr(f,"attr",None)
                                    if nm: cls.append(nm)
                doc=None
                if cal in funcs:
                    d=ast.get_docstring(funcs[cal]); doc=d.strip().split("\n")[0] if d else None
                elif cal in alldocs: doc=alldocs[cal]
                rows.append({"corpus":corpus,"file":rel,"line":nd.lineno,"explicit":exp,
                    "callable":cal,"cls":[c for c in dict.fromkeys(cls) if c not in INFRA],
                    "doc":doc,"mod":imports.get(cal),
                    "graph":ast.unparse(nd.func.value)})
    return rows

# ---------- strategies ----------
def s1_declared(r):
    return (titleize(r["explicit"]), "declared node id") if r["explicit"] else (None,None)
def safe_strip(word, siblings):
    """Strip a _node/_agent suffix only if it does not collide with a sibling."""
    stripped = SUFFIX.sub("", word) or word
    if stripped != word and any(s != word and SUFFIX.sub("", s) == stripped for s in siblings):
        return word
    return stripped
def s2_impl(r, siblings=()):
    if r["cls"]:
        return titleize(safe_strip(r["cls"][0], siblings)), "class constructed in node body"
    if r["callable"] and r["callable"].lower() not in GENERIC:
        return titleize(safe_strip(r["callable"], siblings)), "callable identifier"
    return None,None
def s3_doc(r):
    if not r["doc"]: return None,None
    d=NOISE.sub("",r["doc"]).strip().rstrip(".")
    words=d.split()
    if len(words)<2: return None,None
    return " ".join(w if w.isupper() else w.capitalize() for w in words[:5]), "docstring summary"
def s4_context(r):
    parts=[p for p in os.path.dirname(r["file"]).split(os.sep) if p not in ("src","backend","app","")]
    base=os.path.splitext(os.path.basename(r["file"]))[0]
    seed=r["mod"].split(".")[-1] if r["mod"] else (base if base not in ("graph","main") else (parts[-1] if parts else base))
    return titleize(SUFFIX.sub("",seed) or seed), "module/package context"

def gate(name, r, seen_in_graph, global_counts):
    if not name: return False,"empty"
    flat=name.lower().replace(" ","")
    if flat in GENERIC: return False,"generic word"
    if len(flat)<3: return False,"too short"
    if name in seen_in_graph: return False,"duplicate within graph"
    if global_counts[name]>1: return False,"collapses across sites"
    return True,"ok"

rows=collect()
# pre-count each strategy's outputs to detect collapse
SIB=defaultdict(list)
for r in rows: SIB[(r["corpus"],r["graph"])].append(r["callable"] or r["explicit"] or "")
# collapse detection is scoped to the GRAPH, not the whole corpus: two graphs may
# legitimately both have a "reflection" node.
pre=defaultdict(Counter)
for r in rows:
    k=(r["corpus"],r["graph"])
    for i,f in ((1,s1_declared),(2,lambda x:s2_impl(x,SIB[k])),(3,s3_doc),(4,s4_context)):
        nm,_=f(r)
        if nm: pre[(i,k)][nm]+=1

print(f"{'site':46} {'S1 declared':22} {'S2 impl':22} {'S3 doc':26} {'S4 ctx':16} -> CASCADE")
print("-"*172)
seen=defaultdict(set); out=[]
for r in rows:
    key=(r["corpus"],r["graph"])
    cands=[]
    for i,f in ((1,s1_declared),(2,lambda x:s2_impl(x,SIB[key])),(3,s3_doc),(4,s4_context)):
        nm,why=f(r); cands.append((i,nm,why))
    chosen=chosen_why=None
    for i,nm,why in cands:
        ok,reason=gate(nm,r,seen[key],pre[(i,key)])
        if ok: chosen,chosen_why=nm,f"S{i}: {why}"; break
    if not chosen:
        base=cands[0][1] or cands[1][1] or cands[3][1] or "Node"
        chosen=f"{base} ({r['line']})"; chosen_why="S4+disambiguator"
    seen[key].add(chosen)
    out.append((r,chosen,chosen_why))
    site=f"{r['corpus'][:20]}/{os.path.basename(r['file'])}:{r['line']}"
    print(f"{site:46} {str(cands[0][1])[:21]:22} {str(cands[1][1])[:21]:22} {str(cands[2][1])[:25]:26} {str(cands[3][1])[:15]:16} -> {chosen}  [{chosen_why}]")

print()
c=Counter(w.split(":")[0] for _,_,w in out)
print("CASCADE SOURCE:", dict(c))
names=[n for _,n,_ in out]
print(f"UNIQUE NAMES: {len(set(names))}/{len(names)}")
print("GENERIC IN FINAL OUTPUT:", [n for n in names if n.lower().replace(' ','') in GENERIC])
