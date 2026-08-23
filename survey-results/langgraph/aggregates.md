# LangGraph corpus survey — aggregates

Corpora scanned in this run: `original:gemini-fullstack-langgraph-quickstart, original:graph_websearch_agent, original:company-research-agent, new:executive-ai-assistant`

**Part B is inherited verbatim** from the CrewAI v2 survey — same category set, same boundary rulings (class-body `self.x`; value-level-only `runtime_external`). Reachability numbers here are directly comparable to the CrewAI `llm=` table. **Part A is rebuilt**: a LangGraph graph is assembled imperatively, so the unit is a construction site plus the `add_node` calls bound to its builder variable.

## 1. Totals

| Metric | Count |
|---|---|
| Repos scanned | 4 |
| .py files scanned | 77 |
| .ipynb present (not parsed) | 1 |
| Parse failures | 0 |
| Read failures | 0 |
| Files importing langgraph symbols | 6 |
| Graph construction sites | 7 |
|   of which `state_graph` | 7 |
|   of which `message_graph` | 0 |
|   of which `react_agent` | 0 |
| `add_node` attachments | 40 |
| `add_edge` calls | 31 |
| `add_conditional_edges` calls | 6 |

No parse failures.

## 2. Raw-graph API vs `create_react_agent` — the dialect split

| API | Sites | % of graph sites |
|---|---|---|
| raw graph (`StateGraph` / `MessageGraph`) | 7 | 100.0% |
| prebuilt (`create_react_agent`) | 0 | 0.0% |

This is the LangGraph analog of a config dialect: it decides how much of the ecosystem each detection path covers. A scanner that only recognises `create_react_agent` would see 0.0% of this corpus.

**Lookalike callees — same name, different package.** These call a name in the target set but the binding does not come from `langgraph.*`, so they are correctly excluded. A name-only matcher would count them as LangGraph sites and be wrong:

| Site | Callee | Actually imported from |
|---|---|---|
| executive-ai-assistant/eaia/main/find_meeting_time.py:70 | `create_react_agent` | `langchain.agents.react.agent` |


## 3. Node-target reachability (inherited Part-B categories)

The `add_node` second argument, classified by the inherited resolver taxonomy. Directly comparable to CrewAI's `llm=` reachability table.

| Reachability | Count | % of nodes |
|---|---|---|
| `unresolved_local` | 13 | 32.5% |
| `namespace_attr` | 10 | 25.0% |
| `(not a reference — Lambda)` | 9 | 22.5% |
| `imported` | 8 | 20.0% |

**Boundary note — 13 of 40 node targets are names bound by a module-level `def`/`class` in the same file.** The inherited `module` scope is assignment-only (`Assign`/`AnnAssign`), so these classify as `unresolved_local` under the verbatim contract. In CrewAI this case never arose — kwarg values were never bare function names. It is recorded in `ref_module_def` rather than silently reclassified, so the cross-framework numbers stay comparable; **corrected, these are trivially resolvable and the addressable bucket shrinks accordingly.**

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
| `Name` | 21 | 52.5% |
| `Attribute` | 10 | 25.0% |
| `Lambda` | 9 | 22.5% |

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
| `module_level` | 21 | 52.5% |
| `same_method` | 10 | 25.0% |
| `same_function` | 9 | 22.5% |

| Scope distance | Site | Graph site | Enclosing |
|---|---|---|---|
| module_level | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:272 | `269` | — |
| module_level | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:273 | `269` | — |
| module_level | gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:274 | `269` | — |
| same_method | company-research-agent/backend/graph.py:59 | `56` | `_build_workflow` |
| same_method | company-research-agent/backend/graph.py:60 | `56` | `_build_workflow` |
| same_method | company-research-agent/backend/graph.py:61 | `56` | `_build_workflow` |
| same_function | graph_websearch_agent/agent_graph/graph.py:37 | `35` | `create_graph` |
| same_function | graph_websearch_agent/agent_graph/graph.py:55 | `35` | `create_graph` |
| same_function | graph_websearch_agent/agent_graph/graph.py:74 | `35` | `create_graph` |

## 5. Nodes and edges per graph

| Graph site | Kind | Builder | Nodes | Edges | Cond. edges |
|---|---|---|---|---|---|
| gemini-fullstack-langgraph-quickstart/backend/src/agent/graph.py:269 | `state_graph` | `builder` | 4 | 3 | 2 |
| graph_websearch_agent/agent_graph/graph.py:35 | `state_graph` | `graph` | 9 | 7 | 1 |
| company-research-agent/backend/graph.py:56 | `state_graph` | `self.workflow` | 10 | 6 | 0 |
| executive-ai-assistant/eaia/cron_graph.py:50 | `state_graph` | `graph` | 1 | 2 | 0 |
| executive-ai-assistant/eaia/reflection_graphs.py:97 | `state_graph` | `general_reflection_graph` | 1 | 2 | 0 |
| executive-ai-assistant/eaia/reflection_graphs.py:186 | `state_graph` | `multi_reflection_graph` | 2 | 1 | 0 |
| executive-ai-assistant/eaia/main/graph.py:162 | `state_graph` | `graph_builder` | 13 | 10 | 3 |

| Metric | min | max | mean | total |
|---|---|---|---|---|
| nodes per graph | 1 | 13 | 5.7 | 40 |
| edges per graph | 1 | 13 | 5.3 | 37 |

Edges and conditional edges are counted, not resolved — the number quantifies how much graph structure a node-only inventory ignores.

## 6. Import paths observed

| Import path | Kind | Count |
|---|---|---|
| `langgraph.graph` | state_graph | 7 |

| callee_form | Count |
|---|---|
| Name | 7 |

## 7. Reachability by cohort — read this first

| Reachability | new (n=17) | original (n=14) | Total |
|---|---|---|---|
| `unresolved_local` | 9 (52.9%) | 4 (28.6%) | 13 |
| `namespace_attr` | 0 (0.0%) | 10 (71.4%) | 10 |
| `imported` | 8 (47.1%) | 0 (0.0%) | 8 |

## 8. Per-repo (cohorts never blended)

| Cohort | Repo | .py | Graph sites | Nodes | Edges | APIs used |
|---|---|---|---|---|---|---|
| original | gemini-fullstack-langgraph-quickstart | 9 | 1 | 4 | 5 | state_graph |
| original | graph_websearch_agent | 25 | 1 | 9 | 8 | state_graph |
| original | company-research-agent | 25 | 1 | 10 | 6 | state_graph |
| new | executive-ai-assistant | 18 | 4 | 17 | 18 | state_graph |

