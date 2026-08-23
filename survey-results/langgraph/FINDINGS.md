# LangGraph corpus survey — four repos

`survey_lg.py`, one run. Three `original` (the first LangGraph run) plus one
`new`: **`langchain-ai/executive-ai-assistant` @ `758db71`** — the first
LangGraph corpus written by the framework's own authors rather than a fork.

**77 `.py` files, 0 parse failures, 7 graph sites, 40 `add_node` attachments,
37 edges.** Node count reconciled against an independent grep: 40 = 17 + 23.

| Cohort | Repo | `.py` | Graphs | Nodes | Edges | API |
|---|---|---|---|---|---|---|
| original | gemini-fullstack-langgraph-quickstart | 9 | 1 | 4 | 5 | `state_graph` |
| original | graph_websearch_agent | 25 | 1 | 9 | 8 | `state_graph` |
| original | company-research-agent | 25 | 1 | 10 | 6 | `state_graph` |
| **new** | **executive-ai-assistant** | 18 | **4** | **17** | 18 | `state_graph` |

---

## A gap in my Part A, found by this repo

`executive-ai-assistant` uses LangGraph's **single-argument** `add_node` form:

```python
graph_builder.add_node(human_node)      # name inferred from the callable's __name__
graph_builder.add_node(triage_input)
```

My Part A assumed `add_node(name, target)` and took `args[1]` as the target. On
the first run against this repo that **silently dropped the target on 16 of 40
attachments (40%)** — they came back with `node_target_type: null` and no
reachability at all. Fixed: one positional arg is the *target*, and the node name
is inferred from it.

Corpus-wide the two forms are near-evenly split — **24 explicit names, 16
inferred from the callable**. Any detector that assumes the two-argument form
loses 40% of node targets, and loses them quietly, which is worse than losing
them loudly.

## And a lookalike the import map correctly refused

`eaia/main/find_meeting_time.py:70` calls `create_react_agent(llm, [...])` — but
imported from **`langchain.agents.react.agent`**, not `langgraph.prebuilt`. Same
name, different package, different API. The import map declined it; a name-only
matcher would have counted it as a LangGraph react-agent site and been wrong.
This is the direct analog of `crewai` vs `crewai_tools` in the CrewAI survey, and
it is now recorded in its own table rather than being invisibly correct.

---

## Correction: "0% `create_react_agent`" was a misleading headline

It was in the aggregates — a "Lookalike callees" table under the split — but as a
footnote beneath a headline reading **0**, which invites exactly the wrong
conclusion. The corpus *does* construct a ReAct agent:

```python
# eaia/main/find_meeting_time.py:70
from langchain.agents.react.agent import create_react_agent   # NOT langgraph.prebuilt
llm = ChatOpenAI(model=config["configurable"].get("model", "gpt-4o"), temperature=0)
agent = create_react_agent(llm, [get_events_for_days])
```

Excluding it from the *graph-site* census is right — it builds a Runnable, not a
graph, and the spec scopes detection to `langgraph.*` module paths. But
"0 LangGraph prebuilt sites" and "no react agents in this corpus" are different
statements, and I let the first stand in for the second. Table 2 now carries it
as an explicit third row with the distinction spelled out.

## The bigger miss it exposed: node bodies are where the assets live

`find_meeting_time` is not some peripheral file — it is **one of the 17 nodes**,
attached at `graph.py:180`. The agent, its `ChatOpenAI` model, the default model
string `"gpt-4o"`, and its tool all sit *inside* that node's body. My Part A
records a node's **name** and stops.

Censusing node bodies that resolve to a `def` in the same module:

| Node body | Count | Share |
|---|---|---|
| visible (`def` in the same module) | 13 | 32.5% |
| **not inspectable** (imported, lambda, dotted) | **27** | **67.5%** |

**8 of 40 nodes construct something in their body** — `ChatGoogleGenerativeAI` ×3,
`ChatOpenAI` ×2, `ChatAnthropic`, plus `Send`/`Command` control-flow objects.
None of it appears in the graph-site or node-target tables.

And that count is a floor, because it only covers the 32.5% of bodies that are
visible at all. `find_meeting_time` is imported across a module boundary, so it
falls in the 67.5% — the corpus's one react agent is inside the part of the blind
spot the survey cannot see into. Repo-wide there are **14** `ChatOpenAI` /
`ChatAnthropic` / `ChatGoogleGenerativeAI` constructions; the graph census
attributes zero of them to any node.

**This reframes the LangGraph result.** The node-target reachability numbers
answer "can I resolve the name?" — but even a perfect answer yields a function
name, not a model or a tool. For CrewAI the assets are kwargs on the
construction call. For LangGraph they are two levels down: `add_node` → function
→ body. A node-name inventory is roughly the LangGraph equivalent of listing
CrewAI agents without ever reading `llm=` or `tools=`.

---

## 1. The dialect split holds — for LangGraph's own prebuilt API: still 100% raw graph, 0% prebuilt

| API | Sites | Share |
|---|---|---|
| raw graph (`StateGraph`) | 7 | **100%** |
| prebuilt (`create_react_agent`) | 0 | **0%** |

I flagged the 0% result last run as resting on three repos and wanting a fourth.
The fourth is by the framework's own authors and still contributes zero
**LangGraph** prebuilt sites — but it does call a same-named LangChain
constructor, which is why the headline needed the correction above.

## 2. Graph building stays in scope — now 40 for 40

| Scope distance | Count | Share |
|---|---|---|
| `module_level` | 21 | 52.5% |
| `same_method` | 10 | 25.0% |
| `same_function` | 9 | 22.5% |
| `cross_method_same_class` | **0** | 0% |
| `other` | **0** | 0% |

The new repo builds four separate graphs, all at module level, and every node
attaches in the same scope as its builder. Across four repos and seven graphs,
**not one `add_node` is separated from its `StateGraph(...)` by a scope
boundary.** This is now the most robust result in the LangGraph survey.

Multi-graph repos are also newly represented: `executive-ai-assistant` has four
graphs across three files, from a 1-node graph to a 13-node one. Builder-variable
association carries that without ambiguity.

---

## 3. Node-target reachability — the new repo shifts it

| Reachability (verbatim) | new (n=17) | original (n=14) | Total |
|---|---|---|---|
| `unresolved_local` | 9 (53%) | 4 (29%) | 13 |
| `namespace_attr` | 0 | 10 (71%) | 10 |
| **`imported`** | **8 (47%)** | **0** | **8** |
| *(Lambda — not a reference)* | 0 | 9 | 9 |

Two things changed:

**`imported` appears for the first time — 8 of 17 new-cohort targets.** Last run
I wrote that cross-module following "fires zero times" in LangGraph and ranked it
last. On the fourth repo it is 47% of node targets. That reranking was premature
and I'm correcting it: node functions imported from sibling modules
(`from eaia.main.triage import triage_input`) are a real and common shape.

**All 17 new-cohort targets are bare `Name`s** — no lambdas, no dotted
attributes. The lambda idiom (39% of the original cohort) and the `self.<x>.run`
idiom (71%) are each confined to a single repo. Four repos, four distinct
node-target idioms, with almost no overlap between them.

Corrected reachability across all 40, applying the two cheap extensions:

| | Count | Share |
|---|---|---|
| module-level `def` in the same file | 13 | 33% |
| one attribute hop (`self.x.run` → `self.x`) | 10 | 25% |
| cross-module import (one hop, not followed here) | 8 | 20% |
| inline lambda — no reference exists | 9 | 22% |

**0 of 40 resolve under the verbatim contract; 23 of 40 (58%) resolve with two
one-hop extensions; 31 of 40 (78%) with cross-module following added.**

---

## 4. Structure ignored

37 edges (34 `add_edge` + 3 `add_conditional_edges`) against 40 nodes — mean 5.3
edges vs 5.7 nodes per graph. Edges remain roughly as numerous as nodes, so a
node-only inventory still captures about half of what is written.

---

## 5. Resolver priorities, corrected

| Capability | CrewAI | LangGraph (3 repos) | LangGraph (4 repos) |
|---|---|---|---|
| Module-level `def` binding | 0 | 4 of 23 | **13 of 40 (33%)** |
| Deeper `self`/attribute resolution | 5 of 13 | 10 of 23 | 10 of 40 (25%) |
| Cross-module import following | 6 of 13 | **0** | **8 of 40 (20%)** |
| Descend into lambdas | 0 | 9 of 23 | 9 of 40 (22%) |
| Factory following | 0 | 0 | **0** |
| Function-local variables | 0 of 108 | 0 of 23 | **0 of 40** |

1. **Treat module-level `def`/`class` as `module` scope.** Now the single largest
   category at 33%, up from 17% on three repos. It is a hole in the inherited
   contract, not a property of the code, and it costs nothing to close.
2. **Cross-module import following returns to contention** — 20%, and the only
   capability that appears in *both* frameworks' evidence (6 of 13 CrewAI
   references, 8 of 40 LangGraph node targets). Last run I ranked it last on
   LangGraph evidence; that was wrong on one more repo.
3. **Deeper attribute resolution** (25%) and **lambda descent** (22%) stay
   valuable but are each single-repo idioms so far — they should be weighted as
   shapes to handle, not as frequencies to plan around.
4. **Factory following: 0 across both frameworks and every repo.** It has now
   failed to earn its place on nine repositories.
5. **`local`: 0 of 148 sites** across two frameworks, nine repos. Settled.

---

## Caveat

Four LangGraph repos, 40 node attachments. The two results I would now defend
are the scope-distance one (40/40, four repos, three idioms) and the
`create_react_agent` 0% (survived the framework-authors test). Everything about
the *distribution* of node-target shapes remains one-repo-per-idiom, and the
`imported` reranking above is a reminder that a single additional repo has twice
now overturned a priority ordering I stated with more confidence than four data
points support.
