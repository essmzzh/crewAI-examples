# CrewAI corpus survey — aggregates

Corpus root: `/workspace/essmzzh/PurpleCrew`

**Repo-unit note.** The corpus root carries a packaging manifest of its own, so it is **one project, not a corpus of repos**. Splitting it on top-level directories would invent repos out of its source, test and asset folders and then report most of them as having no agents, which is an artefact of the split rather than a fact about the code. Table 11 therefore has a single row. Per-directory detail is recoverable from the `file` field in `agent_sites.jsonl`.

## 1. Totals

| Metric | Count |
|---|---|
| Repo units scanned | 1 |
| Top-level categories | 1 |
| .py files scanned | 19 |
| .ipynb files present (not parsed — see narrative) | 0 |
| Parse failures | 0 |
| Read failures | 0 |
| Files importing crewai symbols | 3 |
| Agent sites | 16 |
| Crew sites | 3 |
| Task sites | 29 |
| LLM sites | 0 |
| Agent sites in test/example paths | 0 |

No parse failures.

## 2. Kwarg frequency on `Agent(...)`

| Kwarg | Count | % of agents | Anticipated by spec |
|---|---|---|---|
| config | 16 | 100.0% | yes |
| allow_delegation | 15 | 93.8% | yes |
| tools | 9 | 56.2% | yes |
| verbose | 6 | 37.5% | yes |

Agents constructed with `**kwargs` unpacking: 0 (0.0%). Agents with positional args: 0 (0.0%).

## 3. `llm_shape` distribution

| llm_shape | Count | % of agents |
|---|---|---|
| absent | 16 | 100.0% |

## 4. `llm_call_callee` distribution

No `llm=` kwarg is a direct call at an Agent site.

Constructors reached **indirectly** (the `llm=`/`function_calling_llm=` reference resolves to a call), from Pass B:

| Resolved callee | Count |
|---|---|
| (none) | 0 |

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
| (none) | 0 |  |

## 6. `ref_scope` distribution

All reference-valued kwargs on `Agent(...)`:

| ref_scope | Count | % of refs |
|---|---|---|
| (none — no kwarg on any Agent is a bare Name or Attribute) | 0 | 0.0% |

`llm=` alone:

| ref_scope | Count | % of llm refs |
|---|---|---|
| (none) | 0 | 0.0% |

`tools=` alone:

| ref_scope | Count |
|---|---|
| (none) | 0 |

Where `self.<attr>` references are actually bound:

| Binding site | Count |
|---|---|
| (none) | 0 |

**Locally resolvable** (local / class_attr / module / self_attr): 0 of 0 (0.0%).

## 7. `tools_element_types` (summed across agents)

| Element node type | Count |
|---|---|
| Attribute | 8 |
| Name | 5 |

`tools_shape`:

| tools_shape | Count | % of agents |
|---|---|---|
| list | 9 | 56.2% |
| absent | 7 | 43.8% |

Reference scope of the **elements** inside `tools=[...]` (beyond the spec's kwarg-level Pass B, but it is what decides whether a tools list resolves):

| Element ref_scope | Count |
|---|---|
| self_attr | 8 |
| module | 5 |

Most common tool expressions:

| Element | Count |
|---|---|
| `self.serper_tool` | 4 |
| `sentinel_tool` | 2 |
| `self.exctractor_tool` | 2 |
| `matrix_tool` | 1 |
| `analytic_rule_tool` | 1 |
| `git_sentinel_tool` | 1 |
| `self.pdf_search_tool` | 1 |
| `self.caldera_tool` | 1 |

## 8. Construction surface

| Surface | Count | % of agents |
|---|---|---|
| decorated method (@agent) in @CrewBase class | 16 | 100.0% |

Cross-tab of the raw signals:

| in class | in func | func decorated | class decorated | in return | in list | Count |
|---|---|---|---|---|---|---|
| True | True | True | True | True | False | 16 |

Decorators observed on the enclosing function / class:

| Decorator | Scope | Count |
|---|---|---|
| `agent` | func | 16 |
| `CrewBase` | class | 16 |

## 9. Import paths observed

| Import path (Agent) | Count |
|---|---|
| `crewai` | 16 |

All kinds:

| Kind | Import path | Count |
|---|---|---|
| task | `crewai` | 29 |
| agent | `crewai` | 16 |
| crew | `crewai` | 3 |

## 10. `identity_fields_present`

| Identity fields | Count | % of agents |
|---|---|---|
| All three (role, goal, backstory) | 0 | 0.0% |
| Some (1-2) | 0 | 0.0% |
| None | 16 | 100.0% |

| Exact combination | Count |
|---|---|
| (none) | 16 |

## 11. Repo dialects

| Repo | py | ipynb | agent sites | agents.yaml | tasks.yaml | crew.json(c) | agents/*.jsonc | manifest crewai | pin | type | extras | crewai import | dialect_only | invisible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| . | 19 | 0 | 16 | Y | Y |  |  | Y | >=0.100.1 |  | tools | Y |  |  |

**dialect_only repos (spec definition — config/manifest signal but zero `Agent(...)` sites): 0 of 1 (0.0%)**

None. All 1 repo(s) carrying `config/agents.yaml` also construct `Agent(...)` in Python — the YAML dialect here is always *paired* with a `config=` call site, never a replacement for one. The flag as specified therefore finds nothing in this corpus.

**Broader flag — repos an AST-only pass sees nothing in, for any reason: 0 of 1 (0.0%)**. This is the population `dialect_only` was meant to catch; here it is empty:


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
| `backstory` | 0 |
| `cache` | 0 |
| `function_calling_llm` | 0 |
| `goal` | 0 |
| `llm` | 0 |
| `max_iter` | 0 |
| `mcps` | 0 |
| `memory` | 0 |
| `role` | 0 |
| `step_callback` | 0 |

11 of 15 anticipated kwargs are unused; 4 distinct kwargs carry the entire corpus.

## Appendix — kwargs on the other kinds

### `Crew(...)` — 3 sites

| Kwarg | Count | % of crews |
|---|---|---|
| agents | 3 | 100.0% |
| manager_agent | 3 | 100.0% |
| planning | 3 | 100.0% |
| process | 3 | 100.0% |
| tasks | 3 | 100.0% |
| manager_llm | 2 | 66.7% |
| verbose | 2 | 66.7% |

### `Task(...)` — 29 sites

| Kwarg | Count | % of tasks |
|---|---|---|
| config | 27 | 93.1% |
| agent | 25 | 86.2% |
| context | 23 | 79.3% |
| tools | 12 | 41.4% |
| max_retries | 4 | 13.8% |
| tool | 3 | 10.3% |
| verbose | 2 | 6.9% |
| output_file | 2 | 6.9% |
| output_format | 2 | 6.9% |
| description | 2 | 6.9% |
| expected_output | 2 | 6.9% |
| name | 2 | 6.9% |
| input | 1 | 3.4% |

### `LLM(...)` — 0 sites

| Kwarg | Count | % of llms |
|---|---|---|
| (none) | 0 | 0.0% |

