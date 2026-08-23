#!/usr/bin/env python3
"""Throwaway static-analysis survey of CrewAI construction sites in a cloned corpus.

Usage:  python survey.py /path/to/crewAI-examples

Writes into the current working directory:
    agent_sites.jsonl   Pass A rows (+ Pass B reference fields)
    repo_dialects.jsonl Pass C rows
    aggregates.md       the twelve summary tables

Never imports or executes corpus code. Everything is ast.parse on file bytes.
This script is disposable. It shares no code with the adapter.
"""

import ast
import json
import os
import re
import sys
from collections import Counter, defaultdict

TARGETS = {"Agent", "Crew", "Task", "LLM"}
SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", "site-packages",
             ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
             ".eggs", "env",
             # This script's own output happens to be committed inside corpus 1.
             # Without this it gets discovered as a 32nd "repo unit".
             "survey-results"}

# The kwargs the build spec anticipates; anything else lands in Table 12.
KNOWN_AGENT_KWARGS = {
    "role", "goal", "backstory", "llm", "tools", "mcps", "apps", "config",
    "function_calling_llm", "verbose", "allow_delegation", "max_iter", "memory",
    "cache", "step_callback",
}

# Markers that make a directory a project unit rather than a category folder.
UNIT_MARKERS = ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "poetry.lock")
SINGLE_UNIT = "."  # the corpus root is itself one packaged project

SCOPE_BARRIERS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef,
                  ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
DESCEND_BODIES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
LIST_PARENTS = (ast.List, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


# --------------------------------------------------------------------------
# repo units
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# import map
# --------------------------------------------------------------------------

def crewai_module(mod):
    """True for the crewai distribution itself, not lookalikes such as crewai_tools."""
    return mod == "crewai" or mod.startswith("crewai.")


def build_import_map(tree):
    """direct: local name -> (symbol, module path);  modules: local alias -> module path.

    All Import/ImportFrom nodes are scanned, not only top-level ones: function-local
    imports of Agent do occur and skipping those files would undercount.
    `bound_names` is every name any import binds, for Pass B's "imported" scope.
    `lookalikes` records crewai*-prefixed modules that are not the crewai package.
    """
    direct, modules, bound_names, lookalikes = {}, {}, set(), []
    origin = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                bound_names.add(local)
                origin[local] = alias.name
                mod = alias.name
                if crewai_module(mod):
                    modules[alias.asname or alias.name] = mod
                    if not alias.asname:
                        modules[alias.name.split(".")[0]] = alias.name.split(".")[0]
                elif mod.startswith("crewai"):
                    lookalikes.append(mod)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level:  # relative import: module path is not resolvable statically
                mod = "." * node.level + mod
            for alias in node.names:
                local = alias.asname or alias.name
                bound_names.add(local)
                origin[local] = mod
                if crewai_module(mod) and alias.name in TARGETS:
                    direct[local] = (alias.name, mod)
                elif mod.startswith("crewai") and alias.name in TARGETS:
                    lookalikes.append(mod)
    return direct, modules, bound_names, lookalikes, origin


def match_callee(func, direct, modules):
    """Return (kind, callee_form, import_path) or None."""
    if isinstance(func, ast.Name) and func.id in direct:
        sym, mod = direct[func.id]
        return sym.lower(), "Name", mod
    if isinstance(func, ast.Attribute) and func.attr in TARGETS:
        base = func.value
        if isinstance(base, ast.Name) and base.id in modules:
            return func.attr.lower(), "Attribute", modules[base.id]
        # crewai.agent.Agent after `import crewai`
        try:
            base_text = ast.unparse(base)
        except Exception:
            return None
        head = base_text.split(".")[0]
        if head in modules and crewai_module(base_text):
            return func.attr.lower(), "Attribute", base_text
    return None


# --------------------------------------------------------------------------
# scope collection for Pass B
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Pass A + B over one file
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# v2 Change 1 — sub-classify Call-valued RHS
# --------------------------------------------------------------------------

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
        return "terminal_constructor", name, "CrewAI constructor"
    if name in import_origin:
        src = import_origin[name]
        if name[:1].isupper():
            return "terminal_constructor", name, f"imported from `{src}`, class by PEP 8 naming"
        return "call_unknown", name, (f"imported from `{src}`, function-shaped — "
                                      "cross-module, not followed (latent factory)")
    return "call_unknown", name, "callee neither defined nor imported in this module"


# --------------------------------------------------------------------------
# v2 Change 3 — provably-runtime detection
# --------------------------------------------------------------------------

_RUNTIME_CALLS = {"getenv", "environ.get", "open", "input", "getcwd", "cwd",
                  "loads", "load", "read", "urlopen", "get", "post", "request"}
_RUNTIME_MODULES = ("requests.", "httpx.", "urllib.", "socket.", "aiohttp.")


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


def derive_agent_fields(kwargs):
    d = {}
    llm = kwargs.get("llm")
    if llm is None:
        d["llm_shape"] = "absent"
    else:
        nt = llm["node_type"]
        if nt == "Constant":
            d["llm_shape"] = "constant" if llm["constant_value"] is not None else "other"
        elif nt == "Name":
            d["llm_shape"] = "name"
        elif nt == "Attribute":
            d["llm_shape"] = "attribute"
        elif nt == "Call":
            d["llm_shape"] = "call"
        else:
            d["llm_shape"] = "other"
    d["llm_constant"] = llm["constant_value"] if (llm and d["llm_shape"] == "constant") else None
    d["llm_call_callee"] = None
    if llm is not None and d["llm_shape"] == "call":
        callee = llm["unparsed"].split("(")[0].strip()
        d["llm_call_callee"] = callee.split(".")[-1] or callee

    tools = kwargs.get("tools")
    if tools is None:
        d["tools_shape"] = "absent"
    elif tools["node_type"] == "List":
        d["tools_shape"] = "list"
    elif tools["node_type"] == "Name":
        d["tools_shape"] = "name"
    else:
        d["tools_shape"] = "other"
    d["tools_element_types"] = tools.get("_element_types") if tools else None
    d["tools_element_names"] = tools.get("_element_names") if tools else None

    d["config_present"] = "config" in kwargs
    d["config_subscript_key"] = kwargs["config"].get("_subscript_key") if "config" in kwargs else None
    d["identity_fields_present"] = [f for f in ("role", "goal", "backstory") if f in kwargs]
    return d


def scan_file(path, root, units, stats, corpus, cohort):
    rel = os.path.relpath(path, root)
    try:
        with open(path, "rb") as fh:
            src = fh.read()
    except OSError as exc:
        stats["read_failures"].append((rel, str(exc)))
        return []
    try:
        tree = ast.parse(src, filename=path)
    except (SyntaxError, ValueError) as exc:
        stats["parse_failures"].append((rel, f"{type(exc).__name__}: {exc}"))
        return []
    src_text = src.decode("utf-8", errors="replace")

    direct, modules, imported_names, lookalikes, import_origin = build_import_map(tree)
    for m in lookalikes:
        stats["lookalike_modules"][m] += 1
    if not direct and not modules:
        return []

    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    module_assigns = collect_assignments(tree.body, descend=True)
    module_defs = collect_module_defs(tree)   # v2 Change 1
    func_nodes = {n.name: n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    # v2: census of the bindings a reference could resolve TO. Agent kwargs only
    # ever see one module; this is what shows whether factories exist at all.
    def _census(scope_label, body, owner=None):
        for st in body:
            tgts = []
            if isinstance(st, ast.Assign):
                tgts = [(t, st.value) for t in st.targets]
            elif isinstance(st, ast.AnnAssign) and st.value is not None:
                tgts = [(st.target, st.value)]
            for t, rhs in tgts:
                if not isinstance(t, ast.Name) or not isinstance(rhs, ast.Call):
                    continue
                kind, callee, basis = classify_call_kind(rhs, module_defs[0],
                                                         module_defs[1], import_origin)
                stats["bindings"].append({
                    "corpus": corpus, "cohort": cohort, "file": rel,
                    "line": st.lineno, "scope": scope_label, "owner": owner,
                    "name": t.id, "call_kind": kind, "callee": callee,
                    "basis": basis, "unparsed": unparse(rhs)[:120],
                    "runtime_evidence": runtime_evidence(rhs),
                    **(dict(zip(("factory_terminus", "factory_evidence"),
                                factory_terminus(callee, func_nodes)))
                       if kind == "factory_call" else
                       {"factory_terminus": None, "factory_evidence": None}),
                })
    _census("module", tree.body)
    for _n in tree.body:
        if isinstance(_n, ast.ClassDef):
            _census("class_body", _n.body, _n.name)

    local_caches, class_caches, self_caches = {}, {}, {}
    rows = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        m = match_callee(node.func, direct, modules)
        if m is None:
            continue
        kind, callee_form, import_path = m

        funcnode, clsnode, _ = enclosing(node, parents)
        parent = parents.get(node)

        if funcnode is not None and id(funcnode) not in local_caches:
            local_caches[id(funcnode)] = collect_assignments(funcnode.body, descend=True)
        if clsnode is not None and id(clsnode) not in class_caches:
            class_caches[id(clsnode)] = collect_assignments(clsnode.body, descend=False)
            self_caches[id(clsnode)] = collect_self_attrs(clsnode)
        local_cache = local_caches.get(id(funcnode), ({}, set()))
        class_cache = class_caches.get(id(clsnode), ({}, set()))
        self_cache = self_caches.get(id(clsnode), {})

        kwargs, dup_kwargs, has_double_star = {}, [], False
        for kw in node.keywords:
            if kw.arg is None:
                has_double_star = True
                continue
            if kw.arg in kwargs:
                dup_kwargs.append(kw.arg)
            val = kw.value
            entry = {
                "node_type": type(val).__name__,
                "unparsed": unparse(val),
                # ast.unparse normalises string literals onto one line. The spec also
                # asks for exact source text, so carry the raw segment alongside it.
                "source": ast.get_source_segment(src_text, val),
                "constant_value": val.value if (isinstance(val, ast.Constant)
                                                and isinstance(val.value, str)) else None,
            }
            if isinstance(val, ast.List):
                entry["_element_types"] = dict(Counter(type(e).__name__ for e in val.elts))
                entry["_element_names"] = [unparse(e) for e in val.elts]
                # Elements are references too — the same question one level down, and it
                # decides whether a tools list is statically resolvable at all.
                entry["_element_refs"] = [
                    classify_ref(e, funcnode, clsnode, module_assigns, imported_names,
                                 local_cache, class_cache, self_cache, module_defs,
                                 import_origin)
                    for e in val.elts]
            if isinstance(val, ast.Subscript) and isinstance(val.slice, ast.Constant) \
                    and isinstance(val.slice.value, str):
                entry["_subscript_key"] = val.slice.value
            entry.update(classify_ref(val, funcnode, clsnode, module_assigns,
                                      imported_names, local_cache, class_cache,
                                      self_cache, module_defs, import_origin))
            kwargs[kw.arg] = entry  # duplicates: last wins

        assignment_target = None
        if isinstance(parent, ast.Assign) and len(parent.targets) == 1 \
                and isinstance(parent.targets[0], ast.Name):
            assignment_target = parent.targets[0].id

        row = {
            "kind": kind,
            "corpus": corpus,
            "cohort": cohort,
            "repo": repo_for(rel, units),
            "repo_top": rel.split(os.sep)[0],
            "file": rel,
            "is_test": is_test_path(rel),
            "line": node.lineno,
            "callee_form": callee_form,
            "callee_text": unparse(node.func),
            "import_path": import_path,
            "enclosing_class": clsnode.name if clsnode else None,
            "enclosing_func": funcnode.name if funcnode else None,
            "enclosing_func_decorators": [unparse(d) for d in funcnode.decorator_list] if funcnode else [],
            "enclosing_class_decorators": [unparse(d) for d in clsnode.decorator_list] if clsnode else [],
            "assignment_target": assignment_target,
            "in_return": isinstance(parent, ast.Return),
            "in_list": isinstance(parent, LIST_PARENTS),
            "positional_arg_count": len(node.args),
            "has_double_star": has_double_star,
            "kwarg_names": sorted(kwargs.keys()),
            "duplicate_kwargs": sorted(set(dup_kwargs)),
            "kwargs": kwargs,
        }
        if kind == "agent":
            row.update(derive_agent_fields(kwargs))
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# Pass C
# --------------------------------------------------------------------------

def read_text(path):
    """Decode a manifest without assuming UTF-8. Windows-authored requirements.txt
    files are often UTF-16; reading those as UTF-8 turns 'crewai' into 'c r e w a i'
    and every substring check silently returns False."""
    try:
        raw = open(path, "rb").read()
    except OSError:
        return ""
    for bom, enc in ((b"\xff\xfe\x00\x00", "utf-32"), (b"\x00\x00\xfe\xff", "utf-32"),
                     (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16"),
                     (b"\xef\xbb\xbf", "utf-8-sig")):
        if raw.startswith(bom):
            return raw.decode(enc, errors="replace")
    # BOM-less UTF-16 still shows as interleaved NULs
    if raw[:200].count(b"\x00") > len(raw[:200]) // 4:
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def has_glob(unit_abs, *relparts):
    """Existence check for a path pattern anywhere beneath unit_abs."""
    target = os.path.join(*relparts)
    for dirpath, dirnames, filenames in os.walk(unit_abs):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            candidate = os.path.join(dirpath, fn)
            if candidate.endswith(os.sep + target) or fn == target:
                return True
    return False


def scan_repo_dialect(root, unit, agent_counts, py_counts, import_repos):
    unit_abs = os.path.join(root, unit)
    found = defaultdict(bool)
    extras, ptype, manifest_crewai, pin = set(), None, False, None
    nb_count, nb_crewai = 0, 0

    for dirpath, dirnames, filenames in os.walk(unit_abs):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        parent_name = os.path.basename(dirpath)
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if fn.endswith(".ipynb"):
                nb_count += 1
                try:
                    if "crewai" in open(full, "r", encoding="utf-8",
                                        errors="replace").read().lower():
                        nb_crewai += 1
                except OSError:
                    pass
            if fn == "crew.jsonc":
                found["has_crew_jsonc"] = True
            elif fn == "crew.json":
                found["has_crew_json"] = True
            elif fn.endswith(".jsonc") and parent_name == "agents":
                found["has_agents_jsonc_dir"] = True
            elif fn == "agents.yaml" and parent_name == "config":
                found["has_agents_yaml"] = True
            elif fn == "tasks.yaml" and parent_name == "config":
                found["has_tasks_yaml"] = True
            elif fn in ("pyproject.toml", "requirements.txt", "Pipfile"):
                text = read_text(full)
                if "crewai" in text.lower():
                    manifest_crewai = True
                m = re.search(r"crewai(?:\[[^\]]*\])?\s*([=><~!]=?[^\"',\s]+)", text)
                if m and not pin:
                    pin = m.group(1)
                for m in re.finditer(r"crewai\s*\[([^\]]*)\]", text):
                    for e in m.group(1).split(","):
                        e = e.strip().strip("\"'")
                        if e:
                            extras.add(e)
                if fn == "pyproject.toml":
                    m = re.search(r"^\s*type\s*=\s*[\"']([^\"']+)[\"']", text, re.M)
                    if m:
                        ptype = m.group(1)

    return {
        "repo": unit,
        "repo_top": unit.split(os.sep)[0],
        "has_crew_jsonc": bool(found["has_crew_jsonc"]),
        "has_crew_json": bool(found["has_crew_json"]),
        "has_agents_jsonc_dir": bool(found["has_agents_jsonc_dir"]),
        "has_agents_yaml": bool(found["has_agents_yaml"]),
        "has_tasks_yaml": bool(found["has_tasks_yaml"]),
        "has_pyproject_crewai": manifest_crewai,
        "pyproject_type": ptype,
        "crewai_pin": pin,
        "crewai_extras": sorted(extras),
        "has_crewai_import": unit in import_repos,
        "agent_site_count": agent_counts.get(unit, 0),
        "py_file_count": py_counts.get(unit, 0),
        "ipynb_file_count": nb_count,
        "ipynb_mentioning_crewai": nb_crewai,
    }


# --------------------------------------------------------------------------
# aggregates
# --------------------------------------------------------------------------

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


def reachability(kw):
    """v2 Change 5. One reachability category per reference.

    A call-valued reference is reported by its ref_call_kind (that is the thing
    that decides whether following it is worth building); everything else by its
    binding scope.
    """
    scope = kw.get("ref_scope")
    if not scope:
        return None
    if kw.get("ref_call_kind") and scope not in ("runtime_external",):
        return kw["ref_call_kind"]
    return scope


def surface_bucket(row):
    fdec = " ".join(row["enclosing_func_decorators"])
    cdec = " ".join(row["enclosing_class_decorators"])
    if row["in_list"]:
        return "inside comprehension/list"
    if "CrewBase" in cdec and re.search(r"\bagent\b", fdec):
        return "decorated method (@agent) in @CrewBase class"
    if re.search(r"\bagent\b", fdec):
        return "decorated method (@agent)"
    if "CrewBase" in cdec:
        return "method in @CrewBase class (undecorated)"
    if row["enclosing_class"] and row["enclosing_func"]:
        return "plain method"
    if row["enclosing_func"]:
        return "plain function"
    if row["enclosing_class"]:
        return "class body"
    return "module-level"


def write_aggregates(rows, dialects, stats, corpora_label, unit_count,
                     path="aggregates.md"):
    agents = [r for r in rows if r["kind"] == "agent"]
    crews = [r for r in rows if r["kind"] == "crew"]
    tasks = [r for r in rows if r["kind"] == "task"]
    llms = [r for r in rows if r["kind"] == "llm"]
    na = len(agents)
    o = []

    o.append("# CrewAI corpus survey v2 — aggregates")
    o.append("")
    o.append(f"Corpora scanned in this run: `{corpora_label}`")
    o.append("")
    o.append("**v2 changes against v1.** Pass B's `Call` case is split into "
             "`terminal_constructor` / `factory_call` / `call_unknown` (`ref_call_kind`); "
             "`argument_passed` is a scope of its own; v1's `unresolved` is split into "
             "`runtime_external` (provably execution-time) and `unresolved_local` "
             "(addressable). Every corpus below went through v2 in one run, so all "
             "counts share these categories. Repos are labelled `original` (the four "
             "already surveyed) or `new`.")
    o.append("")
    o.append("**Reading `imported`.** The survey does not cross module boundaries, so a "
             "cross-module import is unresolved-but-addressable. `ref_scope` keeps "
             "`imported` because the distinction is informative; the reachability table "
             "folds it into `unresolved_local` and shows the split.")
    o.append("")
    o.append("**Repo-unit note.** A corpus root carrying its own packaging manifest is "
             "one unit; otherwise units are the nearest directories holding a manifest or "
             "code, capped at depth 3. `repo_top` preserves the literal first-component "
             "reading.")
    o.append("")

    # 1
    o.append("## 1. Totals")
    o.append("")
    table(o, ["Metric", "Count"], [
        ["Corpora scanned", len({d["corpus"] for d in dialects})],
        ["Repo units scanned", unit_count],
        ["Top-level categories", len({d['repo_top'] for d in dialects})],
        [".py files scanned", stats["py_files"]],
        [".ipynb files present (not parsed — see narrative)", stats["ipynb_files"]],
        ["Parse failures", len(stats["parse_failures"])],
        ["Read failures", len(stats["read_failures"])],
        ["Files importing crewai symbols", stats["files_with_binding"]],
        ["Agent sites", na],
        ["Crew sites", len(crews)],
        ["Task sites", len(tasks)],
        ["LLM sites", len(llms)],
        ["Agent sites in test/example paths", sum(1 for r in agents if r["is_test"])],
    ])
    if stats["parse_failures"]:
        o.append("Parse failures:")
        o.append("")
        table(o, ["File", "Error"], [[p, e] for p, e in stats["parse_failures"]])
    else:
        o.append("No parse failures.")
        o.append("")

    # 2
    o.append("## 2. Kwarg frequency on `Agent(...)`")
    o.append("")
    c = Counter(k for r in agents for k in r["kwarg_names"])
    table(o, ["Kwarg", "Count", "% of agents", "Anticipated by spec"],
          [[k, n, pct(n, na), "yes" if k in KNOWN_AGENT_KWARGS else "**NO**"]
           for k, n in c.most_common()])
    dbl = sum(1 for r in agents if r["has_double_star"])
    pos = sum(1 for r in agents if r["positional_arg_count"])
    o.append(f"Agents constructed with `**kwargs` unpacking: {dbl} ({pct(dbl, na)}). "
             f"Agents with positional args: {pos} ({pct(pos, na)}).")
    o.append("")

    # 3
    o.append("## 3. `llm_shape` distribution")
    o.append("")
    c = Counter(r["llm_shape"] for r in agents)
    table(o, ["llm_shape", "Count", "% of agents"],
          [[k, n, pct(n, na)] for k, n in c.most_common()])

    # 4
    o.append("## 4. `llm_call_callee` distribution")
    o.append("")
    c = Counter(r["llm_call_callee"] for r in agents if r["llm_call_callee"])
    if c:
        table(o, ["Callee", "Count"], [[k, n] for k, n in c.most_common()])
    else:
        o.append("No `llm=` kwarg is a direct call at an Agent site.")
        o.append("")
    ind = Counter()
    for r in agents:
        for kwname in ("llm", "function_calling_llm"):
            kw = r["kwargs"].get(kwname)
            if kw and kw.get("ref_target_type") == "Call" and kw.get("ref_target_unparsed"):
                callee = kw["ref_target_unparsed"].split("(")[0].strip().split(".")[-1]
                ind[callee] += 1
    o.append("Constructors reached **indirectly** (the `llm=`/`function_calling_llm=` "
             "reference resolves to a call), from Pass B:")
    o.append("")
    table(o, ["Resolved callee", "Count"], [[k, n] for k, n in ind.most_common()] or [["(none)", 0]])

    # 5
    o.append("## 5. `llm_constant` values")
    o.append("")
    c = Counter(r["llm_constant"] for r in agents if r["llm_constant"])
    for r in agents:
        kw = r["kwargs"].get("llm")
        if kw and kw.get("ref_target_type") == "Constant":
            pass
    rows5 = []
    for v, n in c.most_common():
        flags = []
        if v.count("/") > 1:
            flags.append("multi-slash")
        if v == "provider/model-id":
            flags.append("**literal placeholder**")
        rows5.append([f"`{v}`", n, ", ".join(flags)])
    table(o, ["Model string", "Count", "Flags"], rows5 or [["(none)", 0, ""]])
    # Model strings hide in three other places, all of which Table 5's Agent-only
    # `llm=` view misses: model kwargs on LLM(...), model kwargs nested inside a
    # constructor call, and llm-ish kwargs on Crew/Task — `manager_llm="GPT-4o"`
    # is a bare model string that never touches an Agent.
    LLM_KWARGS = ("llm", "manager_llm", "function_calling_llm", "planning_llm",
                  "model", "model_name")
    modelstrings, offsite = Counter(), Counter()
    for r in rows:
        for kwname, kw in r["kwargs"].items():
            if kwname not in LLM_KWARGS:
                continue
            if kw.get("constant_value"):
                if r["kind"] == "agent" and kwname == "llm":
                    continue  # already in the table above
                offsite[(r["kind"], kwname, kw["constant_value"])] += 1
            if kwname in ("model", "model_name") and kw.get("constant_value"):
                modelstrings[kw["constant_value"]] += 1
            elif kw["node_type"] == "Call":
                m = re.search(r"model(?:_name|_str)?=['\"]([^'\"]+)['\"]", kw["unparsed"])
                if m:
                    modelstrings[m.group(1)] += 1
        # and inside whatever a reference resolved to
        for kw in r["kwargs"].values():
            if kw.get("ref_target_type") == "Call" and kw.get("ref_target_unparsed"):
                m = re.search(r"model(?:_name|_str)?=['\"]([^'\"]+)['\"]",
                              kw["ref_target_unparsed"])
                if m:
                    modelstrings[m.group(1)] += 1
    if offsite:
        o.append("**Constant model strings on kwargs other than `Agent(llm=)`** — these "
                 "are invisible to the table above:")
        o.append("")
        table(o, ["Kind", "Kwarg", "Value", "Count", "Flags"],
              [[k, kwn, f"`{v}`", n,
                ", ".join(([ "multi-slash"] if v.count("/") > 1 else [])
                          + (["**literal placeholder**"] if v == "provider/model-id" else [])
                          + (["**not lowercase — LiteLLM ids are lowercase**"]
                             if v != v.lower() else []))]
               for (k, kwn, v), n in offsite.most_common()])
    o.append("Model strings found inside constructor calls (`LLM(...)`, `llm=Call(...)`, "
             "or whatever a reference resolved to):")
    o.append("")
    rows5b = []
    for v, n in modelstrings.most_common():
        flags = []
        if v.count("/") > 1:
            flags.append("multi-slash")
        if v == "provider/model-id":
            flags.append("**literal placeholder**")
        if v.endswith("/") or v.startswith("/"):
            flags.append("**partial — concatenated at runtime, not a real id**")
        if v != v.lower():
            flags.append("not lowercase")
        rows5b.append([f"`{v}`", n, ", ".join(flags)])
    table(o, ["Model string", "Count", "Flags"], rows5b or [["(none)", 0, ""]])

    # 6
    o.append("## 6. `ref_scope` distribution")
    o.append("")
    allref = Counter()
    for r in agents:
        for kw in r["kwargs"].values():
            if kw.get("ref_scope"):
                allref[kw["ref_scope"]] += 1
    tot = sum(allref.values())
    o.append("All reference-valued kwargs on `Agent(...)`:")
    o.append("")
    table(o, ["ref_scope", "Count", "% of refs"],
          [[k, n, pct(n, tot)] for k, n in allref.most_common()]
          or [["(none — no kwarg on any Agent is a bare Name or Attribute)", 0, "0.0%"]])
    llmref = Counter()
    for r in agents:
        kw = r["kwargs"].get("llm")
        if kw and kw.get("ref_scope"):
            llmref[kw["ref_scope"]] += 1
    tl = sum(llmref.values())
    o.append("`llm=` alone:")
    o.append("")
    table(o, ["ref_scope", "Count", "% of llm refs"],
          [[k, n, pct(n, tl)] for k, n in llmref.most_common()] or [["(none)", 0, "0.0%"]])
    toolsref = Counter()
    for r in agents:
        kw = r["kwargs"].get("tools")
        if kw and kw.get("ref_scope"):
            toolsref[kw["ref_scope"]] += 1
    o.append("`tools=` alone:")
    o.append("")
    table(o, ["ref_scope", "Count"], [[k, n] for k, n in toolsref.most_common()] or [["(none)", 0]])
    bind = Counter()
    for r in agents:
        for kw in r["kwargs"].values():
            if kw.get("ref_scope") == "self_attr":
                bind[kw.get("ref_binding_site") or "?"] += 1
    o.append("Where `self.<attr>` references are actually bound:")
    o.append("")
    table(o, ["Binding site", "Count"], [[k, n] for k, n in bind.most_common()] or [["(none)", 0]])
    resolved = sum(n for k, n in allref.items()
                   if k in ("local", "class_attr", "module", "self_attr"))
    o.append(f"**Locally resolvable** (local / class_attr / module / self_attr): "
             f"{resolved} of {tot} ({pct(resolved, tot)}).")
    o.append("")

    # --- v2 Change 1: ref_call_kind ---------------------------------------
    o.append("### 6a. `ref_call_kind` — the Call split (v2 Change 1)")
    o.append("")
    o.append("Sub-classification of references whose resolved RHS is a call. This is "
             "what decides whether factory-following is worth building.")
    o.append("")
    ck, ck_llm = Counter(), Counter()
    for r in agents:
        for kwn, kw in r["kwargs"].items():
            if kw.get("ref_call_kind"):
                ck[kw["ref_call_kind"]] += 1
                if kwn == "llm":
                    ck_llm[kw["ref_call_kind"]] += 1
    tck = sum(ck.values())
    table(o, ["ref_call_kind", "Count", "% of call-valued refs", "of which `llm=`"],
          [[k, n, pct(n, tck), ck_llm.get(k, 0)] for k, n in ck.most_common()]
          or [["(none — no reference resolves to a call)", 0, "0.0%", 0]])
    ex = defaultdict(list)
    for r in agents:
        for kwn, kw in r["kwargs"].items():
            if kw.get("ref_call_kind"):
                ex[kw["ref_call_kind"]].append(
                    (f"{r['corpus']}/{r['file']}:{r['line']}", kwn,
                     (kw.get("ref_target_unparsed") or "")[:64], kw.get("ref_call_basis")))
    o.append("Spot-check examples (up to 3 per bucket, with `file:line`):")
    o.append("")
    rows_ex = []
    for kind in ("factory_call", "terminal_constructor", "call_unknown"):
        for site, kwn, tgt, basis in ex.get(kind, [])[:3]:
            rows_ex.append([kind, site, f"`{kwn}=`", f"`{tgt}`", basis])
    table(o, ["Bucket", "Site", "Kwarg", "Resolved RHS", "Why"],
          rows_ex or [["(none)", "", "", "", ""]])

    # --- v2 Change 5: reachability by cohort ------------------------------
    o.append("### 6b. Reachability by cohort (v2 Change 5) — read this first")
    o.append("")
    o.append("One row per reachability category, cross-tabbed against the `original` "
             "and `new` cohorts. A call-valued reference is reported by its "
             "`ref_call_kind`; everything else by its `ref_scope`.")
    o.append("")
    cohorts = sorted({r["cohort"] for r in agents}) or ["original"]
    grid = defaultdict(Counter)
    for r in agents:
        for kw in r["kwargs"].values():
            cat = reachability(kw)
            if cat:
                grid[cat][r["cohort"]] += 1
    order = ["local", "class_attr", "module", "self_attr", "terminal_constructor",
             "factory_call", "call_unknown", "argument_passed", "namespace_attr",
             "imported", "unresolved_local", "runtime_external"]
    seen = [c for c in order if c in grid] + [c for c in grid if c not in order]
    totals = {ch: sum(grid[c][ch] for c in grid) for ch in cohorts}
    hdr = ["Reachability"] + [f"{ch} (n={totals.get(ch,0)})" for ch in cohorts] + ["Total"]
    body = []
    for cat in seen:
        cells = [grid[cat][ch] for ch in cohorts]
        pcts = [f"{grid[cat][ch]} ({pct(grid[cat][ch], totals.get(ch,0))})" for ch in cohorts]
        body.append([f"`{cat}`"] + pcts + [sum(cells)])
    table(o, hdr, body or [["(none)"] + [""] * (len(cohorts) + 1)])
    imported_n = sum(grid["imported"].values())
    unres_n = sum(grid["unresolved_local"].values())
    o.append(f"Addressable bucket = `unresolved_local` ({unres_n}) + `imported` "
             f"({imported_n}) = **{unres_n + imported_n}**; provably terminal = "
             f"`runtime_external` ({sum(grid['runtime_external'].values())}).")
    o.append("")

    # --- v2 Change 4: locals, loudly, per cohort --------------------------
    o.append("### 6c. Local-variable references by cohort (v2 Change 4)")
    o.append("")
    loc = Counter()
    for r in agents:
        for kw in r["kwargs"].values():
            if kw.get("ref_scope") == "local":
                loc[r["cohort"]] += 1
    table(o, ["Cohort", "`local` refs", "All refs", "% local"],
          [[ch, loc.get(ch, 0), totals.get(ch, 0), pct(loc.get(ch, 0), totals.get(ch, 0))]
           for ch in cohorts])
    o.append("v1 measured 0 local-variable references across 95 agents. This table is "
             "the check on whether that still holds for the `new` cohort — the deferred "
             "function-scope walker is only worth reviving if it climbs here.")
    o.append("")

    # --- v2: binding census, where the factories actually live ------------
    binds = stats.get("bindings", [])
    if binds:
        o.append("### 6d. Binding census — call-valued bindings a reference could resolve to")
        o.append("")
        o.append("Agent kwargs only ever see one module, so `factory_call` can look empty "
                 "at the call site while factories exist one import away. This censuses "
                 "every module-level and class-body binding whose RHS is a call, across "
                 "every file scanned — the population a cross-module resolver would reach.")
        o.append("")
        bc = defaultdict(Counter)
        for b in binds:
            bc[b["call_kind"]][b["cohort"]] += 1
        cohs = sorted({b["cohort"] for b in binds})
        tot_b = {c: sum(bc[k][c] for k in bc) for c in cohs}
        table(o, ["call_kind"] + [f"{c} (n={tot_b[c]})" for c in cohs] + ["Total"],
              [[f"`{k}`"] + [f"{bc[k][c]} ({pct(bc[k][c], tot_b[c])})" for c in cohs]
               + [sum(bc[k].values())]
               for k in sorted(bc, key=lambda x: -sum(bc[x].values()))])
        o.append("Spot-check examples (up to 3 per bucket, with `file:line`):")
        o.append("")
        exb = defaultdict(list)
        for b in binds:
            exb[b["call_kind"]].append(b)
        rows_b = []
        for kind in ("factory_call", "terminal_constructor", "call_unknown"):
            for b in exb.get(kind, [])[:3]:
                rows_b.append([kind, f"{b['corpus']}/{b['file']}:{b['line']}",
                               f"`{b['name']}`", f"`{b['unparsed'][:56]}`", b["basis"]])
        table(o, ["Bucket", "Site", "Binds", "RHS", "Why"],
              rows_b or [["(none)", "", "", "", ""]])
        rt_b = [b for b in binds if b["runtime_evidence"]]
        if rt_b:
            o.append(f"Of these bindings, **{len(rt_b)}** are provably runtime-external:")
            o.append("")
            table(o, ["Site", "Binds", "Evidence"],
                  [[f"{b['corpus']}/{b['file']}:{b['line']}", f"`{b['name']}`",
                    f"`{b['runtime_evidence'][:60]}`"] for b in rt_b[:10]])
        fac = [b for b in binds if b["call_kind"] == "factory_call"]
        if fac:
            ft = Counter(b["factory_terminus"] for b in fac)
            o.append("**Where the factories actually terminate.** Following each "
                     "`factory_call` into its `def` in the same module (max 3 hops) — "
                     "this is the payoff test for building factory-following at all:")
            o.append("")
            table(o, ["Terminus", "Count", "% of factories"],
                  [[f"`{k}`", n, pct(n, len(fac))] for k, n in ft.most_common()])
            table(o, ["Factory site", "Binds", "Terminates in"],
                  [[f"{b['corpus']}/{b['file']}:{b['line']}", f"`{b['name']}`",
                    f"`{(b['factory_evidence'] or '?')[:56]}`"] for b in fac[:6]])

        # which of these are the target of an `imported` reference at an agent site
        imported_names_used = {kw["unparsed"] for r in agents
                               for kw in r["kwargs"].values()
                               if kw.get("ref_scope") == "imported"}
        latent = [b for b in binds if b["name"] in imported_names_used]
        if latent:
            o.append(f"**Latent cross-module chains: {len(latent)}.** These bindings are "
                     f"named by an `imported` reference at an agent site elsewhere in the "
                     f"corpus — the value a one-module-hop resolver would recover:")
            o.append("")
            table(o, ["Binding site", "Name", "call_kind", "RHS"],
                  [[f"{b['corpus']}/{b['file']}:{b['line']}", f"`{b['name']}`",
                    f"`{b['call_kind']}`", f"`{b['unparsed'][:56]}`"] for b in latent[:10]])
        o.append("")

    # --- runtime evidence -------------------------------------------------
    rt = [(f"{r['corpus']}/{r['file']}:{r['line']}", kwn, kw.get("ref_runtime_evidence"),
           kw.get("ref_scope_base"))
          for r in agents for kwn, kw in r["kwargs"].items()
          if kw.get("ref_scope") == "runtime_external"]
    if rt:
        o.append("`runtime_external` evidence:")
        o.append("")
        table(o, ["Site", "Kwarg", "Evidence", "Would have been"],
              [[a, f"`{b}`", f"`{c}`", d or "unresolved"] for a, b, c, d in rt[:12]])
    hops = Counter(kw.get("ref_next_hop") for r in agents for kw in r["kwargs"].values()
                   if kw.get("ref_next_hop"))
    if hops:
        o.append("References that resolve one hop to a call-site-bound parameter "
                 "(`self.x = <param>`):")
        o.append("")
        table(o, ["Next hop", "Count"], [[k, n] for k, n in hops.most_common()])

    # 7
    o.append("## 7. `tools_element_types` (summed across agents)")
    o.append("")
    c = Counter()
    for r in agents:
        for k, n in (r["tools_element_types"] or {}).items():
            c[k] += n
    table(o, ["Element node type", "Count"], [[k, n] for k, n in c.most_common()] or [["(none)", 0]])
    ts = Counter(r["tools_shape"] for r in agents)
    o.append("`tools_shape`:")
    o.append("")
    table(o, ["tools_shape", "Count", "% of agents"],
          [[k, n, pct(n, na)] for k, n in ts.most_common()])
    oth = Counter()
    for r in agents:
        if r["tools_shape"] == "other":
            oth[r["kwargs"]["tools"]["node_type"]] += 1
    if oth:
        o.append("What `tools_shape == \"other\"` actually is (no element list is "
                 "recoverable from these without evaluating them):")
        o.append("")
        table(o, ["Node type", "Count"], [[k, n] for k, n in oth.most_common()])
    eref = Counter()
    for r in agents:
        kw = r["kwargs"].get("tools")
        for e in (kw or {}).get("_element_refs", []) or []:
            if e.get("ref_scope"):
                eref[e["ref_scope"]] += 1
    o.append("Reference scope of the **elements** inside `tools=[...]` (beyond the spec's "
             "kwarg-level Pass B, but it is what decides whether a tools list resolves):")
    o.append("")
    table(o, ["Element ref_scope", "Count"],
          [[k, n] for k, n in eref.most_common()] or [["(none)", 0]])
    en = Counter(nm for r in agents for nm in (r["tools_element_names"] or []))
    o.append("Most common tool expressions:")
    o.append("")
    table(o, ["Element", "Count"], [[f"`{k}`", n] for k, n in en.most_common(25)] or [["(none)", 0]])

    # 8
    o.append("## 8. Construction surface")
    o.append("")
    c = Counter(surface_bucket(r) for r in agents)
    table(o, ["Surface", "Count", "% of agents"],
          [[k, n, pct(n, na)] for k, n in c.most_common()])
    o.append("Cross-tab of the raw signals:")
    o.append("")
    xt = Counter()
    for r in agents:
        xt[(bool(r["enclosing_class"]), bool(r["enclosing_func"]),
            bool(r["enclosing_func_decorators"]), bool(r["enclosing_class_decorators"]),
            r["in_return"], r["in_list"])] += 1
    table(o, ["in class", "in func", "func decorated", "class decorated", "in return",
              "in list", "Count"],
          [[a, b, cc, d, e, f, n] for (a, b, cc, d, e, f), n in xt.most_common()])
    dec = Counter(d for r in agents for d in r["enclosing_func_decorators"])
    cdec = Counter(d for r in agents for d in r["enclosing_class_decorators"])
    o.append("Decorators observed on the enclosing function / class:")
    o.append("")
    table(o, ["Decorator", "Scope", "Count"],
          [[f"`{k}`", "func", n] for k, n in dec.most_common()]
          + [[f"`{k}`", "class", n] for k, n in cdec.most_common()])

    # 9
    o.append("## 9. Import paths observed")
    o.append("")
    c = Counter(r["import_path"] for r in agents)
    table(o, ["Import path (Agent)", "Count"], [[f"`{k}`", n] for k, n in c.most_common()])
    ck = Counter((r["kind"], r["import_path"]) for r in rows)
    o.append("All kinds:")
    o.append("")
    table(o, ["Kind", "Import path", "Count"],
          [[k, f"`{p}`", n] for (k, p), n in ck.most_common()])
    if stats["lookalike_modules"]:
        o.append("`crewai*` modules seen that are **not** the `crewai` package "
                 "(excluded from matching):")
        o.append("")
        table(o, ["Module", "Import statements"],
              [[f"`{k}`", n] for k, n in stats["lookalike_modules"].most_common()])

    # 10
    o.append("## 10. `identity_fields_present`")
    o.append("")
    allthree = sum(1 for r in agents if len(r["identity_fields_present"]) == 3)
    some = sum(1 for r in agents if 0 < len(r["identity_fields_present"]) < 3)
    none = sum(1 for r in agents if not r["identity_fields_present"])
    table(o, ["Identity fields", "Count", "% of agents"], [
        ["All three (role, goal, backstory)", allthree, pct(allthree, na)],
        ["Some (1-2)", some, pct(some, na)],
        ["None", none, pct(none, na)],
    ])
    c = Counter(",".join(r["identity_fields_present"]) or "(none)" for r in agents)
    table(o, ["Exact combination", "Count"], [[k, n] for k, n in c.most_common()])

    # 11
    o.append("## 11. Repo dialects")
    o.append("")
    table(o, ["Repo", "py", "ipynb", "agent sites", "agents.yaml", "tasks.yaml",
              "crew.json(c)", "agents/*.jsonc", "manifest crewai", "pin", "type", "extras",
              "crewai import", "dialect_only", "invisible"],
          [[d["repo"], d["py_file_count"], d["ipynb_file_count"], d["agent_site_count"],
            "Y" if d["has_agents_yaml"] else "", "Y" if d["has_tasks_yaml"] else "",
            "Y" if (d["has_crew_json"] or d["has_crew_jsonc"]) else "",
            "Y" if d["has_agents_jsonc_dir"] else "",
            "Y" if d["has_pyproject_crewai"] else "", d["crewai_pin"] or "",
            d["pyproject_type"] or "",
            ",".join(d["crewai_extras"]), "Y" if d["has_crewai_import"] else "",
            "**YES**" if d["dialect_only"] else "",
            "**YES**" if d["invisible_to_ast"] else ""]
           for d in sorted(dialects, key=lambda x: x["repo"])])

    donly = [d["repo"] for d in dialects if d["dialect_only"]]
    o.append(f"**dialect_only repos (spec definition — config/manifest signal but zero "
             f"`Agent(...)` sites): {len(donly)} of {len(dialects)} "
             f"({pct(len(donly), len(dialects))})**")
    o.append("")
    if donly:
        for r in donly:
            d = next(x for x in dialects if x["repo"] == r)
            why = [n for n, f in (("config/agents.yaml", d["has_agents_yaml"]),
                                  ("config/tasks.yaml", d["has_tasks_yaml"]),
                                  ("crewai in manifest", d["has_pyproject_crewai"]),
                                  ("imports crewai", d["has_crewai_import"])) if f]
            o.append(f"- `{r}` — {', '.join(why) or 'no signal'} "
                     f"({d['py_file_count']} .py files)")
    else:
        paired = [d for d in dialects if d["has_agents_yaml"] and d["agent_site_count"]]
        o.append(f"None. All {len(paired)} repo(s) carrying `config/agents.yaml` also "
                 f"construct `Agent(...)` in Python — the YAML dialect here is always "
                 f"*paired* with a `config=` call site, never a replacement for one. The "
                 f"flag as specified therefore finds nothing in this corpus.")
    o.append("")

    inv = [d for d in dialects if d["invisible_to_ast"]]

    def cause_of(d):
        if d["notebook_only"]:
            return "notebook-only"
        if d["py_file_count"] == 0 and d["ipynb_file_count"] == 0:
            return "no code at all"
        return "py files but no Agent sites"

    causes = Counter(cause_of(d) for d in inv)
    lead = (f"dominated by {causes.most_common(1)[0][0]}" if causes else "empty")
    o.append(f"**Broader flag — repos an AST-only pass sees nothing in, for any reason: "
             f"{len(inv)} of {len(dialects)} ({pct(len(inv), len(dialects))})**. This is "
             f"the population `dialect_only` was meant to catch; here it is {lead}:")
    o.append("")
    for d in sorted(inv, key=lambda x: x["repo"]):
        o.append(f"- `{d['repo']}` — {cause_of(d)} "
                 f"({d['py_file_count']} .py, {d['ipynb_file_count']} .ipynb, "
                 f"{d['ipynb_mentioning_crewai']} of them mentioning crewai)")
    o.append("")
    nb = [d for d in dialects if d["notebook_only"]]
    if nb:
        o.append(f"Notebook-only repos: **{len(nb)} of {len(dialects)} "
                 f"({pct(len(nb), len(dialects))})**. `.ipynb` is outside the `*.py` glob "
                 f"the spec defines, so none of their agent sites appear anywhere in "
                 f"Passes A or B.")
    else:
        total_nb = sum(d["ipynb_file_count"] for d in dialects)
        o.append(f"No notebook-only repos ({total_nb} `.ipynb` files in the corpus). The "
                 f"`*.py`-glob blind spot does not bite here.")
    o.append("")

    # 12
    o.append("## 12. Unrecognised kwargs on `Agent(...)`")
    o.append("")
    unk = Counter()
    example = {}
    for r in agents:
        for k, v in r["kwargs"].items():
            if k not in KNOWN_AGENT_KWARGS:
                unk[k] += 1
                example.setdefault(k, (v["unparsed"], f"{r['file']}:{r['line']}"))
    table(o, ["Kwarg", "Count", "% of agents", "Example value", "First seen"],
          [[f"`{k}`", n, pct(n, na), f"`{example[k][0][:110]}`", example[k][1]]
           for k, n in unk.most_common()] or [["(none)", 0, "0.0%", "", ""]])
    if not unk:
        o.append("Empty. Every kwarg in the corpus is already anticipated by the build spec.")
        o.append("")
    seen = {k for r in agents for k in r["kwarg_names"]}
    absent = sorted(KNOWN_AGENT_KWARGS - seen)
    o.append("The inverse is the more interesting result — spec-anticipated kwargs that "
             "**never appear** in the corpus:")
    o.append("")
    table(o, ["Anticipated kwarg", "Occurrences"], [[f"`{k}`", 0] for k in absent])
    o.append(f"{len(absent)} of {len(KNOWN_AGENT_KWARGS)} anticipated kwargs are unused; "
             f"{len(seen)} distinct kwargs carry the entire corpus.")
    o.append("")

    # bonus context for the other kinds
    o.append("## Appendix — kwargs on the other kinds")
    o.append("")
    for kindname, coll in (("Crew", crews), ("Task", tasks), ("LLM", llms)):
        c = Counter(k for r in coll for k in r["kwarg_names"])
        o.append(f"### `{kindname}(...)` — {len(coll)} sites")
        o.append("")
        table(o, ["Kwarg", "Count", f"% of {kindname.lower()}s"],
              [[k, n, pct(n, len(coll))] for k, n in c.most_common()] or [["(none)", 0, "0.0%"]])

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(o) + "\n")


# --------------------------------------------------------------------------

def scan_corpus(root, corpus, cohort, stats):
    """One corpus root. Returns (rows, dialects)."""
    units = discover_repo_units(root)
    py_counts, agent_counts, import_repos = Counter(), Counter(), set()
    rows = []
    for path in iter_py_files(root):
        rel = os.path.relpath(path, root)
        stats["py_files"] += 1
        unit = repo_for(rel, units)
        py_counts[unit] += 1
        before = len(rows)
        file_rows = scan_file(path, root, units, stats, corpus, cohort)
        if file_rows:
            stats["files_with_binding"] += 1
            import_repos.add(unit)
        rows.extend(file_rows)
        agent_counts[unit] += sum(1 for r in rows[before:] if r["kind"] == "agent")

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        stats["ipynb_files"] += sum(1 for f in filenames if f.endswith(".ipynb"))

    dialects = []
    for unit in sorted(units):
        d = scan_repo_dialect(root, unit, agent_counts, py_counts, import_repos)
        d["corpus"], d["cohort"] = corpus, cohort
        d["dialect_only"] = bool(
            (d["has_agents_yaml"] or d["has_tasks_yaml"] or d["has_crew_json"]
             or d["has_crew_jsonc"] or d["has_agents_jsonc_dir"] or d["has_pyproject_crewai"])
            and d["agent_site_count"] == 0)
        d["invisible_to_ast"] = d["agent_site_count"] == 0
        d["notebook_only"] = d["py_file_count"] == 0 and d["ipynb_mentioning_crewai"] > 0
        dialects.append(d)
    return rows, dialects, units


def main():
    """usage: python survey_v2.py <cohort>:<path> [<cohort>:<path> ...]

    Every corpus goes through v2 in one run so all counts share the v2 categories.
    `cohort` is `original` or `new`; a bare path defaults to `original`.
    """
    args = sys.argv[1:]
    if not args:
        print(main.__doc__, file=sys.stderr)
        return 2

    targets = []
    for a in args:
        cohort, sep, path = a.partition(":")
        if not sep or cohort not in ("original", "new"):
            cohort, path = "original", a
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            print(f"not a directory: {path}", file=sys.stderr)
            return 2
        targets.append((cohort, path, os.path.basename(path.rstrip(os.sep))))

    stats = {"parse_failures": [], "read_failures": [], "py_files": 0, "ipynb_files": 0,
             "files_with_binding": 0, "lookalike_modules": Counter(),
             "bindings": []}
    all_rows, all_dialects, unit_count = [], [], 0
    for cohort, path, corpus in targets:
        rows, dialects, units = scan_corpus(path, corpus, cohort, stats)
        all_rows.extend(rows)
        all_dialects.extend(dialects)
        unit_count += len(units)
        print(f"[{cohort:8}] {corpus:28} units={len(units):2} "
              f"agents={sum(1 for r in rows if r['kind']=='agent'):3} "
              f"crews={sum(1 for r in rows if r['kind']=='crew'):2} "
              f"tasks={sum(1 for r in rows if r['kind']=='task'):3}")

    with open("agent_sites.jsonl", "w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open("repo_dialects.jsonl", "w", encoding="utf-8") as fh:
        for d in all_dialects:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")

    write_aggregates(all_rows, all_dialects, stats,
                     ", ".join(f"{c}:{n}" for c, _, n in targets), unit_count)

    print(f"\ncorpora:         {len(targets)}  ({sum(1 for c,_,_ in targets if c=='original')}"
          f" original / {sum(1 for c,_,_ in targets if c=='new')} new)")
    print(f"repo units:      {unit_count}")
    print(f".py files:       {stats['py_files']}  (parse failures: {len(stats['parse_failures'])})")
    print(f"agent sites:     {sum(1 for r in all_rows if r['kind'] == 'agent')}")
    print("wrote agent_sites.jsonl, repo_dialects.jsonl, aggregates.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
