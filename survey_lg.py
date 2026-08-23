#!/usr/bin/env python3
"""Throwaway static-analysis survey of LangGraph construction sites in a cloned corpus.

Usage:  python survey_lg.py <cohort>:/path/to/repo [<cohort>:/path ...]
        cohort is `original` or `new`; a bare path defaults to `new`.

Writes into the current working directory:
    graph_sites.jsonl        Part A rows — one per graph construction site
    node_attachments.jsonl   Part A rows — one per add_node call
    aggregates.md            the summary tables

Never imports or executes corpus code. Everything is ast.parse on file bytes —
LangGraph repos routinely have side-effecting imports and missing env.
This script is disposable. It shares no code with the adapter.

PART B IS INHERITED VERBATIM from the CrewAI v2 survey (survey_v2.py). The
functions below the "Part B" banner were lifted from that file's source text
unmodified, so the reachability categories and their boundary rulings are
literally identical and the two frameworks' numbers are comparable. The only
edit is the `TARGETS` constant (LangGraph constructors instead of CrewAI's)
and the corresponding basis string.
"""

import ast
import json
import os
import sys
from collections import Counter, defaultdict

# LangGraph construction targets. Feeds classify_call_kind's framework-constructor
# ruling exactly as CrewAI's four names did.
TARGETS = {"StateGraph", "MessageGraph", "create_react_agent"}
KIND_OF = {"StateGraph": "state_graph", "MessageGraph": "message_graph",
           "create_react_agent": "react_agent"}
BUILDER_METHODS = {"add_node", "add_edge", "add_conditional_edges",
                   "set_entry_point", "set_finish_point", "compile"}

SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", "site-packages",
             ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
             ".eggs", "env", "survey-results"}

UNIT_MARKERS = ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "poetry.lock")
SINGLE_UNIT = "."

SCOPE_BARRIERS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef,
                  ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
DESCEND_BODIES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
LIST_PARENTS = (ast.List, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


# ==========================================================================
# Part B — INHERITED VERBATIM from survey_v2.py. Do not edit.
# ==========================================================================

_RUNTIME_CALLS = {"getenv", "environ.get", "open", "input", "getcwd", "cwd",
                  "loads", "load", "read", "urlopen", "get", "post", "request"}
_RUNTIME_MODULES = ("requests.", "httpx.", "urllib.", "socket.", "aiohttp.")


def _subdirs(path):
    try:
        entries = sorted(os.listdir(path))
    except OSError:
        return []
    out = []
    for e in entries:
        if e in SKIP_DIRS or e.startswith("."):
            continue
        if os.path.isdir(os.path.join(path, e)):
            out.append(e)
    return out


def _files(path):
    try:
        return [e for e in os.listdir(path) if os.path.isfile(os.path.join(path, e))]
    except OSError:
        return []


def discover_repo_units(root, max_depth=3):
    """Return repo-unit paths relative to root, deepest-first for prefix matching.

    The spec assumes a corpus of repos flat under the root. This corpus is a single
    repo whose first level is category folders (crews/, flows/, ...), so a literal
    "first path component" reading yields four meaningless rows. Rule used instead:
    a directory is a unit if it holds a packaging manifest or .py files of its own;
    otherwise descend into its children, capped at max_depth. `repo_top` on every
    row preserves the literal first-component reading.
    """
    # A root that is itself a packaged project is one unit, not a corpus. Splitting
    # such a repo on its top-level directories invents "repos" out of tests/, ui/,
    # api/ and then reports most of them as invisible, which is an artefact.
    if any(m in _files(root) for m in UNIT_MARKERS):
        return [SINGLE_UNIT]

    units = []

    def visit(rel, depth):
        abspath = os.path.join(root, rel) if rel else root
        files = _files(abspath)
        has_marker = any(m in files for m in UNIT_MARKERS)
        has_code = any(f.endswith((".py", ".ipynb")) for f in files)
        kids = _subdirs(abspath)
        if rel and (has_marker or has_code or depth >= max_depth or not kids):
            units.append(rel)
            return
        for k in kids:
            visit(os.path.join(rel, k) if rel else k, depth + 1)

    visit("", 0)
    units.sort(key=lambda p: (-p.count(os.sep), p))
    return units


def repo_for(relpath, units):
    if units == [SINGLE_UNIT]:
        return SINGLE_UNIT
    for u in units:
        if relpath == u or relpath.startswith(u + os.sep):
            return u
    return relpath.split(os.sep)[0] if os.sep in relpath else "."


def iter_py_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                full = os.path.join(dirpath, fn)
                if os.path.abspath(full) == os.path.abspath(__file__):
                    continue  # do not survey the surveyor
                yield full


def is_test_path(relpath):
    parts = relpath.split(os.sep)
    base = parts[-1]
    return (base.startswith("test_") or base.endswith("_test.py")
            or any(p in ("tests", "test", "examples", "example") for p in parts[:-1]))


def unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparse-failed>"


def enclosing(node, parents):
    func = cls = None
    cur = parents.get(node)
    chain = []
    while cur is not None:
        chain.append(cur)
        if func is None and isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func = cur
        if cls is None and isinstance(cur, ast.ClassDef):
            cls = cur
        cur = parents.get(cur)
    return func, cls, chain


def _record_target(store, target, rhs, multi):
    if isinstance(target, ast.Name):
        if target.id in store:
            multi.add(target.id)
        store[target.id] = rhs  # branch flattening: last assignment wins
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _record_target(store, elt, rhs, multi)


def collect_assignments(body, descend):
    """Map name -> RHS node over `body`. If descend, walk into control-flow bodies
    but never into nested function/class/comprehension scopes."""
    store, multi = {}, set()

    def walk_stmts(stmts):
        for st in stmts:
            if isinstance(st, ast.Assign):
                for t in st.targets:
                    _record_target(store, t, st.value, multi)
            elif isinstance(st, ast.AnnAssign):
                if st.value is not None:
                    _record_target(store, st.target, st.value, multi)
            elif descend and isinstance(st, DESCEND_BODIES):
                for field in ("body", "orelse", "finalbody"):
                    walk_stmts(getattr(st, field, []) or [])
                for handler in getattr(st, "handlers", []) or []:
                    walk_stmts(handler.body)
            elif isinstance(st, SCOPE_BARRIERS):
                continue

    walk_stmts(body)
    return store, multi


def collect_params(funcnode):
    if funcnode is None:
        return set()
    a = funcnode.args
    names = set()
    for group in (a.posonlyargs, a.args, a.kwonlyargs):
        for arg in group or []:
            names.add(arg.arg)
    if a.vararg:
        names.add(a.vararg.arg)
    if a.kwarg:
        names.add(a.kwarg.arg)
    return names


def collect_self_attrs(classnode):
    """attr -> (rhs node, assigned_in_init, owning method) for every method.

    The owning method is carried so v2 can take one visible hop: `self.x = param`
    means the value is bound at the *caller's* call site, not here."""
    out = {}
    if classnode is None:
        return out
    for st in classnode.body:
        if not isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        in_init = st.name == "__init__"
        for sub in ast.walk(st):
            targets = []
            if isinstance(sub, ast.Assign):
                targets = [(t, sub.value) for t in sub.targets]
            elif isinstance(sub, ast.AnnAssign) and sub.value is not None:
                targets = [(sub.target, sub.value)]
            for t, rhs in targets:
                if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                        and t.value.id == "self"):
                    prev = out.get(t.attr)
                    out[t.attr] = (rhs, in_init or (prev[1] if prev else False), st)
    return out


def collect_module_defs(tree):
    """Names bound by `def`/`async def` and by `class` anywhere in the module.

    Nested defs count: a factory does not have to be top-level to be followable.
    Kept per-module — cross-module observation would invent confidence the
    survey has not earned.
    """
    funcs, classes = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.add(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
    return funcs, classes


def callee_name(call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def classify_call_kind(call, module_funcs, module_classes, import_origin):
    """v2 Change 1. Returns (ref_call_kind, callee, basis).

    `factory_call` is reserved for the spec's definition — a callee matching a
    `def` in *this* module, i.e. one the survey could actually follow. A callee
    imported from elsewhere is never called a factory even when it is function-
    shaped: an inflated factory count would misdirect the prioritisation, so
    those are `call_unknown` with the naming evidence recorded.

    Imported CamelCase callees are `terminal_constructor` on PEP 8 convention
    plus observed import provenance (e.g. `Ollama` from `langchain.llms`). That
    is evidence, not a guess: the import statement names the origin.
    """
    name = callee_name(call)
    if name is None:
        return "call_unknown", None, "callee is not a plain name"
    if name in module_funcs:
        return "factory_call", name, "matches a def in this module"
    if name in module_classes:
        return "terminal_constructor", name, "matches a class in this module"
    if name in TARGETS:
        return "terminal_constructor", name, "framework constructor"
    if name in import_origin:
        src = import_origin[name]
        if name[:1].isupper():
            return "terminal_constructor", name, f"imported from `{src}`, class by PEP 8 naming"
        return "call_unknown", name, (f"imported from `{src}`, function-shaped — "
                                      "cross-module, not followed (latent factory)")
    return "call_unknown", name, "callee neither defined nor imported in this module"


def runtime_evidence(node):
    """Evidence string if *node itself* is execution-time data, else None.

    Deliberately shallow: this asks whether the value IS runtime data, not
    whether it merely contains a runtime sub-expression. `Ollama(model=os.environ['M'])`
    is a terminal constructor whose argument happens to be runtime — the object is
    statically identified, so it is NOT runtime_external. Over-claiming here would
    understate the addressable bucket, which is the error we cannot afford.
    """
    if isinstance(node, ast.Subscript):
        base = unparse(node.value)
        if base in ("os.environ", "environ"):
            return unparse(node)
    if isinstance(node, ast.Call):
        f = unparse(node.func)
        tail = f.split(".")[-1]
        if f in ("os.getenv", "getenv", "os.environ.get", "environ.get"):
            return unparse(node)
        if tail in ("open", "input") and f in ("open", "input", "io.open"):
            return unparse(node)
        if any(f.startswith(m) for m in _RUNTIME_MODULES):
            return unparse(node)
        if tail == "read" and isinstance(node.func, ast.Attribute):
            return unparse(node)
    if isinstance(node, ast.Attribute) and unparse(node) in ("os.environ",):
        return unparse(node)
    return None


def factory_terminus(name, func_nodes, depth=0):
    """Follow a same-module factory to see what it actually yields.

    Answers the question the factory_call bucket exists to ask: if a resolver
    followed this call, would it find a value or a runtime dependency? Bounded
    to 3 hops, same module only.

    A returned *name* is resolved against the function's own locals first —
    `value = os.getenv(v); return value` is a runtime terminus, and treating it
    as static would be the exact over-claim that inflates the reachable count.
    """
    fn = func_nodes.get(name)
    if fn is None or depth > 2:
        return "unknown", None
    local_assigns, _ = collect_assignments(fn.body, descend=True)
    for node in ast.walk(fn):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        expr = node.value
        # one visible hop: a returned bare name resolves to its local binding
        if isinstance(expr, ast.Name) and expr.id in local_assigns:
            expr = local_assigns[expr.id]
        for sub in ast.walk(expr):
            ev = runtime_evidence(sub)
            if ev:
                return "runtime_external", ev
            if isinstance(sub, ast.Call):
                inner = callee_name(sub)
                if inner and inner != name and inner in func_nodes:
                    kind, ev2 = factory_terminus(inner, func_nodes, depth + 1)
                    if kind == "runtime_external":
                        return kind, ev2
        return "static", unparse(expr)[:80]
    return "unknown", None


def classify_ref(value, funcnode, clsnode, module_assigns, imported_names,
                 local_cache, class_cache, self_cache,
                 module_defs=(frozenset(), frozenset()), import_origin=None):
    """Pass B (v2). Returns dict of ref_* fields (empty for non-reference values).

    v2 changes: `argument_passed` scope (Change 2), `runtime_external` /
    `unresolved_local` split (Change 3), and `ref_call_kind` on Call-valued
    RHS (Change 1).
    """
    module_funcs, module_classes = module_defs
    import_origin = import_origin or {}
    out = {"ref_scope": None, "ref_target_unparsed": None, "ref_target_type": None,
           "ref_call_kind": None, "ref_call_callee": None, "ref_call_basis": None,
           "ref_scope_base": None, "ref_runtime_evidence": None, "ref_next_hop": None}

    def settle(scope, rhs=None, **extra):
        out.update(ref_scope=scope, **extra)
        if rhs is None:
            return out
        out["ref_target_unparsed"] = unparse(rhs)
        out["ref_target_type"] = type(rhs).__name__
        # Change 1 — split the Call case
        if isinstance(rhs, ast.Call):
            kind, callee, basis = classify_call_kind(rhs, module_funcs,
                                                     module_classes, import_origin)
            out.update(ref_call_kind=kind, ref_call_callee=callee, ref_call_basis=basis)
        # Change 3 — a binding whose RHS *is* runtime data is terminally unreachable
        ev = runtime_evidence(rhs)
        if ev:
            out["ref_scope_base"] = scope
            out["ref_scope"] = "runtime_external"
            out["ref_runtime_evidence"] = ev
        # one visible hop: RHS is a bare name that is itself a parameter
        elif isinstance(rhs, ast.Name) and funcnode is not None \
                and rhs.id in collect_params(funcnode):
            out["ref_next_hop"] = "argument_passed"
        return out

    if isinstance(value, ast.Name):
        name = value.id
        locals_, local_multi = local_cache
        if funcnode is not None and name in locals_:
            if name in local_multi:
                out["ref_multiple_assignments"] = True
            return settle("local", locals_[name])
        class_assigns, class_multi = class_cache
        if clsnode is not None and name in class_assigns:
            return settle("class_attr", class_assigns[name])
        mod_assigns, mod_multi = module_assigns
        if name in mod_assigns:
            if name in mod_multi:
                out["ref_multiple_assignments"] = True
            return settle("module", mod_assigns[name])
        if name in imported_names:
            # Cross-module: the survey does not follow imports. Addressable, not
            # impossible — reported inside unresolved_local in the reachability table.
            return settle("imported")
        # Change 2 — parameter of the enclosing function, bound at the call site.
        # Checked after the four lexical scopes, per the v2 spec's ordering.
        if funcnode is not None and name in collect_params(funcnode):
            return settle("argument_passed")
        # Change 3 — not provably runtime, so addressable
        return settle("unresolved_local")

    if isinstance(value, ast.Attribute):
        if isinstance(value.value, ast.Name) and value.value.id == "self":
            hit = self_cache.get(value.attr)
            if hit is not None:
                rhs, in_init, owner = hit
                res = settle("self_attr", rhs,
                             ref_binding_site="__init__" if in_init else "method")
                # one visible hop: self.x = <param of the method that assigned it>
                if isinstance(rhs, ast.Name) and owner is not None \
                        and rhs.id in collect_params(owner):
                    res["ref_next_hop"] = "argument_passed"
                return res
            # `self.x` also resolves against class-body assignments — the @CrewBase
            # `llm = ChatOpenAI(...)` shape.
            class_assigns, _ = class_cache
            if clsnode is not None and value.attr in class_assigns:
                return settle("self_attr", class_assigns[value.attr],
                              ref_binding_site="class_body")
            return settle("unresolved_local")
        return settle("namespace_attr")

    return out


def pct(n, d):
    return "0.0%" if not d else f"{100.0 * n / d:.1f}%"


def table(out, headers, rows):
    out.append("| " + " | ".join(headers) + " |")
    out.append("|" + "|".join("---" for _ in headers) + "|")
    for r in rows:
        cells = ["" if c is None else str(c).replace("|", "\\|").replace("\n", "\\n")
                 for c in r]
        out.append("| " + " | ".join(cells) + " |")
    out.append("")


# ==========================================================================
# Part A — REBUILT for LangGraph. A graph is assembled imperatively, so the
# unit of detection is a construction site plus the node calls bound to it.
# ==========================================================================

def langgraph_module(mod):
    """Accept any module path starting with langgraph; the observed path is recorded."""
    return mod == "langgraph" or mod.startswith("langgraph.")


def build_import_map(tree):
    """direct: local name -> (symbol, module path);  modules: local alias -> module path.

    Same shape as the CrewAI survey's: handles `from langgraph.graph import StateGraph`,
    `... as SG`, and `import langgraph` + `langgraph.graph.StateGraph(...)`. All
    Import nodes are walked, not only top-level ones.
    """
    direct, modules, bound_names, origin, lookalikes = {}, {}, set(), {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                bound_names.add(local)
                origin[local] = alias.name
                if langgraph_module(alias.name):
                    modules[alias.asname or alias.name] = alias.name
                    if not alias.asname:
                        head = alias.name.split(".")[0]
                        modules[head] = head
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level:
                mod = "." * node.level + mod
            for alias in node.names:
                local = alias.asname or alias.name
                bound_names.add(local)
                origin[local] = mod
                if langgraph_module(mod) and alias.name in TARGETS:
                    direct[local] = (alias.name, mod)
                elif alias.name in TARGETS:
                    # Same name, different package — e.g. create_react_agent from
                    # langchain.agents.react.agent, which is NOT LangGraph's prebuilt.
                    # A name-only matcher would count this as a LangGraph site.
                    lookalikes[local] = (alias.name, mod)
    return direct, modules, bound_names, origin, lookalikes


def match_graph_callee(func, direct, modules):
    """Return (symbol, callee_form, import_path) for a graph construction call."""
    if isinstance(func, ast.Name) and func.id in direct:
        sym, mod = direct[func.id]
        return sym, "Name", mod
    if isinstance(func, ast.Attribute) and func.attr in TARGETS:
        base = func.value
        if isinstance(base, ast.Name) and base.id in modules:
            return func.attr, "Attribute", modules[base.id]
        base_text = unparse(base)
        if base_text.split(".")[0] in modules and langgraph_module(base_text):
            return func.attr, "Attribute", base_text
    return None


def builder_of(parent):
    """The variable a graph is assigned to, and the expression node calls use.

    `workflow = StateGraph(...)`      -> ("workflow", "workflow")
    `self.workflow = StateGraph(...)` -> ("workflow", "self.workflow")
    """
    if not isinstance(parent, ast.Assign) or len(parent.targets) != 1:
        return None, None
    t = parent.targets[0]
    if isinstance(t, ast.Name):
        return t.id, t.id
    if isinstance(t, ast.Attribute):
        return t.attr, unparse(t)
    return None, None


def scope_distance(g_func, g_cls, n_func, n_cls):
    """Part A measurement 4 — how far a node call sits from its graph assignment."""
    if g_func is not None and g_func is n_func:
        return "same_method" if g_cls is not None else "same_function"
    if g_func is None and n_func is None:
        return "module_level"
    if g_cls is not None and g_cls is n_cls and g_func is not n_func:
        return "cross_method_same_class"
    return "other"


def scan_file(path, root, units, stats, corpus, cohort):
    rel = os.path.relpath(path, root)
    try:
        src = open(path, "rb").read()
    except OSError as exc:
        stats["read_failures"].append((rel, str(exc)))
        return [], []
    try:
        tree = ast.parse(src, filename=path)
    except (SyntaxError, ValueError) as exc:
        stats["parse_failures"].append((rel, f"{type(exc).__name__}: {exc}"))
        return [], []
    src_text = src.decode("utf-8", errors="replace")

    direct, modules, imported_names, import_origin, lookalikes = build_import_map(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in lookalikes:
            sym, mod = lookalikes[node.func.id]
            stats["lookalike_sites"].append(
                {"corpus": corpus, "file": rel, "line": node.lineno,
                 "symbol": sym, "import_path": mod})
    if not direct and not modules:
        return [], []

    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    module_assigns = collect_assignments(tree.body, descend=True)
    module_defs = collect_module_defs(tree)
    func_nodes = {n.name: n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    local_caches, class_caches, self_caches = {}, {}, {}

    def caches_for(funcnode, clsnode):
        if funcnode is not None and id(funcnode) not in local_caches:
            local_caches[id(funcnode)] = collect_assignments(funcnode.body, descend=True)
        if clsnode is not None and id(clsnode) not in class_caches:
            class_caches[id(clsnode)] = collect_assignments(clsnode.body, descend=False)
            self_caches[id(clsnode)] = collect_self_attrs(clsnode)
        return (local_caches.get(id(funcnode), ({}, set())),
                class_caches.get(id(clsnode), ({}, set())),
                self_caches.get(id(clsnode), {}))

    def part_b(value, funcnode, clsnode):
        lc, cc, sc = caches_for(funcnode, clsnode)
        d = classify_ref(value, funcnode, clsnode, module_assigns, imported_names,
                         lc, cc, sc, module_defs, import_origin)
        # Supplementary, NOT part of the inherited contract: the inherited `module`
        # scope is assignment-only, so a name bound by a module-level `def`/`class`
        # falls to unresolved_local. In CrewAI that never arose; in LangGraph it is
        # the dominant node-target shape. Recorded separately so the verbatim
        # numbers stay comparable and the gap is still visible.
        if isinstance(value, ast.Name):
            d["ref_module_def"] = value.id in module_defs[0] or value.id in module_defs[1]
        else:
            d["ref_module_def"] = False
        # Supplementary: for a dotted target like `self.ground.run`, the inherited
        # rule is namespace_attr (base is not literally `self`). Classify the base
        # too, so "one level deeper" reachability is measurable without changing
        # the inherited category.
        d["ref_base_scope"] = d["ref_base_target"] = None
        if isinstance(value, ast.Attribute) and not (
                isinstance(value.value, ast.Name) and value.value.id == "self"):
            b = classify_ref(value.value, funcnode, clsnode, module_assigns,
                             imported_names, lc, cc, sc, module_defs, import_origin)
            d["ref_base_scope"] = b.get("ref_scope")
            d["ref_base_target"] = b.get("ref_target_unparsed")
        # Supplementary: a Lambda target has no reference at all — the work is inline.
        # Record the constructors called inside it, which is where the agent lives.
        if isinstance(value, ast.Lambda):
            d["lambda_callees"] = sorted({callee_name(c) for c in ast.walk(value.body)
                                          if isinstance(c, ast.Call) and callee_name(c)})
        return d

    graphs, nodes = [], []
    by_expr = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        m = match_graph_callee(node.func, direct, modules)
        if m is None:
            continue
        symbol, callee_form, import_path = m
        funcnode, clsnode, _ = enclosing(node, parents)
        parent = parents.get(node)
        var, expr = builder_of(parent)

        row = {
            "corpus": corpus, "cohort": cohort, "repo": repo_for(rel, units),
            "file": rel, "line": node.lineno, "is_test": is_test_path(rel),
            "kind": KIND_OF.get(symbol, symbol.lower()),
            "callee_form": callee_form, "callee_text": unparse(node.func),
            "import_path": import_path,
            "builder_var": var, "builder_expr": expr,
            "enclosing_func": funcnode.name if funcnode else None,
            "enclosing_class": clsnode.name if clsnode else None,
            "positional_args": [unparse(a) for a in node.args],
            "kwarg_names": sorted(k.arg for k in node.keywords if k.arg),
            "node_count": 0, "edge_count": 0, "cond_edge_count": 0,
            "react_bindings": {},
        }
        # Part A measurement 7 — react-agent asset bindings on the same footing
        if row["kind"] == "react_agent":
            for kw in node.keywords:
                if kw.arg in ("model", "llm", "tools"):
                    entry = {"node_type": type(kw.value).__name__,
                             "unparsed": unparse(kw.value)}
                    entry.update(part_b(kw.value, funcnode, clsnode))
                    row["react_bindings"][kw.arg] = entry
        graphs.append(row)
        if expr:
            by_expr.setdefault(expr, []).append((row, funcnode, clsnode))

    # associate builder-method calls to their graph by the base expression
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in BUILDER_METHODS):
            continue
        base = unparse(node.func.value)
        if base not in by_expr:
            continue
        grow, gfunc, gcls = by_expr[base][-1]
        method = node.func.attr
        if method == "add_edge":
            grow["edge_count"] += 1
            continue
        if method == "add_conditional_edges":
            grow["cond_edge_count"] += 1
            continue
        if method != "add_node":
            continue
        grow["node_count"] += 1
        nfunc, ncls, _ = enclosing(node, parents)
        # LangGraph accepts BOTH add_node(name, target) and add_node(callable),
        # the latter inferring the node name from the callable's __name__. The
        # one-arg form is 40% of this corpus; assuming two args drops its target.
        name_arg = target = None
        if len(node.args) >= 2:
            name_arg, target = node.args[0], node.args[1]
        elif len(node.args) == 1:
            only = node.args[0]
            if isinstance(only, ast.Constant) and isinstance(only.value, str):
                name_arg = only
            else:
                target = only
        if target is None:
            for kw in node.keywords:
                if kw.arg in ("action", "node", "func", "runnable"):
                    target = kw.value
                    break
        if isinstance(name_arg, ast.Constant) and isinstance(name_arg.value, str):
            node_name, node_name_source = name_arg.value, "explicit"
        elif isinstance(target, ast.Name):
            node_name, node_name_source = target.id, "inferred_from_callable"
        elif isinstance(target, ast.Attribute):
            node_name, node_name_source = target.attr, "inferred_from_callable"
        else:
            node_name, node_name_source = None, None
        nrow = {
            "corpus": corpus, "cohort": cohort, "repo": repo_for(rel, units),
            "file": rel, "line": node.lineno, "is_test": is_test_path(rel),
            "graph_file": grow["file"], "graph_line": grow["line"],
            "graph_kind": grow["kind"], "builder_expr": base,
            "node_name": node_name, "node_name_source": node_name_source,
            "node_target_unparsed": unparse(target) if target is not None else None,
            "node_target_type": type(target).__name__ if target is not None else None,
            "scope_distance": scope_distance(gfunc, gcls, nfunc, ncls),
            "enclosing_func": nfunc.name if nfunc else None,
            "enclosing_class": ncls.name if ncls else None,
        }
        if target is not None:
            nrow.update(part_b(target, nfunc, ncls))
        nodes.append(nrow)

    return graphs, nodes


# ==========================================================================
# aggregates
# ==========================================================================

def ex_rows(items, key, buckets, cols, limit=3):
    out = []
    grouped = defaultdict(list)
    for it in items:
        grouped[it.get(key)].append(it)
    for b in buckets:
        for it in grouped.get(b, [])[:limit]:
            out.append([b, f"{it['corpus']}/{it['file']}:{it['line']}"] + [
                (f"`{it[c]}`" if it.get(c) is not None else "—") for c in cols])
    return out


def write_aggregates(graphs, nodes, dialects, stats, label, path="aggregates.md"):
    o = []
    cohorts = sorted({g["cohort"] for g in graphs} | {"original", "new"})
    o.append("# LangGraph corpus survey — aggregates")
    o.append("")
    o.append(f"Corpora scanned in this run: `{label}`")
    o.append("")
    o.append("**Part B is inherited verbatim** from the CrewAI v2 survey — same category "
             "set, same boundary rulings (class-body `self.x`; value-level-only "
             "`runtime_external`). Reachability numbers here are directly comparable to "
             "the CrewAI `llm=` table. **Part A is rebuilt**: a LangGraph graph is "
             "assembled imperatively, so the unit is a construction site plus the "
             "`add_node` calls bound to its builder variable.")
    o.append("")

    # 1 totals
    o.append("## 1. Totals")
    o.append("")
    kinds = Counter(g["kind"] for g in graphs)
    table(o, ["Metric", "Count"], [
        ["Repos scanned", len({g['corpus'] for g in dialects})],
        [".py files scanned", stats["py_files"]],
        [".ipynb present (not parsed)", stats["ipynb_files"]],
        ["Parse failures", len(stats["parse_failures"])],
        ["Read failures", len(stats["read_failures"])],
        ["Files importing langgraph symbols", stats["files_with_binding"]],
        ["Graph construction sites", len(graphs)],
        ["  of which `state_graph`", kinds.get("state_graph", 0)],
        ["  of which `message_graph`", kinds.get("message_graph", 0)],
        ["  of which `react_agent`", kinds.get("react_agent", 0)],
        ["`add_node` attachments", len(nodes)],
        ["`add_edge` calls", sum(g["edge_count"] for g in graphs)],
        ["`add_conditional_edges` calls", sum(g["cond_edge_count"] for g in graphs)],
    ])
    if stats["parse_failures"]:
        o.append("Parse failures:")
        o.append("")
        table(o, ["File", "Error"], [[p, e] for p, e in stats["parse_failures"]])
    else:
        o.append("No parse failures.")
        o.append("")

    # 2 raw vs react
    o.append("## 2. Raw-graph API vs `create_react_agent` — the dialect split")
    o.append("")
    raw = kinds.get("state_graph", 0) + kinds.get("message_graph", 0)
    react = kinds.get("react_agent", 0)
    tot = raw + react
    table(o, ["API", "Sites", "% of graph sites"],
          [["raw graph (`StateGraph` / `MessageGraph`)", raw, pct(raw, tot)],
           ["prebuilt (`create_react_agent`)", react, pct(react, tot)]])
    o.append("This is the LangGraph analog of a config dialect: it decides how much of "
             "the ecosystem each detection path covers. A scanner that only recognises "
             f"`create_react_agent` would see {pct(react, tot)} of this corpus.")
    o.append("")

    la = stats.get("lookalike_sites", [])
    if la:
        o.append("**Lookalike callees — same name, different package.** These call a "
                 "name in the target set but the binding does not come from `langgraph.*`, "
                 "so they are correctly excluded. A name-only matcher would count them "
                 "as LangGraph sites and be wrong:")
        o.append("")
        table(o, ["Site", "Callee", "Actually imported from"],
              [[f"{x['corpus']}/{x['file']}:{x['line']}", f"`{x['symbol']}`",
                f"`{x['import_path']}`"] for x in la])
    o.append("")

    # 3 node-target reachability — the comparable table
    o.append("## 3. Node-target reachability (inherited Part-B categories)")
    o.append("")
    o.append("The `add_node` second argument, classified by the inherited resolver "
             "taxonomy. Directly comparable to CrewAI's `llm=` reachability table.")
    o.append("")
    def reach(d):
        s = d.get("ref_scope")
        if not s:
            return None
        if d.get("ref_call_kind") and s != "runtime_external":
            return d["ref_call_kind"]
        return s
    rc = Counter()
    for n in nodes:
        c = reach(n)
        rc[c if c else f"(not a reference — {n['node_target_type']})"] += 1
    table(o, ["Reachability", "Count", "% of nodes"],
          [[f"`{k}`", v, pct(v, len(nodes))] for k, v in rc.most_common()])
    md = sum(1 for n in nodes if n.get("ref_module_def"))
    if md:
        o.append(f"**Boundary note — {md} of {len(nodes)} node targets are names bound by "
                 f"a module-level `def`/`class` in the same file.** The inherited `module` "
                 f"scope is assignment-only (`Assign`/`AnnAssign`), so these classify as "
                 f"`unresolved_local` under the verbatim contract. In CrewAI this case "
                 f"never arose — kwarg values were never bare function names. It is "
                 f"recorded in `ref_module_def` rather than silently reclassified, so the "
                 f"cross-framework numbers stay comparable; **corrected, these are "
                 f"trivially resolvable and the addressable bucket shrinks accordingly.**")
        o.append("")
    base = Counter(n.get("ref_base_scope") for n in nodes if n.get("ref_base_scope"))
    if base:
        o.append("**One level deeper.** For dotted targets (`self.ground.run`) the "
                 "inherited rule is `namespace_attr` because the base is not literally "
                 "`self`. Classifying the *base* expression shows how much a "
                 "one-attribute-deeper resolver would reach:")
        o.append("")
        table(o, ["Base scope", "Count", "Example base resolves to"],
              [[f"`{k}`", v, "`" + (next(n["ref_base_target"] for n in nodes
                                         if n.get("ref_base_scope") == k
                                         and n.get("ref_base_target")) or "")[:44] + "`"
                if any(n.get("ref_base_target") for n in nodes
                       if n.get("ref_base_scope") == k) else "—"]
               for k, v in base.most_common()])
    lam = [n for n in nodes if n.get("lambda_callees")]
    if lam:
        o.append(f"**Inline lambdas.** {len(lam)} node targets are lambdas — no reference "
                 f"to resolve, because the work is written inline. The constructors called "
                 f"inside them are where the agent actually lives:")
        o.append("")
        cc2 = Counter(c for n in lam for c in n["lambda_callees"])
        table(o, ["Callee inside lambda", "Occurrences"],
              [[f"`{k}`", v] for k, v in cc2.most_common(12)])
    o.append("Node-target node types (what the second argument syntactically is):")
    o.append("")
    tt = Counter(n["node_target_type"] for n in nodes)
    table(o, ["AST node type", "Count", "% of nodes"],
          [[f"`{k}`", v, pct(v, len(nodes))] for k, v in tt.most_common()])
    o.append("Examples (`file:line`):")
    o.append("")
    table(o, ["Reachability", "Site", "Node name", "Target"],
          [[r, s, a, b] for r, s, a, b in
           [(reach(n) or f"(not a reference — {n['node_target_type']})",
             f"{n['corpus']}/{n['file']}:{n['line']}",
             f"`{n['node_name']}`" if n["node_name"] else "—",
             f"`{(n['node_target_unparsed'] or '')[:60]}`") for n in nodes]][:12])

    # 4 scope distance
    o.append("## 4. Scope distance from `StateGraph` assignment to `add_node`")
    o.append("")
    o.append("The real-world test of whether graph building stays inside one scope. A "
             "scanner whose scope logic assumes one function finds nothing in the rows "
             "below `same_function` / `same_method`.")
    o.append("")
    sd = Counter(n["scope_distance"] for n in nodes)
    table(o, ["Scope distance", "Count", "% of nodes"],
          [[f"`{k}`", v, pct(v, len(nodes))] for k, v in sd.most_common()])
    table(o, ["Scope distance", "Site", "Graph site", "Enclosing"],
          ex_rows(nodes, "scope_distance", [k for k, _ in sd.most_common()],
                  ["graph_line", "enclosing_func"]))

    # 5 nodes/edges per graph
    o.append("## 5. Nodes and edges per graph")
    o.append("")
    table(o, ["Graph site", "Kind", "Builder", "Nodes", "Edges", "Cond. edges"],
          [[f"{g['corpus']}/{g['file']}:{g['line']}", f"`{g['kind']}`",
            f"`{g['builder_expr']}`" if g["builder_expr"] else "—",
            g["node_count"], g["edge_count"], g["cond_edge_count"]] for g in graphs])
    if graphs:
        ns = [g["node_count"] for g in graphs]
        es = [g["edge_count"] + g["cond_edge_count"] for g in graphs]
        table(o, ["Metric", "min", "max", "mean", "total"],
              [["nodes per graph", min(ns), max(ns), f"{sum(ns)/len(ns):.1f}", sum(ns)],
               ["edges per graph", min(es), max(es), f"{sum(es)/len(es):.1f}", sum(es)]])
    o.append("Edges and conditional edges are counted, not resolved — the number "
             "quantifies how much graph structure a node-only inventory ignores.")
    o.append("")

    # 6 import paths
    o.append("## 6. Import paths observed")
    o.append("")
    table(o, ["Import path", "Kind", "Count"],
          [[f"`{p}`", k, n] for (p, k), n in
           Counter((g["import_path"], g["kind"]) for g in graphs).most_common()])
    table(o, ["callee_form", "Count"],
          [[k, v] for k, v in Counter(g["callee_form"] for g in graphs).most_common()])

    # 7 cohort cross-tab
    o.append("## 7. Reachability by cohort — read this first")
    o.append("")
    grid = defaultdict(Counter)
    for n in nodes:
        c = reach(n)
        if c:
            grid[c][n["cohort"]] += 1
    for g in graphs:
        for b in g["react_bindings"].values():
            c = reach(b)
            if c:
                grid[c][g["cohort"]] += 1
    present = [c for c in cohorts if any(grid[k][c] for k in grid)]
    tots = {c: sum(grid[k][c] for k in grid) for c in cohorts}
    if grid:
        table(o, ["Reachability"] + [f"{c} (n={tots[c]})" for c in cohorts] + ["Total"],
              [[f"`{k}`"] + [f"{grid[k][c]} ({pct(grid[k][c], tots[c])})" for c in cohorts]
               + [sum(grid[k].values())]
               for k in sorted(grid, key=lambda x: -sum(grid[x].values()))])
    else:
        table(o, ["Reachability", "Count"], [["(no reference-valued targets)", 0]])
    if not any(tots[c] for c in cohorts if c == "original"):
        o.append("The `original` column is empty: this is the first LangGraph run, so all "
                 "three repos are `new`. The cross-framework comparison against CrewAI is "
                 "in the narrative rather than this table.")
        o.append("")

    # 8 per-repo, never blended
    o.append("## 8. Per-repo (cohorts never blended)")
    o.append("")
    table(o, ["Cohort", "Repo", ".py", "Graph sites", "Nodes", "Edges", "APIs used"],
          [[d["cohort"], d["corpus"], d["py_file_count"],
            sum(1 for g in graphs if g["corpus"] == d["corpus"]),
            sum(1 for n in nodes if n["corpus"] == d["corpus"]),
            sum(g["edge_count"] + g["cond_edge_count"]
                for g in graphs if g["corpus"] == d["corpus"]),
            ", ".join(sorted({g["kind"] for g in graphs if g["corpus"] == d["corpus"]})) or "—"]
           for d in dialects])

    open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: python survey_lg.py <cohort>:/path [...]", file=sys.stderr)
        return 2
    targets = []
    for a in args:
        cohort, sep, p = a.partition(":")
        if not sep or cohort not in ("original", "new"):
            cohort, p = "new", a
        p = os.path.abspath(p)
        if not os.path.isdir(p):
            print(f"not a directory: {p}", file=sys.stderr)
            return 2
        targets.append((cohort, p, os.path.basename(p.rstrip(os.sep))))

    stats = {"parse_failures": [], "read_failures": [], "py_files": 0,
             "ipynb_files": 0, "files_with_binding": 0, "lookalike_sites": []}
    graphs, nodes, dialects = [], [], []
    for cohort, root, corpus in targets:
        units = discover_repo_units(root)
        n_py = 0
        for path in iter_py_files(root):
            stats["py_files"] += 1
            n_py += 1
            g, nd = scan_file(path, root, units, stats, corpus, cohort)
            if g or nd:
                stats["files_with_binding"] += 1
            graphs.extend(g)
            nodes.extend(nd)
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            stats["ipynb_files"] += sum(1 for f in fn if f.endswith(".ipynb"))
        dialects.append({"corpus": corpus, "cohort": cohort, "py_file_count": n_py})
        print(f"[{cohort:8}] {corpus:42} py={n_py:3} graphs="
              f"{sum(1 for x in graphs if x['corpus']==corpus)} "
              f"nodes={sum(1 for x in nodes if x['corpus']==corpus)}")

    for fname, rowset in (("graph_sites.jsonl", graphs), ("node_attachments.jsonl", nodes)):
        with open(fname, "w", encoding="utf-8") as fh:
            for r in rowset:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    write_aggregates(graphs, nodes, dialects, stats,
                     ", ".join(f"{c}:{n}" for c, _, n in targets))
    print(f"\n.py files:   {stats['py_files']}  (parse failures: {len(stats['parse_failures'])})")
    print(f"graph sites: {len(graphs)}   node attachments: {len(nodes)}")
    print("wrote graph_sites.jsonl, node_attachments.jsonl, aggregates.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
