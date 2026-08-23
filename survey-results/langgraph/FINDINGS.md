# LangGraph corpus survey v1 — findings

`survey_lg.py`, one run, three repos, all `new` (first LangGraph run, so the
`original` cohort column is empty by construction).

**59 `.py` files, 0 parse failures, 3 graph construction sites, 23 `add_node`
attachments, 19 edges.** Node count reconciled against an independent
`grep -c add_node` sweep: 23 = 23.

| Cohort | Repo | `.py` | Graphs | Nodes | Edges | API |
|---|---|---|---|---|---|---|
| new | gemini-fullstack-langgraph-quickstart | 9 | 1 | 4 | 5 | `state_graph` |
| new | graph_websearch_agent | 25 | 1 | 9 | 8 | `state_graph` |
| new | company-research-agent | 25 | 1 | 10 | 6 | `state_graph` |

Part B was lifted from `survey_v2.py`'s **source text** rather than reimplemented,
so the categories and both forced boundary rulings (class-body `self.x`;
value-level-only `runtime_external`) are literally identical. The only edits are
the `TARGETS` constant and one basis string.

---

## 1. The dialect split: 100% raw graph, 0% `create_react_agent`

| API | Sites | Share |
|---|---|---|
| raw graph (`StateGraph`) | 3 | **100%** |
| prebuilt (`create_react_agent`) | 0 | **0%** |

Not one `create_react_agent` call, and no `MessageGraph`. **A detector built
only on the prebuilt path would see 0% of this corpus.** Every site imports from
`langgraph.graph`, every callee form is a bare `Name` — the alias and
`langgraph.graph.StateGraph(...)` paths never fire, exactly as
`callee_form == Name` held 213/213 in CrewAI.

---

## 2. Graph building stays in one scope — completely

| Scope distance | Count | Share |
|---|---|---|
| `same_method` | 10 | 43.5% |
| `same_function` | 9 | 39.1% |
| `module_level` | 4 | 17.4% |
| `cross_method_same_class` | **0** | 0% |
| `other` | **0** | 0% |

**Every one of the 23 `add_node` calls sits in the same scope as its
`StateGraph(...)` assignment.** The worry that motivated this measurement —
graph assembly split across methods, where a single-scope scanner finds the
graph but none of its nodes — does not occur here. Each repo picks one of three
idioms and stays in it:

- `builder = StateGraph(...)` at module level, `builder.add_node(...)` at module level (gemini)
- `graph = StateGraph(...)` inside `create_graph()`, all nodes in the same function (websearch)
- `self.workflow = StateGraph(...)` inside `_build_workflow()`, all nodes in the same method (company-research)

The builder-variable association is what makes this measurable, and it is
load-bearing: without it the `self.workflow` case would need matching on a
dotted expression rather than a name.

---

## 3. Node targets: **0 of 23 resolvable under the inherited contract**

| Reachability (verbatim) | Count | Share |
|---|---|---|
| `namespace_attr` | 10 | 43.5% |
| *(not a reference — `Lambda`)* | 9 | 39.1% |
| `unresolved_local` | 4 | 17.4% |

Nothing lands in `local`, `class_attr`, `module`, `self_attr` or
`terminal_constructor`. Set against CrewAI, where 11 of 19 references were
`terminal_constructor` and the model string was frequently in hand, **LangGraph
node targets are categorically harder** — but the reason is instructive, and two
of the three causes are cheap to fix.

**(a) 4 targets are module-level `def`s — a gap in the inherited contract.**
`builder.add_node("generate_query", generate_query)` where `generate_query` is a
`def` in the same file. The inherited `module` scope is assignment-only
(`Assign`/`AnnAssign`), so these fall to `unresolved_local`. In CrewAI the case
never arose — kwarg values were never bare function names. I recorded it in a
separate `ref_module_def` field rather than reclassifying, so the cross-framework
numbers stay comparable, but **these are trivially resolvable** and the honest
corrected figure counts them as reached. This is a boundary the inherited
contract does not cover, not a property of the code.

**(b) 10 targets are `self.<x>.run` — one attribute deeper than the rule reaches.**
The inherited `self_attr` rule requires the base to be literally `self`;
`self.ground.run` has base `self.ground`, so it is `namespace_attr`. Classifying
the *base* shows all 10 resolve:

| Base scope | Count | Base resolves to |
|---|---|---|
| `self_attr` | 10 | `GroundingNode()`, `Enricher()`, `Editor()`, … |

One extra attribute hop turns 43.5% of node targets from unresolved into
constructor-identified. This is the direct analog of the CrewAI class-body
ruling — the same shape of near-miss, one level along a different axis.

**(c) 9 targets are inline lambdas — genuinely not references.**

```python
graph.add_node("planner", lambda state: PlannerAgent(state=state, model=model, …).invoke(…))
```

There is nothing to resolve: the agent is constructed *inside* the lambda. The
constructors hiding there are the actual assets — `PlannerAgent`,
`SelectorAgent`, `ReporterAgent`, `ReviewerAgent`, `RouterAgent`,
`FinalReportAgent`, `EndNodeAgent`, plus `get_google_serper` / `scrape_website`.
**A node-target inventory that does not descend into lambda bodies reports 9
nodes with no discoverable asset, while 7 distinct agent classes sit one AST
level down.**

**Corrected reachability**, with the two extensions and lambdas counted honestly:

| | Count | Share |
|---|---|---|
| reachable (module `def` + one attribute hop) | **14** | **61%** |
| inline in a lambda — no reference exists | 9 | 39% |

---

## 4. Structure the node inventory ignores

19 edges (16 `add_edge` + 3 `add_conditional_edges`) across 3 graphs — a mean of
6.3 per graph against 7.7 nodes. **Edges are roughly as numerous as nodes**, so a
node-only inventory captures about half of what is written. Counted, not
resolved, per the spec.

---

## 5. Does this reorder resolver priorities relative to CrewAI?

Yes — the ranking is close to inverted.

| Capability | CrewAI evidence | LangGraph evidence |
|---|---|---|
| Class-body / `self` attribute resolution | 5 of 13 new-cohort refs | **10 of 23 node targets** (one hop deeper) |
| Module-level `def` binding | 0 (never arose) | **4 of 23** |
| Descend into lambdas | 0 | **9 of 23 — 7 agent classes** |
| Cross-module import following | 6 of 13 | **0** |
| Factory following | 0 at call sites | **0** |
| Function-local variables | 0 of 108 | **0 of 23** |

1. **Extend `self_attr` one attribute deeper.** Largest single win in this
   corpus (43.5%), and it generalises the ruling CrewAI already forced.
2. **Treat module-level `def`/`class` as `module` scope.** 17.4% here, zero cost,
   and it closes a real hole in the inherited contract.
3. **Descend into lambda bodies.** 39% of node targets, and the only way to see
   7 agent classes that currently appear nowhere.
4. **Cross-module following drops to last.** It was the top LangGraph-side
   candidate on the CrewAI evidence; here it fires **zero** times.
5. **`local` stays dead** — 0 of 23, matching 0 of 108 CrewAI sites. Five corpora
   and two frameworks now agree.

The framework-agnostic conclusion: the expensive capabilities (cross-module,
factory-following) keep failing to earn their place, while two cheap
one-hop extensions to attribute resolution keep being the thing that actually
moves the number — in both frameworks.

---

## Caveat

Three repos, 3 graph sites, 23 nodes — small, and one repo contributes all 9
lambdas while another contributes all 10 dotted targets. Each headline rests on
a single repo's idiom, so the *distribution* is not yet meaningful; the *shapes*
are real and none of them is currently handled. The 100%-in-scope result and the
0% `create_react_agent` result are the two that would most benefit from a fourth
and fifth repo before being relied on.
