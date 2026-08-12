# CrewAI corpus survey — aggregates

Corpus root: `/home/user/crewAI-examples`

**Repo-unit note.** The spec defines `repo` as the first path component under the corpus root. Here the first level is `crews/` — 1 component(s) covering 3 actual projects, so the literal reading would collapse the dialect table. `repo` is therefore the project unit (nearest directory holding a manifest or code, capped at depth 3); `repo_top` on every row preserves the literal reading.

## 1. Totals

| Metric | Count |
|---|---|
| Repo units scanned | 3 |
| Top-level categories | 1 |
| .py files scanned | 14 |
| .ipynb files present (not parsed — see narrative) | 0 |
| Parse failures | 0 |
| Read failures | 0 |
| Files importing crewai symbols | 6 |
| Agent sites | 13 |
| Crew sites | 3 |
| Task sites | 14 |
| LLM sites | 0 |
| Agent sites in test/example paths | 0 |

No parse failures.

## 2. Kwarg frequency on `Agent(...)`

| Kwarg | Count | % of agents | Anticipated by spec |
|---|---|---|---|
| verbose | 12 | 92.3% | yes |
| config | 9 | 69.2% | yes |
| tools | 7 | 53.8% | yes |
| allow_delegation | 6 | 46.2% | yes |
| backstory | 4 | 30.8% | yes |
| goal | 4 | 30.8% | yes |
| role | 4 | 30.8% | yes |
| llm | 4 | 30.8% | yes |

Agents constructed with `**kwargs` unpacking: 0 (0.0%). Agents with positional args: 0 (0.0%).

## 3. `llm_shape` distribution

| llm_shape | Count | % of agents |
|---|---|---|
| absent | 9 | 69.2% |
| name | 4 | 30.8% |

## 4. `llm_call_callee` distribution

No `llm=` kwarg is a direct call at an Agent site.

Constructors reached **indirectly** (the `llm=`/`function_calling_llm=` reference resolves to a call), from Pass B:

| Resolved callee | Count |
|---|---|
| Ollama | 4 |

## 5. `llm_constant` values

| Model string | Count | Flags |
|---|---|---|
| (none) | 0 |  |

Model strings found inside constructor calls (`LLM(...)`, `llm=Call(...)`, or whatever a reference resolved to):

| Model string | Count | Flags |
|---|---|---|
| `llama3.1` | 4 |  |

## 6. `ref_scope` distribution

All reference-valued kwargs on `Agent(...)`:

| ref_scope | Count | % of refs |
|---|---|---|
| module | 4 | 100.0% |

`llm=` alone:

| ref_scope | Count | % of llm refs |
|---|---|---|
| module | 4 | 100.0% |

`tools=` alone:

| ref_scope | Count |
|---|---|
| (none) | 0 |

Where `self.<attr>` references are actually bound:

| Binding site | Count |
|---|---|
| (none) | 0 |

**Locally resolvable** (local / class_attr / module / self_attr): 4 of 4 (100.0%).

## 7. `tools_element_types` (summed across agents)

| Element node type | Count |
|---|---|
| Call | 16 |
| Attribute | 7 |

`tools_shape`:

| tools_shape | Count | % of agents |
|---|---|---|
| list | 7 | 53.8% |
| absent | 6 | 46.2% |

Reference scope of the **elements** inside `tools=[...]` (beyond the spec's kwarg-level Pass B, but it is what decides whether a tools list resolves):

| Element ref_scope | Count |
|---|---|
| namespace_attr | 7 |

Most common tool expressions:

| Element | Count |
|---|---|
| `ScrapeWebsiteTool()` | 4 |
| `SearchTools.search_internet` | 3 |
| `BrowserTools.scrape_and_summarize_website` | 3 |
| `WebsiteSearchTool()` | 3 |
| `CalculatorTool()` | 3 |
| `SEC10QTool('AMZN')` | 2 |
| `SEC10KTool('AMZN')` | 2 |
| `CalculatorTools.calculate` | 1 |
| `SEC10QTool()` | 1 |
| `SEC10KTool()` | 1 |

## 8. Construction surface

| Surface | Count | % of agents |
|---|---|---|
| module-level | 5 | 38.5% |
| plain method | 4 | 30.8% |
| decorated method (@agent) in @CrewBase class | 4 | 30.8% |

Cross-tab of the raw signals:

| in class | in func | func decorated | class decorated | in return | in list | Count |
|---|---|---|---|---|---|---|
| False | False | False | False | False | False | 5 |
| True | True | True | True | True | False | 4 |
| True | True | False | False | True | False | 3 |
| True | True | True | False | False | False | 1 |

Decorators observed on the enclosing function / class:

| Decorator | Scope | Count |
|---|---|---|
| `agent` | func | 4 |
| `tool('Scrape website content')` | func | 1 |
| `CrewBase` | class | 4 |

## 9. Import paths observed

| Import path (Agent) | Count |
|---|---|
| `crewai` | 13 |

All kinds:

| Kind | Import path | Count |
|---|---|---|
| task | `crewai` | 14 |
| agent | `crewai` | 13 |
| crew | `crewai` | 3 |

## 10. `identity_fields_present`

| Identity fields | Count | % of agents |
|---|---|---|
| All three (role, goal, backstory) | 4 | 30.8% |
| Some (1-2) | 0 | 0.0% |
| None | 9 | 69.2% |

| Exact combination | Count |
|---|---|
| (none) | 9 |
| role,goal,backstory | 4 |

## 11. Repo dialects

| Repo | py | ipynb | agent sites | agents.yaml | tasks.yaml | crew.json(c) | agents/*.jsonc | manifest crewai | pin | type | extras | crewai import | dialect_only | invisible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crews/screenplay_writer | 1 | 0 | 5 | Y | Y |  |  |  |  |  |  | Y |  |  |
| crews/stock_analysis | 6 | 0 | 4 | Y | Y |  |  | Y | >=0.152.0 |  | tools | Y |  |  |
| crews/trip_planner | 7 | 0 | 4 |  |  |  |  | Y | >=0.152.0 |  |  | Y |  |  |

**dialect_only repos (spec definition — config/manifest signal but zero `Agent(...)` sites): 0 of 3 (0.0%)**

None. All 2 repo(s) carrying `config/agents.yaml` also construct `Agent(...)` in Python — the YAML dialect here is always *paired* with a `config=` call site, never a replacement for one. The flag as specified therefore finds nothing in this corpus.

**Broader flag — repos an AST-only pass sees nothing in, for any reason: 0 of 3 (0.0%)**. This is the population `dialect_only` was meant to catch; here it is empty:


No notebook-only repos (0 `.ipynb` files in the corpus). The `*.py`-glob blind spot does not bite here.

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
| `memory` | 0 |
| `step_callback` | 0 |

7 of 15 anticipated kwargs are unused; 8 distinct kwargs carry the entire corpus.

## Appendix — kwargs on the other kinds

### `Crew(...)` — 3 sites

| Kwarg | Count | % of crews |
|---|---|---|
| agents | 3 | 100.0% |
| tasks | 3 | 100.0% |
| verbose | 3 | 100.0% |
| process | 2 | 66.7% |

### `Task(...)` — 14 sites

| Kwarg | Count | % of tasks |
|---|---|---|
| agent | 14 | 100.0% |
| description | 9 | 64.3% |
| expected_output | 8 | 57.1% |
| config | 5 | 35.7% |

### `LLM(...)` — 0 sites

| Kwarg | Count | % of llms |
|---|---|---|
| (none) | 0 | 0.0% |

