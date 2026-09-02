import ast, os, json, re
REPOS={"graph_websearch_agent":"/workspace/essmzzh/graph_websearch_agent",
 "gemini-fullstack-langgraph-quickstart":"/workspace/essmzzh/gemini-fullstack-langgraph-quickstart",
 "company-research-agent":"/workspace/essmzzh/company-research-agent",
 "executive-ai-assistant":"/workspace/langchain-ai/executive-ai-assistant"}
SKIP={".venv","__pycache__",".git","node_modules"}
GENERIC={"agent","graph","main","app","workflow","chain","state","builder","default",
         "my agent","langgraph","backend","frontend","src","entry","run","test"}
STATE_GENERIC={"state","inputstate","overallstate","outputstate","graphstate","agentstate"}
FRAMEWORK_TAIL=re.compile(r"\s*(with|using|in|powered by)?\s*(langgraph|langchain)\s*(quickstart|template|example|demo|starter)?\s*$",re.I)
EMOJI=re.compile("[\U0001F000-\U0001FAFF☀-➿]")

def titleize(s):
    s=re.sub(r"(?<=[a-z0-9])(?=[A-Z])"," ",str(s)).replace("_"," ").replace("-"," ")
    return " ".join(w if w.isupper() else w.capitalize() for w in s.split())
def is_generic(n):
    return (not n) or n.strip().lower() in GENERIC or len(n.strip())<3

def repo_identity(root, name):
    for c in ("README.md","readme.md","Readme.md"):
        p=os.path.join(root,c)
        if os.path.exists(p):
            for line in open(p,errors="replace"):
                if line.startswith("# "):
                    h=EMOJI.sub("",line.strip("# \n")).strip()
                    h=FRAMEWORK_TAIL.sub("",h).strip(" -—:")
                    if h and not is_generic(h): return h,"README H1"
                    break
    pp=os.path.join(root,"pyproject.toml")
    if os.path.exists(pp):
        m=re.search(r'^\s*name\s*=\s*["\']([^"\']+)',open(pp,errors="replace").read(),re.M)
        if m and not is_generic(m.group(1)) and len(m.group(1))>4:
            return titleize(m.group(1)),"pyproject name"
    return titleize(name),"repo directory name"

def collect(corpus, root):
    man={}
    for dp,dn,fn in os.walk(root):
        dn[:]=[d for d in dn if d not in SKIP]
        if "langgraph.json" in fn:
            try:
                j=json.load(open(os.path.join(dp,"langgraph.json")))
                for k,v in (j.get("graphs") or {}).items():
                    man[(os.path.relpath(os.path.join(dp,v.split(":")[0]),root), v.split(":")[1])]=k
            except Exception: pass
    sites=[]
    for dp,dn,fn in os.walk(root):
        dn[:]=[d for d in dn if d not in SKIP]
        for f in sorted(fn):
            if not f.endswith(".py"): continue
            p=os.path.join(dp,f); rel=os.path.relpath(p,root)
            try: t=ast.parse(open(p,"rb").read())
            except Exception: continue
            comp={}
            for n in ast.walk(t):
                if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) \
                   and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=="compile":
                    nm=next((k.value.value for k in n.value.keywords
                             if k.arg=="name" and isinstance(k.value,ast.Constant)),None)
                    comp[ast.unparse(n.value.func.value)]=(ast.unparse(n.targets[0]),nm)
            for n in ast.walk(t):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ("StateGraph","MessageGraph"):
                    bvar=next((ast.unparse(a.targets[0]) for a in ast.walk(t)
                               if isinstance(a,ast.Assign) and a.value is n),None)
                    cvar,cname=comp.get(bvar,(None,None))
                    sites.append({"corpus":corpus,"root":root,"file":rel,"line":n.lineno,
                        "state":ast.unparse(n.args[0]) if n.args else None,
                        "builder":bvar,"compiled":cvar,"compile_name":cname,
                        "manifest":man.get((rel,cvar)) or man.get((rel,bvar)),
                        "manifest_all":man})
    return sites

all_sites=[]
for c,r in REPOS.items(): all_sites+=collect(c,r)

# resolve manifest entries that point at a wrapper module (entry -> class -> graph)
for s in all_sites:
    if s["manifest"]: continue
    for (mfile,mvar),key in s["manifest_all"].items():
        if mfile!=s["file"] and len(s["manifest_all"])==1 and \
           sum(1 for x in all_sites if x["corpus"]==s["corpus"])==1:
            s["manifest"]=key; s["manifest_indirect"]=mfile
            break

chosen_by_repo={}
print(f"{'graph site':52} {'S1 compile':16} {'S2 manifest':14} {'S3 repo identity':30} {'S4 structural':20} -> NAME  [source]")
print("-"*186)
for s in all_sites:
    n_in_repo=sum(1 for x in all_sites if x["corpus"]==s["corpus"])
    ident,ident_src=repo_identity(s["root"],s["corpus"])
    # candidates
    s1=titleize(s["compile_name"]) if s["compile_name"] else None
    s2=titleize(re.sub(r"_?graphs?$","",s["manifest"]) or s["manifest"]) if s["manifest"] else None
    s3=ident
    st=s["state"]
    s4=None
    if st and st.lower() not in STATE_GENERIC: s4=titleize(re.sub(r"State$","",st) or st)
    if not s4:
        base=os.path.splitext(os.path.basename(s["file"]))[0]
        seg=[p for p in os.path.dirname(s["file"]).split(os.sep) if p not in ("src","backend","app","")]
        cand=base if base not in ("graph","main","__init__") else (seg[-1] if seg else base)
        s4=titleize(re.sub(r"_?graphs?$","",cand) or cand)
    # cascade
    chosen=src=None
    for cand,label in ((s1,"S1 compile(name=)"),(s2,"S2 langgraph.json key"),
                       (s3,"S3 repo identity"),(s4,"S4 structural")):
        if cand and not is_generic(cand): chosen,src=cand,label; break
    if not chosen: chosen,src=s4 or "Graph","S4 structural"
    # qualify when the repo has more than one graph
    if n_in_repo>1 and src!="S1 compile(name=)":
        disc=None
        for cand in (s2,s4):
            if cand and not is_generic(cand): disc=cand; break
        if disc: chosen=f"{ident}: {disc}"; src+=f" + repo qualifier ({ident_src})"
    # sibling-collision guard: if qualification could not discriminate, fall to structure
    sib=chosen_by_repo.setdefault(s["corpus"],[])
    if chosen in sib:
        tail=s4 if s4 and not is_generic(s4) else titleize(
            os.path.splitext(os.path.basename(s["file"]))[0])
        chosen=f"{ident}: {tail}"; src+=" + collision guard"
        if chosen in sib:
            chosen=f"{chosen} ({s['line']})"; src+=" + line disambiguator"
    sib.append(chosen)
    site=f"{s['corpus'][:24]}/{s['file']}:{s['line']}"
    print(f"{site:52} {str(s1)[:15]:16} {str(s2)[:13]:14} {str(s3)[:29]:30} {str(s4)[:19]:20} -> {chosen}  [{src}]")
