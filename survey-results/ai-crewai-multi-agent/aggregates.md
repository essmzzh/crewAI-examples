# CrewAI corpus survey — aggregates

Corpus root: `/workspace/essmzzh/ai-crewai-multi-agent`

**Repo-unit note.** The corpus root carries a packaging manifest of its own, so it is **one project, not a corpus of repos**. Splitting it on top-level directories would invent repos out of its source, test and asset folders and then report most of them as having no agents, which is an artefact of the split rather than a fact about the code. Table 11 therefore has a single row. Per-directory detail is recoverable from the `file` field in `agent_sites.jsonl`.

## 1. Totals

| Metric | Count |
|---|---|
| Repo units scanned | 1 |
| Top-level categories | 1 |
| .py files scanned | 3 |
| .ipynb files present (not parsed — see narrative) | 0 |
| Parse failures | 0 |
| Read failures | 0 |
| Files importing crewai symbols | 1 |
| Agent sites | 2 |
| Crew sites | 1 |
| Task sites | 2 |
| LLM sites | 0 |
| Agent sites in test/example paths | 0 |

No parse failures.

## 2. Kwarg frequency on `Agent(...)`

| Kwarg | Count | % of agents | Anticipated by spec |
|---|---|---|---|
| config | 2 | 100.0% | yes |
| llm | 2 | 100.0% | yes |
| tools | 2 | 100.0% | yes |

Agents constructed with `**kwargs` unpacking: 0 (0.0%). Agents with positional args: 0 (0.0%).

## 3. `llm_shape` distribution

| llm_shape | Count | % of agents |
|---|---|---|
| attribute | 2 | 100.0% |

## 4. `llm_call_callee` distribution

No `llm=` kwarg is a direct call at an Agent site.

Constructors reached **indirectly** (the `llm=`/`function_calling_llm=` reference resolves to a call), from Pass B:

| Resolved callee | Count |
|---|---|
| ChatOpenAI | 2 |

## 5. `llm_constant` values

| Model string | Count | Flags |
|---|---|---|
| (none) | 0 |  |

Model strings found on `LLM(...)`/`llm=Call(...)` sites (not `llm=` constants):

| Model string | Count | Flags |
|---|---|---|
| (none) | 0 |  |

## 6. `ref_scope` distribution

All reference-valued kwargs on `Agent(...)`:

| ref_scope | Count | % of refs |
|---|---|---|
| self_attr | 2 | 100.0% |

`llm=` alone:

| ref_scope | Count | % of llm refs |
|---|---|---|
| self_attr | 2 | 100.0% |

`tools=` alone:

| ref_scope | Count |
|---|---|
| (none) | 0 |

Where `self.<attr>` references are actually bound:

| Binding site | Count |
|---|---|
| __init__ | 2 |

**Locally resolvable** (local / class_attr / module / self_attr): 2 of 2 (100.0%).

## 7. `tools_element_types` (summed across agents)

| Element node type | Count |
|---|---|
| Attribute | 4 |

`tools_shape`:

| tools_shape | Count | % of agents |
|---|---|---|
| list | 2 | 100.0% |

Reference scope of the **elements** inside `tools=[...]` (beyond the spec's kwarg-level Pass B, but it is what decides whether a tools list resolves):

| Element ref_scope | Count |
|---|---|
| namespace_attr | 4 |

Most common tool expressions:

| Element | Count |
|---|---|
| `SECTools.search_10k` | 2 |
| `SECTools.search_10q` | 2 |

## 8. Construction surface

| Surface | Count | % of agents |
|---|---|---|
| decorated method (@agent) in @CrewBase class | 2 | 100.0% |

Cross-tab of the raw signals:

| in class | in func | func decorated | class decorated | in return | in list | Count |
|---|---|---|---|---|---|---|
| True | True | True | True | True | False | 2 |

Decorators observed on the enclosing function / class:

| Decorator | Scope | Count |
|---|---|---|
| `agent` | func | 2 |
| `CrewBase` | class | 2 |

## 9. Import paths observed

| Import path (Agent) | Count |
|---|---|
| `crewai` | 2 |

All kinds:

| Kind | Import path | Count |
|---|---|---|
| agent | `crewai` | 2 |
| task | `crewai` | 2 |
| crew | `crewai` | 1 |

## 10. `identity_fields_present`

| Identity fields | Count | % of agents |
|---|---|---|
| All three (role, goal, backstory) | 0 | 0.0% |
| Some (1-2) | 0 | 0.0% |
| None | 2 | 100.0% |

| Exact combination | Count |
|---|---|
| (none) | 2 |

## 11. Repo dialects

| Repo | py | ipynb | agent sites | agents.yaml | tasks.yaml | crew.json(c) | agents/*.jsonc | manifest crewai | pin | type | extras | crewai import | dialect_only | invisible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| . | 3 | 0 | 2 | Y | Y |  |  | Y | ==0.30.11 |  |  | Y |  |  |

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
| `allow_delegation` | 0 |
| `apps` | 0 |
| `backstory` | 0 |
| `cache` | 0 |
| `function_calling_llm` | 0 |
| `goal` | 0 |
| `max_iter` | 0 |
| `mcps` | 0 |
| `memory` | 0 |
| `role` | 0 |
| `step_callback` | 0 |
| `verbose` | 0 |

12 of 15 anticipated kwargs are unused; 3 distinct kwargs carry the entire corpus.

## Appendix — kwargs on the other kinds

### `Crew(...)` — 1 sites

| Kwarg | Count | % of crews |
|---|---|---|
| agents | 1 | 100.0% |
| process | 1 | 100.0% |
| tasks | 1 | 100.0% |
| verbose | 1 | 100.0% |

### `Task(...)` — 2 sites

| Kwarg | Count | % of tasks |
|---|---|---|
| agent | 2 | 100.0% |
| config | 2 | 100.0% |

### `LLM(...)` — 0 sites

| Kwarg | Count | % of llms |
|---|---|---|
| (none) | 0 | 0.0% |

