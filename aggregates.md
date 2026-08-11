# CrewAI corpus survey — aggregates

Corpus root: `/home/user/crewAI-examples`

**Repo-unit note.** The spec defines `repo` as the first path component under the corpus root. This corpus is a single repository whose first level is category folders (`crews/`, `flows/`, `integrations/`, `notebooks/`), so that reading yields four rows and no usable dialect table. `repo` is therefore the project unit (nearest directory holding a manifest or `.py` files, capped at depth 3); `repo_top` on every row preserves the literal reading.

## 1. Totals

| Metric | Count |
|---|---|
| Repo units scanned | 31 |
| Top-level categories | 4 |
| .py files scanned | 116 |
| .ipynb files present (not parsed — see narrative) | 8 |
| Parse failures | 0 |
| Read failures | 0 |
| Files importing crewai symbols | 40 |
| Agent sites | 71 |
| Crew sites | 30 |
| Task sites | 81 |
| LLM sites | 2 |
| Agent sites in test/example paths | 0 |

No parse failures.

## 2. Kwarg frequency on `Agent(...)`

| Kwarg | Count | % of agents | Anticipated by spec |
|---|---|---|---|
| verbose | 63 | 88.7% | yes |
| config | 49 | 69.0% | yes |
| tools | 46 | 64.8% | yes |
| allow_delegation | 35 | 49.3% | yes |
| llm | 25 | 35.2% | yes |
| backstory | 22 | 31.0% | yes |
| goal | 22 | 31.0% | yes |
| role | 22 | 31.0% | yes |
| memory | 6 | 8.5% | yes |

Agents constructed with `**kwargs` unpacking: 0 (0.0%). Agents with positional args: 0 (0.0%).

## 3. `llm_shape` distribution

| llm_shape | Count | % of agents |
|---|---|---|
| absent | 46 | 64.8% |
| attribute | 15 | 21.1% |
| name | 9 | 12.7% |
| call | 1 | 1.4% |

## 4. `llm_call_callee` distribution

| Callee | Count |
|---|---|
| Ollama | 1 |

Constructors reached **indirectly** (the `llm=`/`function_calling_llm=` reference resolves to a call), from Pass B:

| Resolved callee | Count |
|---|---|
| Ollama | 9 |
| ChatOpenAI | 6 |
| LLM | 4 |
| nvllm | 4 |
| AzureChatOpenAI | 1 |

## 5. `llm_constant` values

| Model string | Count | Flags |
|---|---|---|
| (none) | 0 |  |

Model strings found on `LLM(...)`/`llm=Call(...)` sites (not `llm=` constants):

| Model string | Count | Flags |
|---|---|---|
| `gpt-4o` | 2 |  |

## 6. `ref_scope` distribution

All reference-valued kwargs on `Agent(...)`:

| ref_scope | Count | % of refs |
|---|---|---|
| self_attr | 15 | 62.5% |
| module | 9 | 37.5% |

`llm=` alone:

| ref_scope | Count | % of llm refs |
|---|---|---|
| self_attr | 15 | 62.5% |
| module | 9 | 37.5% |

`tools=` alone:

| ref_scope | Count |
|---|---|
| (none) | 0 |

Where `self.<attr>` references are actually bound:

| Binding site | Count |
|---|---|
| class_body | 8 |
| __init__ | 7 |

**Locally resolvable** (local / class_attr / module / self_attr): 24 of 24 (100.0%).

## 7. `tools_element_types` (summed across agents)

| Element node type | Count |
|---|---|
| Call | 49 |
| Attribute | 27 |
| Name | 12 |

`tools_shape`:

| tools_shape | Count | % of agents |
|---|---|---|
| list | 40 | 56.3% |
| absent | 25 | 35.2% |
| other | 6 | 8.5% |

What `tools_shape == "other"` actually is (no element list is recoverable from these without evaluating them):

| Node type | Count |
|---|---|
| Call | 4 |
| BinOp | 2 |

Reference scope of the **elements** inside `tools=[...]` (beyond the spec's kwarg-level Pass B, but it is what decides whether a tools list resolves):

| Element ref_scope | Count |
|---|---|
| namespace_attr | 27 |
| module | 8 |
| local | 3 |
| imported | 1 |

Most common tool expressions:

| Element | Count |
|---|---|
| `ScrapeWebsiteTool()` | 13 |
| `SerperDevTool()` | 10 |
| `BrowserTools.scrape_and_summarize_website` | 10 |
| `SearchTools.search_internet` | 10 |
| `TavilySearchResults()` | 4 |
| `SearchTools.search_instagram` | 4 |
| `search_tool` | 3 |
| `WebsiteSearchTool()` | 3 |
| `CalculatorTool()` | 3 |
| `web_search_tool` | 3 |
| `seper_dev_tool` | 3 |
| `CharacterCounterTool()` | 2 |
| `GmailGetThread(api_resource=gmail.api_resource)` | 2 |
| `CreateDraftTool.create_draft` | 2 |
| `SEC10QTool('AMZN')` | 2 |
| `SEC10KTool('AMZN')` | 2 |
| `file_read_tool` | 2 |
| `FileReadTool()` | 2 |
| `GmailGetThread(api_resource=self.gmail.api_resource)` | 2 |
| `markdown_validation_tool` | 1 |
| `CalculatorTools.calculate` | 1 |
| `LinkedInTool()` | 1 |
| `SEC10QTool()` | 1 |
| `SEC10KTool()` | 1 |
| `CSVSearchTool()` | 1 |

## 8. Construction surface

| Surface | Count | % of agents |
|---|---|---|
| decorated method (@agent) in @CrewBase class | 44 | 62.0% |
| plain method | 20 | 28.2% |
| module-level | 7 | 9.9% |

Cross-tab of the raw signals:

| in class | in func | func decorated | class decorated | in return | in list | Count |
|---|---|---|---|---|---|---|
| True | True | True | True | True | False | 44 |
| True | True | False | False | True | False | 17 |
| False | False | False | False | False | False | 7 |
| True | True | True | False | False | False | 3 |

Decorators observed on the enclosing function / class:

| Decorator | Scope | Count |
|---|---|---|
| `agent` | func | 44 |
| `tool('Scrape website content')` | func | 3 |
| `CrewBase` | class | 44 |

## 9. Import paths observed

| Import path (Agent) | Count |
|---|---|
| `crewai` | 71 |

All kinds:

| Kind | Import path | Count |
|---|---|---|
| task | `crewai` | 81 |
| agent | `crewai` | 71 |
| crew | `crewai` | 30 |
| llm | `crewai` | 2 |

## 10. `identity_fields_present`

| Identity fields | Count | % of agents |
|---|---|---|
| All three (role, goal, backstory) | 22 | 31.0% |
| Some (1-2) | 0 | 0.0% |
| None | 49 | 69.0% |

| Exact combination | Count |
|---|---|
| (none) | 49 |
| role,goal,backstory | 22 |

## 11. Repo dialects

| Repo | py | ipynb | agent sites | agents.yaml | tasks.yaml | crew.json(c) | agents/*.jsonc | manifest crewai | type | extras | crewai import | dialect_only | invisible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crews/game-builder-crew | 3 | 0 | 3 | Y | Y |  |  | Y |  |  | Y |  |  |
| crews/industry-agents | 0 | 1 | 0 |  |  |  |  |  |  |  |  |  | **YES** |
| crews/instagram_post | 6 | 0 | 6 |  |  |  |  | Y |  |  | Y |  |  |
| crews/job-posting | 3 | 0 | 3 | Y | Y |  |  | Y |  | tools | Y |  |  |
| crews/landing_page_generator | 8 | 0 | 6 | Y | Y |  |  | Y |  |  | Y |  |  |
| crews/markdown_validator | 4 | 0 | 1 | Y | Y |  |  | Y |  |  | Y |  |  |
| crews/marketing_strategy | 3 | 0 | 3 | Y | Y |  |  | Y |  | tools | Y |  |  |
| crews/match_profile_to_positions | 5 | 0 | 2 | Y | Y |  |  | Y |  | tools | Y |  |  |
| crews/meta_quest_knowledge | 4 | 0 | 1 | Y | Y |  |  | Y |  | tools | Y |  |  |
| crews/prep-for-a-meeting | 5 | 0 | 4 |  |  |  |  | Y |  |  | Y |  |  |
| crews/recruitment | 7 | 0 | 4 | Y | Y |  |  | Y |  | tools | Y |  |  |
| crews/screenplay_writer | 1 | 0 | 5 | Y | Y |  |  |  |  |  | Y |  |  |
| crews/starter_template | 3 | 0 | 2 |  |  |  |  |  |  |  | Y |  |  |
| crews/stock_analysis | 6 | 0 | 4 | Y | Y |  |  | Y |  | tools | Y |  |  |
| crews/surprise_trip | 5 | 0 | 3 | Y | Y |  |  | Y |  | tools | Y |  |  |
| crews/trip_planner | 7 | 0 | 4 |  |  |  |  | Y |  |  | Y |  |  |
| flows/content_creator_flow | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  | **YES** |
| flows/email_auto_responder_flow | 6 | 0 | 3 | Y | Y |  |  | Y |  | tools | Y |  |  |
| flows/lead-score-flow | 7 | 0 | 2 | Y | Y |  |  | Y |  | tools | Y |  |  |
| flows/meeting_assistant_flow | 6 | 0 | 1 | Y | Y |  |  | Y |  | tools | Y |  |  |
| flows/self_evaluation_loop_flow | 6 | 0 | 2 | Y | Y |  |  | Y |  | tools | Y |  |  |
| flows/write_a_book_with_flows | 5 | 0 | 4 | Y | Y |  |  | Y | flow | tools | Y |  |  |
| integrations/CrewAI-LangGraph | 10 | 0 | 3 |  |  |  |  | Y |  |  | Y |  |  |
| integrations/azure_model | 1 | 0 | 1 |  |  |  |  | Y |  |  | Y |  |  |
| integrations/nvidia_models/intro | 1 | 0 | 1 |  |  |  |  | Y |  |  | Y |  |  |
| integrations/nvidia_models/marketing_strategy | 4 | 1 | 3 | Y | Y |  |  | Y |  |  | Y |  |  |
| notebooks/Coding Assistant | 0 | 1 | 0 |  |  |  |  |  |  |  |  |  | **YES** |
| notebooks/Flows_101 | 0 | 1 | 0 |  |  |  |  |  |  |  |  |  | **YES** |
| notebooks/Landing Page Flow | 0 | 1 | 0 |  |  |  |  |  |  |  |  |  | **YES** |
| notebooks/QA Agent | 0 | 2 | 0 |  |  |  |  |  |  |  |  |  | **YES** |
| notebooks/Simple QA Crew + Flow | 0 | 1 | 0 |  |  |  |  |  |  |  |  |  | **YES** |

**dialect_only repos (spec definition — config/manifest signal but zero `Agent(...)` sites): 0 of 31 (0.0%)**

None. Every repo carrying `config/agents.yaml` also constructs `Agent(...)` in Python — the YAML dialect in this corpus is always *paired* with a `config=self.agents_config[...]` call site, never a replacement for one. The flag as specified therefore finds nothing here.

**Broader flag — repos an AST-only pass sees nothing in, for any reason: 7 of 31 (22.6%)**. This is the population `dialect_only` was meant to catch, and in this corpus the cause is notebooks, not config dialects:

- `crews/industry-agents` — notebook-only (0 .py, 1 .ipynb, 1 of them mentioning crewai)
- `flows/content_creator_flow` — no code at all (0 .py, 0 .ipynb, 0 of them mentioning crewai)
- `notebooks/Coding Assistant` — notebook-only (0 .py, 1 .ipynb, 1 of them mentioning crewai)
- `notebooks/Flows_101` — notebook-only (0 .py, 1 .ipynb, 1 of them mentioning crewai)
- `notebooks/Landing Page Flow` — notebook-only (0 .py, 1 .ipynb, 1 of them mentioning crewai)
- `notebooks/QA Agent` — notebook-only (0 .py, 2 .ipynb, 1 of them mentioning crewai)
- `notebooks/Simple QA Crew + Flow` — notebook-only (0 .py, 1 .ipynb, 1 of them mentioning crewai)

Notebook-only repos: **6 of 31 (19.4%)**. `.ipynb` is outside the `*.py` glob the spec defines, so none of their agent sites appear anywhere in Passes A or B.

## 12. Unrecognised kwargs on `Agent(...)`

| Kwarg | Count | % of agents | Example value | First seen |
|---|---|---|---|---|
| (none) | 0 | 0.0% |  |  |

Empty. Every kwarg in the corpus is already anticipated by the build spec.

The inverse is the more interesting result — spec-anticipated kwargs that **never appear** in the corpus:

| Anticipated kwarg | Occurrences |
|---|---|
| `apps` | 0 |
| `cache` | 0 |
| `function_calling_llm` | 0 |
| `max_iter` | 0 |
| `mcps` | 0 |
| `step_callback` | 0 |

6 of 15 anticipated kwargs are unused; 9 distinct kwargs carry the entire corpus.

## Appendix — kwargs on the other kinds

### `Crew(...)` — 30 sites

| Kwarg | Count | % of crews |
|---|---|---|
| agents | 30 | 100.0% |
| tasks | 30 | 100.0% |
| verbose | 26 | 86.7% |
| process | 24 | 80.0% |
| knowledge_sources | 1 | 3.3% |

### `Task(...)` — 81 sites

| Kwarg | Count | % of tasks |
|---|---|---|
| agent | 68 | 84.0% |
| config | 53 | 65.4% |
| description | 28 | 34.6% |
| expected_output | 16 | 19.8% |
| output_pydantic | 8 | 9.9% |
| output_json | 5 | 6.2% |
| context | 3 | 3.7% |
| async_execution | 2 | 2.5% |
| verbose | 1 | 1.2% |

### `LLM(...)` — 2 sites

| Kwarg | Count | % of llms |
|---|---|---|
| model | 2 | 100.0% |

