# CrewAI corpus survey v2 — aggregates

Corpora scanned in this run: `original:crewAI-examples, original:academic-commercialization-agent, original:ai-crewai-multi-agent, original:PurpleCrew, new:AITradingCrew`

**v2 changes against v1.** Pass B's `Call` case is split into `terminal_constructor` / `factory_call` / `call_unknown` (`ref_call_kind`); `argument_passed` is a scope of its own; v1's `unresolved` is split into `runtime_external` (provably execution-time) and `unresolved_local` (addressable). Every corpus below went through v2 in one run, so all counts share these categories. Repos are labelled `original` (the four already surveyed) or `new`.

**Reading `imported`.** The survey does not cross module boundaries, so a cross-module import is unresolved-but-addressable. `ref_scope` keeps `imported` because the distinction is informative; the reachability table folds it into `unresolved_local` and shows the split.

**Repo-unit note.** A corpus root carrying its own packaging manifest is one unit; otherwise units are the nearest directories holding a manifest or code, capped at depth 3. `repo_top` preserves the literal first-component reading.

## 1. Totals

| Metric | Count |
|---|---|
| Corpora scanned | 5 |
| Repo units scanned | 7 |
| Top-level categories | 2 |
| .py files scanned | 110 |
| .ipynb files present (not parsed — see narrative) | 0 |
| Parse failures | 0 |
| Read failures | 0 |
| Files importing crewai symbols | 15 |
| Agent sites | 45 |
| Crew sites | 11 |
| Task sites | 59 |
| LLM sites | 2 |
| Agent sites in test/example paths | 0 |

No parse failures.

## 2. Kwarg frequency on `Agent(...)`

| Kwarg | Count | % of agents | Anticipated by spec |
|---|---|---|---|
| config | 41 | 91.1% | yes |
| verbose | 32 | 71.1% | yes |
| allow_delegation | 21 | 46.7% | yes |
| llm | 20 | 44.4% | yes |
| tools | 18 | 40.0% | yes |
| backstory | 4 | 8.9% | yes |
| goal | 4 | 8.9% | yes |
| role | 4 | 8.9% | yes |
| inject_date | 3 | 6.7% | **NO** |

Agents constructed with `**kwargs` unpacking: 0 (0.0%). Agents with positional args: 0 (0.0%).

## 3. `llm_shape` distribution

| llm_shape | Count | % of agents |
|---|---|---|
| absent | 25 | 55.6% |
| name | 10 | 22.2% |
| call | 6 | 13.3% |
| attribute | 4 | 8.9% |

## 4. `llm_call_callee` distribution

| Callee | Count |
|---|---|
| create_llm | 6 |

Constructors reached **indirectly** (the `llm=`/`function_calling_llm=` reference resolves to a call), from Pass B:

| Resolved callee | Count |
|---|---|
| Ollama | 4 |
| ChatOpenAI | 2 |

## 5. `llm_constant` values

| Model string | Count | Flags |
|---|---|---|
| (none) | 0 |  |

**Constant model strings on kwargs other than `Agent(llm=)`** — these are invisible to the table above:

| Kind | Kwarg | Value | Count | Flags |
|---|---|---|---|---|
| crew | manager_llm | `GPT-4o` | 2 | **not lowercase — LiteLLM ids are lowercase** |

Model strings found inside constructor calls (`LLM(...)`, `llm=Call(...)`, or whatever a reference resolved to):

| Model string | Count | Flags |
|---|---|---|
| `llama3.1` | 4 |  |
| `gpt-4-turbo` | 2 |  |

## 6. `ref_scope` distribution

All reference-valued kwargs on `Agent(...)`:

| ref_scope | Count | % of refs |
|---|---|---|
| imported | 6 | 42.9% |
| module | 4 | 28.6% |
| self_attr | 2 | 14.3% |
| unresolved_local | 2 | 14.3% |

`llm=` alone:

| ref_scope | Count | % of llm refs |
|---|---|---|
| imported | 6 | 42.9% |
| module | 4 | 28.6% |
| self_attr | 2 | 14.3% |
| unresolved_local | 2 | 14.3% |

`tools=` alone:

| ref_scope | Count |
|---|---|
| (none) | 0 |

Where `self.<attr>` references are actually bound:

| Binding site | Count |
|---|---|
| __init__ | 2 |

**Locally resolvable** (local / class_attr / module / self_attr): 6 of 14 (42.9%).

### 6a. `ref_call_kind` — the Call split (v2 Change 1)

Sub-classification of references whose resolved RHS is a call. This is what decides whether factory-following is worth building.

| ref_call_kind | Count | % of call-valued refs | of which `llm=` |
|---|---|---|---|
| terminal_constructor | 6 | 100.0% | 6 |

Spot-check examples (up to 3 per bucket, with `file:line`):

| Bucket | Site | Kwarg | Resolved RHS | Why |
|---|---|---|---|---|
| terminal_constructor | crewAI-examples/crews/stock_analysis/src/stock_analysis/crew.py:23 | `llm=` | `Ollama(model='llama3.1')` | imported from `langchain.llms`, class by PEP 8 naming |
| terminal_constructor | crewAI-examples/crews/stock_analysis/src/stock_analysis/crew.py:46 | `llm=` | `Ollama(model='llama3.1')` | imported from `langchain.llms`, class by PEP 8 naming |
| terminal_constructor | crewAI-examples/crews/stock_analysis/src/stock_analysis/crew.py:67 | `llm=` | `Ollama(model='llama3.1')` | imported from `langchain.llms`, class by PEP 8 naming |

### 6b. Reachability by cohort (v2 Change 5) — read this first

One row per reachability category, cross-tabbed against the `original` and `new` cohorts. A call-valued reference is reported by its `ref_call_kind`; everything else by its `ref_scope`.

| Reachability | new (n=8) | original (n=6) | Total |
|---|---|---|---|
| `terminal_constructor` | 0 (0.0%) | 6 (100.0%) | 6 |
| `imported` | 6 (75.0%) | 0 (0.0%) | 6 |
| `unresolved_local` | 2 (25.0%) | 0 (0.0%) | 2 |

Addressable bucket = `unresolved_local` (2) + `imported` (6) = **8**; provably terminal = `runtime_external` (0).

### 6c. Local-variable references by cohort (v2 Change 4)

| Cohort | `local` refs | All refs | % local |
|---|---|---|---|
| new | 0 | 8 | 0.0% |
| original | 0 | 6 | 0.0% |

v1 measured 0 local-variable references across 95 agents. This table is the check on whether that still holds for the `new` cohort — the deferred function-scope walker is only worth reviving if it climbs here.

### 6d. Binding census — call-valued bindings a reference could resolve to

Agent kwargs only ever see one module, so `factory_call` can look empty at the call site while factories exist one import away. This censuses every module-level and class-body binding whose RHS is a call, across every file scanned — the population a cross-module resolver would reach.

| call_kind | new (n=18) | original (n=29) | Total |
|---|---|---|---|
| `terminal_constructor` | 8 (44.4%) | 24 (82.8%) | 32 |
| `call_unknown` | 5 (27.8%) | 5 (17.2%) | 10 |
| `factory_call` | 5 (27.8%) | 0 (0.0%) | 5 |

Spot-check examples (up to 3 per bucket, with `file:line`):

| Bucket | Site | Binds | RHS | Why |
|---|---|---|---|---|
| factory_call | AITradingCrew/ai_trading_crew/config.py:150 | `DEFAULT_STOCKTWITS_LLM` | `create_default_llm('OPENROUTER_API_KEY', 'OPENROUTER_DEE` | matches a def in this module |
| factory_call | AITradingCrew/ai_trading_crew/config.py:151 | `DEFAULT_TI_LLM` | `create_default_llm('OPENROUTER_API_KEY', 'OPENROUTER_DEE` | matches a def in this module |
| factory_call | AITradingCrew/ai_trading_crew/config.py:152 | `DEEPSEEK_OPENROUTER_LLM` | `create_default_llm('OPENROUTER_API_KEY', 'OPENROUTER_DEE` | matches a def in this module |
| terminal_constructor | crewAI-examples/crews/screenplay_writer/screenplay_writer.py:22 | `spamfilter` | `Agent(config=agents_config['spamfilter'], allow_delegati` | CrewAI constructor |
| terminal_constructor | crewAI-examples/crews/screenplay_writer/screenplay_writer.py:26 | `analyst` | `Agent(config=agents_config['analyst'], allow_delegation=` | CrewAI constructor |
| terminal_constructor | crewAI-examples/crews/screenplay_writer/screenplay_writer.py:28 | `scriptwriter` | `Agent(config=agents_config['scriptwriter'], allow_delega` | CrewAI constructor |
| call_unknown | crewAI-examples/crews/screenplay_writer/screenplay_writer.py:10 | `current_dir` | `Path.cwd()` | callee neither defined nor imported in this module |
| call_unknown | crewAI-examples/crews/screenplay_writer/screenplay_writer.py:106 | `result` | `task0.execute()` | callee neither defined nor imported in this module |
| call_unknown | crewAI-examples/crews/screenplay_writer/screenplay_writer.py:136 | `result` | `crew.kickoff()` | callee neither defined nor imported in this module |

**Where the factories actually terminate.** Following each `factory_call` into its `def` in the same module (max 3 hops) — this is the payoff test for building factory-following at all:

| Terminus | Count | % of factories |
|---|---|---|
| `runtime_external` | 4 | 80.0% |
| `static` | 1 | 20.0% |

| Factory site | Binds | Terminates in |
|---|---|---|
| AITradingCrew/ai_trading_crew/config.py:150 | `DEFAULT_STOCKTWITS_LLM` | `os.getenv(var_name)` |
| AITradingCrew/ai_trading_crew/config.py:151 | `DEFAULT_TI_LLM` | `os.getenv(var_name)` |
| AITradingCrew/ai_trading_crew/config.py:152 | `DEEPSEEK_OPENROUTER_LLM` | `os.getenv(var_name)` |
| AITradingCrew/ai_trading_crew/config.py:174 | `provider_name` | `provider` |
| AITradingCrew/ai_trading_crew/config.py:176 | `PROJECT_LLM` | `os.getenv(var_name)` |

**Latent cross-module chains: 2.** These bindings are named by an `imported` reference at an agent site elsewhere in the corpus — the value a one-module-hop resolver would recover:

| Binding site | Name | call_kind | RHS |
|---|---|---|---|
| AITradingCrew/ai_trading_crew/config.py:152 | `DEEPSEEK_OPENROUTER_LLM` | `factory_call` | `create_default_llm('OPENROUTER_API_KEY', 'OPENROUTER_DEE` |
| AITradingCrew/ai_trading_crew/config.py:176 | `PROJECT_LLM` | `factory_call` | `create_default_llm(f'{provider_name}_API_KEY', DEFAULT_P` |


## 7. `tools_element_types` (summed across agents)

| Element node type | Count |
|---|---|
| Attribute | 19 |
| Call | 16 |
| Name | 5 |

`tools_shape`:

| tools_shape | Count | % of agents |
|---|---|---|
| absent | 27 | 60.0% |
| list | 18 | 40.0% |

Reference scope of the **elements** inside `tools=[...]` (beyond the spec's kwarg-level Pass B, but it is what decides whether a tools list resolves):

| Element ref_scope | Count |
|---|---|
| namespace_attr | 11 |
| self_attr | 8 |
| module | 5 |

Most common tool expressions:

| Element | Count |
|---|---|
| `ScrapeWebsiteTool()` | 4 |
| `self.serper_tool` | 4 |
| `SearchTools.search_internet` | 3 |
| `BrowserTools.scrape_and_summarize_website` | 3 |
| `WebsiteSearchTool()` | 3 |
| `CalculatorTool()` | 3 |
| `SEC10QTool('AMZN')` | 2 |
| `SEC10KTool('AMZN')` | 2 |
| `SECTools.search_10k` | 2 |
| `SECTools.search_10q` | 2 |
| `sentinel_tool` | 2 |
| `self.exctractor_tool` | 2 |
| `CalculatorTools.calculate` | 1 |
| `SEC10QTool()` | 1 |
| `SEC10KTool()` | 1 |
| `matrix_tool` | 1 |
| `analytic_rule_tool` | 1 |
| `git_sentinel_tool` | 1 |
| `self.pdf_search_tool` | 1 |
| `self.caldera_tool` | 1 |

## 8. Construction surface

| Surface | Count | % of agents |
|---|---|---|
| decorated method (@agent) in @CrewBase class | 34 | 75.6% |
| plain method | 6 | 13.3% |
| module-level | 5 | 11.1% |

Cross-tab of the raw signals:

| in class | in func | func decorated | class decorated | in return | in list | Count |
|---|---|---|---|---|---|---|
| True | True | True | True | True | False | 34 |
| True | True | False | False | True | False | 5 |
| False | False | False | False | False | False | 5 |
| True | True | True | False | False | False | 1 |

Decorators observed on the enclosing function / class:

| Decorator | Scope | Count |
|---|---|---|
| `agent` | func | 34 |
| `tool('Scrape website content')` | func | 1 |
| `CrewBase` | class | 34 |

## 9. Import paths observed

| Import path (Agent) | Count |
|---|---|
| `crewai` | 45 |

All kinds:

| Kind | Import path | Count |
|---|---|---|
| task | `crewai` | 59 |
| agent | `crewai` | 45 |
| crew | `crewai` | 11 |
| llm | `crewai` | 2 |

## 10. `identity_fields_present`

| Identity fields | Count | % of agents |
|---|---|---|
| All three (role, goal, backstory) | 4 | 8.9% |
| Some (1-2) | 0 | 0.0% |
| None | 41 | 91.1% |

| Exact combination | Count |
|---|---|
| (none) | 41 |
| role,goal,backstory | 4 |

## 11. Repo dialects

| Repo | py | ipynb | agent sites | agents.yaml | tasks.yaml | crew.json(c) | agents/*.jsonc | manifest crewai | pin | type | extras | crewai import | dialect_only | invisible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| . | 55 | 0 | 6 | Y | Y |  |  | Y | ==1.14.7 | crew | tools | Y |  |  |
| . | 3 | 0 | 2 | Y | Y |  |  | Y | ==0.30.11 |  |  | Y |  |  |
| . | 19 | 0 | 16 | Y | Y |  |  | Y | >=0.100.1 |  | tools | Y |  |  |
| . | 18 | 0 | 8 | Y | Y |  |  | Y | >=0.102.0 |  | tools | Y |  |  |
| crews/screenplay_writer | 1 | 0 | 5 | Y | Y |  |  |  |  |  |  | Y |  |  |
| crews/stock_analysis | 6 | 0 | 4 | Y | Y |  |  | Y | >=0.152.0 |  | tools | Y |  |  |
| crews/trip_planner | 7 | 0 | 4 |  |  |  |  | Y | >=0.152.0 |  |  | Y |  |  |

**dialect_only repos (spec definition — config/manifest signal but zero `Agent(...)` sites): 0 of 7 (0.0%)**

None. All 6 repo(s) carrying `config/agents.yaml` also construct `Agent(...)` in Python — the YAML dialect here is always *paired* with a `config=` call site, never a replacement for one. The flag as specified therefore finds nothing in this corpus.

**Broader flag — repos an AST-only pass sees nothing in, for any reason: 0 of 7 (0.0%)**. This is the population `dialect_only` was meant to catch; here it is empty:


No notebook-only repos (0 `.ipynb` files in the corpus). The `*.py`-glob blind spot does not bite here.

## 12. Unrecognised kwargs on `Agent(...)`

| Kwarg | Count | % of agents | Example value | First seen |
|---|---|---|---|---|
| `inject_date` | 3 | 6.7% | `True` | src/academic_agent/crew.py:78 |

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

7 of 15 anticipated kwargs are unused; 9 distinct kwargs carry the entire corpus.

## Appendix — kwargs on the other kinds

### `Crew(...)` — 11 sites

| Kwarg | Count | % of crews |
|---|---|---|
| agents | 11 | 100.0% |
| tasks | 11 | 100.0% |
| verbose | 10 | 90.9% |
| process | 10 | 90.9% |
| manager_agent | 3 | 27.3% |
| planning | 3 | 27.3% |
| output_log_file | 3 | 27.3% |
| manager_llm | 2 | 18.2% |
| max_rpm | 1 | 9.1% |
| step_callback | 1 | 9.1% |
| task_callback | 1 | 9.1% |

### `Task(...)` — 59 sites

| Kwarg | Count | % of tasks |
|---|---|---|
| config | 46 | 78.0% |
| agent | 43 | 72.9% |
| context | 26 | 44.1% |
| description | 13 | 22.0% |
| expected_output | 12 | 20.3% |
| tools | 12 | 20.3% |
| verbose | 10 | 16.9% |
| output_file | 10 | 16.9% |
| guardrail | 6 | 10.2% |
| guardrail_max_retries | 6 | 10.2% |
| max_retries | 4 | 6.8% |
| async_execution | 3 | 5.1% |
| tool | 3 | 5.1% |
| llm | 3 | 5.1% |
| markdown | 2 | 3.4% |
| output_format | 2 | 3.4% |
| name | 2 | 3.4% |
| input | 1 | 1.7% |

### `LLM(...)` — 2 sites

| Kwarg | Count | % of llms |
|---|---|---|
| api_key | 1 | 50.0% |
| base_url | 1 | 50.0% |
| model | 1 | 50.0% |
| temperature | 1 | 50.0% |

