# LangGraph corpus survey — aggregates

Corpora scanned in this run: `new:gemini-fullstack-langgraph-quickstart, new:graph_websearch_agent, new:company-research-agent`

**Part B is inherited verbatim** from the CrewAI v2 survey — same category set, same boundary rulings (class-body `self.x`; value-level-only `runtime_external`). Reachability numbers here are directly comparable to the CrewAI `llm=` table. **Part A is rebuilt**: a LangGraph graph is assembled imperatively, so the unit is a construction site plus the `add_node` calls bound to its builder variable.

## 1. Totals

| Metric | Count |
|---|---|
| Repos scanned | 3 |
| .py files scanned | 59 |
| .ipynb present (not parsed) | 1 |
| Parse failures | 0 |
| Read failures | 0 |
| Files importing langgraph symbols | 3 |
| Graph construction sites | 3 |
|   of which `state_graph` | 3 |
|   of which `message_graph` | 0 |
|   of which `react_agent` | 0 |
| `add_node` attachments | 23 |
| `add_edge` calls | 16 |
| `add_conditional_edges` calls | 3 |

No parse failures.

## 2. Raw-graph API vs `create_react_agent` — the dialect split

| API | Sites | % of graph sites |
|---|---|---|
| raw graph (`StateGraph` / `MessageGraph`) | 3 | 100.0% |
| prebuilt (`create_react_agent`) | 0 | 0.0% |

This is the LangGraph analog of a config dialect: it decides how much of the ecosystem each detection path covers. A scanner that only recognises `create_react_agent` would see 0.0% of this corpus.

## 3. Node-target reachability (inherited Part-B categories)

The `add_node` second argument, classified by the inherited resolver taxonomy. Directly comparable to CrewAI's `llm=` reachability table.

| Reachability | Count | % of nodes |
|---|---|---|
| `namespace_attr` | 10 | 43.5% |
| `(not a reference — Lambda)` | 9 | 39.1% |
| `unresolved_local` | 4 | 17.4% |

**Boundary note — 4 of 23 node targets are names bound by a module-level `def`/`class` in the same file.** The inherited `module` scope is assignment-only (`Assign`/`AnnAssign`), so these classify as `unresolved_local` under the verbatim contract. In CrewAI this case never arose — kwarg values were never bare function names. It is recorded in `ref_module_def` rather than silently reclassified, so the cross-framework numbers stay comparable; **corrected, these are trivially resolvable and the addressable bucket shrinks accordingly.**

**One level deeper.** For dotted targets (`self.ground.run`) the inherited rule is `namespace_attr` because the base is not literally `self`. Classifying the *base* expression shows how much a one-attribute-deeper resolver would reach:

| Base scope | Count | Example base resolves to |
|---|---|---|
| `self_attr` | 10 | `GroundingNode()` |

**Inline lambdas.** 9 node targets are lambdas — no reference to resolve, because the work is written inline. The constructors called inside them are where the agent actually lives:

| Callee inside lambda | Occurrences |
|---|---|
| `get_agent_graph_state` | 8 |
| `invoke` | 7 |
| `PlannerAgent` | 1 |
| `SelectorAgent` | 1 |
| `ReporterAgent` | 1 |
| `ReviewerAgent` | 1 |
| `RouterAgent` | 1 |
| `get_google_serper` | 1 |
| `scrape_website` | 1 |
| `FinalReportAgent` | 1 |
| `EndNodeAgent` | 1 |

Node-target node types (what the second argument syntactically is):

| AST node type | Count | % of nodes |
|---|---|---|
| `Attribute` | 10 | 43.5% |
| `Lambda` | 9 | 39.1% |
| `Name` | 4 | 17.4% |

Examples (`file:line`):

| Reachability | Site | Node name | Target |
|---|---|---|---|
| unresolved_local | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:272 | `generate_query` | `generate_query` |
| unresolved_local | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:273 | `web_research` | `web_research` |
| unresolved_local | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:274 | `reflection` | `reflection` |
| unresolved_local | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:275 | `finalize_answer` | `finalize_answer` |
| (not a reference — Lambda) | graph_websearch_agent/agent_graph/graph.py:37 | `planner` | `lambda state: PlannerAgent(state=state, model=model, server=` |
| (not a reference — Lambda) | graph_websearch_agent/agent_graph/graph.py:55 | `selector` | `lambda state: SelectorAgent(state=state, model=model, server` |
| (not a reference — Lambda) | graph_websearch_agent/agent_graph/graph.py:74 | `reporter` | `lambda state: ReporterAgent(state=state, model=model, server` |
| (not a reference — Lambda) | graph_websearch_agent/agent_graph/graph.py:92 | `reviewer` | `lambda state: ReviewerAgent(state=state, model=model, server` |
| (not a reference — Lambda) | graph_websearch_agent/agent_graph/graph.py:116 | `router` | `lambda state: RouterAgent(state=state, model=model, server=s` |
| (not a reference — Lambda) | graph_websearch_agent/agent_graph/graph.py:141 | `serper_tool` | `lambda state: get_google_serper(state=state, plan=lambda: ge` |
| (not a reference — Lambda) | graph_websearch_agent/agent_graph/graph.py:149 | `scraper_tool` | `lambda state: scrape_website(state=state, research=lambda: g` |
| (not a reference — Lambda) | graph_websearch_agent/agent_graph/graph.py:157 | `final_report` | `lambda state: FinalReportAgent(state=state).invoke(final_res` |

## 4. Scope distance from `StateGraph` assignment to `add_node`

The real-world test of whether graph building stays inside one scope. A scanner whose scope logic assumes one function finds nothing in the rows below `same_function` / `same_method`.

| Scope distance | Count | % of nodes |
|---|---|---|
| `same_method` | 10 | 43.5% |
| `same_function` | 9 | 39.1% |
| `module_level` | 4 | 17.4% |

| Scope distance | Site | Graph site | Enclosing |
|---|---|---|---|
| same_method | company-research-agent/backend/graph.py:59 | `56` | `_build_workflow` |
| same_method | company-research-agent/backend/graph.py:60 | `56` | `_build_workflow` |
| same_method | company-research-agent/backend/graph.py:61 | `56` | `_build_workflow` |
| same_function | graph_websearch_agent/agent_graph/graph.py:37 | `35` | `create_graph` |
| same_function | graph_websearch_agent/agent_graph/graph.py:55 | `35` | `create_graph` |
| same_function | graph_websearch_agent/agent_graph/graph.py:74 | `35` | `create_graph` |
| module_level | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:272 | `269` | — |
| module_level | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:273 | `269` | — |
| module_level | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:274 | `269` | — |

## 5. Nodes and edges per graph

| Graph site | Kind | Builder | Nodes | Edges | Cond. edges |
|---|---|---|---|---|---|
| gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:269 | `state_graph` | `builder` | 4 | 3 | 2 |
| graph_websearch_agent/agent_graph/graph.py:35 | `state_graph` | `graph` | 9 | 7 | 1 |
| company-research-agent/backend/graph.py:56 | `state_graph` | `self.workflow` | 10 | 6 | 0 |

| Metric | min | max | mean | total |
|---|---|---|---|---|
| nodes per graph | 4 | 10 | 7.7 | 23 |
| edges per graph | 5 | 8 | 6.3 | 19 |

Edges and conditional edges are counted, not resolved — the number quantifies how much graph structure a node-only inventory ignores.

## 6. Import paths observed

| Import path | Kind | Count |
|---|---|---|
| `langgraph.graph` | state_graph | 3 |

| callee_form | Count |
|---|---|
| Name | 3 |

## 7. Reachability by cohort — read this first

| Reachability | new (n=14) | original (n=0) | Total |
|---|---|---|---|
| `namespace_attr` | 10 (71.4%) | 0 (0.0%) | 10 |
| `unresolved_local` | 4 (28.6%) | 0 (0.0%) | 4 |

The `original` column is empty: this is the first LangGraph run, so all three repos are `new`. The cross-framework comparison against CrewAI is in the narrative rather than this table.

## 8. Per-repo (cohorts never blended)

| Cohort | Repo | .py | Graph sites | Nodes | Edges | APIs used |
|---|---|---|---|---|---|---|
| new | gemini-fullstack-langgraph-quickstart | 9 | 1 | 4 | 5 | state_graph |
| new | graph_websearch_agent | 25 | 1 | 9 | 8 | state_graph |
| new | company-research-agent | 25 | 1 | 10 | 6 | state_graph |

