# Survey run 4 — `essmzzh/PurpleCrew`

Same `survey.py`, fourth corpus. Commit `dc593e8`, shallow clone, read-only.
No corpus code imported or executed.

**1 project, 19 `.py` files, 0 parse failures, 16 Agent sites, 3 Crews,
29 Tasks, 0 `LLM` sites.** Three sibling crews (`redteamcrew`, `blueteamcrew`,
`itopscrew`), each `@CrewBase` with its own `config/agents.yaml` + `tasks.yaml`.

The richest single-application corpus so far, and it breaks three things the
previous three runs had agreed on.

---

## The survey found two probable bugs in the corpus

Not script bugs — defects in the surveyed code, surfaced by the kwarg tables.

**1. `Task(tool=[...])` — singular, 3 occurrences.** CrewAI's `Task` field is
`tools`. Table 12's Task-side equivalent shows `tool` ×3 alongside `tools` ×12
in the same repository, in the same files:

- `blueteamcrew.py:104` — `tool=[matrix_tool]`
- `blueteamcrew.py:113` — `tool=[sentinel_tool]`
- `redteamcrew.py:96` — `tool=[self.pdf_search_tool, self.exctractor_tool]`

Those four tools are almost certainly not reaching their tasks. This is exactly
the kind of thing a kwarg-frequency table is good at: a typo that is invisible in
review becomes obvious when you count `tool` = 3 next to `tools` = 12.

**2. `manager_llm="GPT-4o"` — wrong case, 2 occurrences.** LiteLLM model ids are
lowercase (`gpt-4o`). Capitalised, this is at best relying on a normalisation
that may not exist. Flagged automatically now.

---

## A script gap this run exposed

**Table 5 was looking in the wrong place.** It only inspected `Agent(llm=)` and
`LLM(...)` sites. `manager_llm="GPT-4o"` is a bare constant model string that
never touches an Agent — **the only literal model string in four corpora, and
Table 5 reported "(none)"**.

Fixed to sweep `llm`, `manager_llm`, `function_calling_llm`, `planning_llm`,
`model`, `model_name` across all four kinds, plus model kwargs nested inside
whatever a reference resolves to. The fix improved corpus 1 retroactively:
where run 1 reported two model strings, it now reports the models hiding one
indirection deep —

| corpus 1, after the fix | count |
|---|---|
| `gpt-4o` | 9 |
| `llama3.1` | 4 |
| `nvidia_nim/` | 4 — flagged **partial, concatenated at runtime** |
| `gpt-3.5-turbo` | 2 |
| `gpt-4` | 1 |

Run 1's claim that "zero agents pass a model string" was accurate about `llm=`
and misleading about the corpus. Corrected.

All four corpora re-run. Corpus 1: 31 units / 71 agents. Corpus 2: 6. Corpus 3: 2.

---

## What this corpus breaks

**1. `llm=` is absent from 100% of agents — and the LLM moved to `Crew`.**
Sixteen agents, not one `llm=`. Instead: `manager_llm` on 2 of 3 crews,
alongside `manager_agent` on 3 of 3 and `planning=True` on 3 of 3. Model
selection has left the Agent entirely and become a crew-level concern.

Four corpora, four different answers for where the model lives:

| corpus | where `llm` is |
|---|---|
| crewAI-examples | `self.<attr>` / module global → LangChain ctor |
| academic-commercialization | cross-module factory call |
| ai-crewai-multi-agent | `self.<attr>` in `__init__` → `ChatOpenAI(...)` |
| **PurpleCrew** | **not on the Agent at all — `Crew(manager_llm=...)`** |

An adapter that reads `Agent(llm=)` extracts nothing from 16 of 16 agents here.

**2. `Crew(...)` carries orchestration the spec has no view of.** `manager_agent`
3/3, `planning` 3/3, `manager_llm` 2/3. The spec's anticipated set is entirely
Agent-shaped. Across runs 2 and 4, Crew now carries `manager_agent`,
`manager_llm`, `planning`, `max_rpm`, `task_callback`, `step_callback` — six
kwargs, none anticipated, one of which (`step_callback`) the spec has filed
under Agent.

**3. Element-level tool references resolve here — 13 of 13.** 8 `self_attr`,
5 `module`. Every previous corpus with tools had them as `namespace_attr`
(`SECTools.search_10k`), needing a cross-module hop. This one instantiates tools
as module globals (`sentinel_tool = SentinelTool()`) and class attributes
(`self.serper_tool`), both of which Pass B resolves.

This vindicates the `_element_refs` addition I made beyond spec in run 1: it was
dead on three corpora and is the whole tools story on the fourth.

It also produces the run's one genuinely interesting resolution case —
`self.pdf_search_tool` is assigned **twice**, once in the class body
(`PDFSearchTool()`) and once in a method (`PDFSearchTool(pdf_path=file_path,
n_results=3)`). The resolver prefers the method binding, which is the right call,
but it is a real instance of the ambiguity the spec waves off as "branch
flattening is fine".

**4. Task kwarg surface is wide.** 13 distinct kwargs across 29 tasks: `config`
93%, `agent` 86%, `context` 79%, `tools` 41%, then `max_retries`, `tool`,
`verbose`, `output_file`, `output_format`, `description`, `expected_output`,
`name`, `input`. `context` at 79% is notable — explicit task-graph wiring, and
nothing in the spec addresses it.

---

## Where four runs now stand

| | run 1 | run 2 | run 3 | run 4 |
|---|---|---|---|---|
| Agent sites | 71 | 6 | 2 | 16 |
| `config=` | 69% | 100% | 100% | **100%** |
| identity fields (all 3) | 31% | 0% | 0% | **0%** |
| `tools=` present | 65% | 0% | 100% | 56% |
| `llm=` present | 35% | 100% | 100% | **0%** |
| refs resolvable | 24/24 | 0 refs | 2/2 | 0 refs |
| tool elements resolvable | 12/48 | — | 0/4 | **13/13** |
| `@agent` in `@CrewBase` | 62% | 100% | 100% | 100% |
| unanticipated Agent kwargs | 0 | 1 | 0 | 0 |
| CrewAI pin | `>=0.152` | `==1.14.7` | `==0.30.11` | `>=0.100.1` |

**Settled across all four (95 agent sites):**

1. **`config=` is the only universal kwarg** — 69/100/100/100%. Subscript-key
   extraction is **73/73**. Nothing else comes close. It should be tier one.
2. **`@agent` in `@CrewBase`, returning directly** — 62/100/100/100%.
3. **Identity fields are absent from 69/100/100/100% of agents.** The spec treats
   `role`/`goal`/`backstory` as the primary path. On three of four corpora they
   appear zero times.
4. **Zero across all four:** `mcps`, `apps`, `max_iter`, `cache`,
   `function_calling_llm`, `**kwargs` unpacking, positional args, comprehension
   construction. `callee_form` is `Name` and `import_path` bare `crewai` at
   **213/213** sites.

**Now unsettled — this run flips it:**

`llm=` presence across the four runs is 35%, 100%, 100%, **0%**. There is no
stable answer. Combined with four different resolution shapes, the conclusion is
firmer than run 3's: **`Agent(llm=)` cannot be the extraction point.** Any
model-identification pass has to look at Crew-level kwargs too, and be prepared
to find nothing.

**Version spread widens: 0.30.11, >=0.100.1, >=0.152.0, ==1.14.7.** Four repos,
four eras of the API. `crewai_pin` (added in run 3) is earning its place.

---

## Recommended spec changes, consolidated across four runs

1. **`config=` to tier one**, ahead of the identity triple. Subscript-key
   extraction works 73/73 and handles three base forms (`self.agents_config`,
   module-level dicts, class-attribute paths).
2. **Add a Crew-level kwarg pass.** `manager_agent`, `manager_llm`, `planning`,
   `max_rpm`, `task_callback`, `step_callback` are all real and all unanticipated.
   Move `step_callback` off the Agent list.
3. **Add a Task-level pass** — `context` (79% here), `guardrail`,
   `guardrail_max_retries`, `output_file`, `max_retries`.
4. **Treat model identification as best-effort across Agent and Crew**, not as an
   `Agent(llm=)` read.
5. **Keep `crewai_pin`** and treat the kwarg vocabulary as version-dependent.
6. **Keep element-level reference resolution for `tools=`** — dead on three
   corpora, 13/13 on this one.
7. **Drop:** `mcps`, `apps`, `max_iter`, `cache`, `function_calling_llm`,
   `**kwargs` handling, positional args, `in_list`/comprehension handling, and
   the `Attribute` callee-matching path. Zero occurrences in 213 sites.

---

## Caveat

Four corpora, 95 agent sites, one author. The `config=` and `@CrewBase` results
are consistent enough across very different code to act on. Everything about
`llm=` has now flipped twice in four runs, which is itself the finding —
but it is four data points, and independently-authored repos would still tell us
more than a fifth from the same source.
