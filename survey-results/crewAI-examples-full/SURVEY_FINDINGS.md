# CrewAI corpus survey — findings

Companion narrative to `aggregates.md`. Numbers below all come from
`agent_sites.jsonl` / `repo_dialects.jsonl`, produced by `survey.py`.

Corpus: `crewAI-examples` @ `claude/crewai-corpus-survey-ln0o1w`.
31 repo units, 116 `.py` files, **0 parse failures**, 71 Agent sites, 30 Crew
sites, 81 Task sites, 2 `LLM` sites.

---

## Two deviations from the spec, and why

**1. `repo` is the project unit, not the first path component.** The spec assumes a
corpus of repos cloned flat under the root. This corpus is one repo whose first
level is category folders (`crews/`, `flows/`, `integrations/`, `notebooks/`).
The literal reading gives four rows and a dialect table with no information in
it. `repo` is therefore the nearest directory holding a manifest or code, capped
at depth 3 (31 units); `repo_top` on every row preserves the literal reading, so
nothing is lost.

**2. `ref_scope` gained one value and `self_attr` gained a sub-field.** Two cases
the spec's enum would have mislabelled:

- **`param`** — a kwarg referencing a function parameter. Calling that
  "unresolved" is a measurement error: the value is injected by the caller and
  the reference is perfectly well understood. (0 occurrences here, but the
  classification would have been wrong if there had been any.)
- **`self.x` bound in the class body**, not in a method. Spec logic checks
  `self.<attr> = ...` inside methods and otherwise falls through to
  "unresolved". That mislabelled **8 of 24 references (33%)** — the entire
  `@CrewBase` idiom, where `llm = ChatOpenAI(model="gpt-4o")` sits at class-body
  level and is read as `self.llm`. Fixed, with `ref_binding_site` ∈
  `{__init__, method, class_body}` recording the distinction. This single fix
  moved local resolvability from 67% to 100%.

Two additions beyond spec, both cheap and both decision-relevant: a `source`
field per kwarg holding the exact `ast.get_source_segment` text (the spec asks
for exact source with no normalisation *and* for `ast.unparse`, which normalises
multi-line strings onto one line — both are now recorded), and `_element_refs`
classifying the elements *inside* `tools=[...]`.

---

## What surprised me

**1. Reference resolution is a solved problem in this corpus — 100%, and the
scope walker is not what solves it.** All 24 reference-valued kwargs resolve:
15 `self_attr`, 9 `module`. **`local` is zero. `class_attr` is zero.
`imported` is zero. `unresolved` is zero.** §5's function-body scope walker —
descending through `If`/`For`/`While`/`With`/`Try`, stopping at nested scopes,
flattening branches — finds nothing at any Agent site, because nothing is ever
assigned to a local and then passed as an Agent kwarg. Every `llm=` is either
`self.<attr>` (62.5%) or a module global (37.5%).

The walker is not worthless, but it is aimed at the wrong target. Element-level
references inside `tools=[...]` do use locals (3 `local`, 8 `module`, 1
`imported`, 27 `namespace_attr`) — so the machinery pays off one level deeper
than the spec points it.

**2. Table 12 is empty, and the inverse table is the real result.** Not one
unanticipated kwarg in 71 Agent sites. The spec anticipates 15 kwargs; the
corpus uses **9**, and 6 anticipated ones — `mcps`, `apps`,
`function_calling_llm`, `max_iter`, `cache`, `step_callback` — appear **zero**
times. `mcps` and `apps` in particular are being designed for against no
observed evidence in this corpus.

**3. Identity fields are absent from 69% of agents, and it is bimodal.** 22
agents carry all three of `role`/`goal`/`backstory`; 49 carry none. **Zero carry
one or two.** Agents are either fully inline or fully config-driven — there is
no partial case to design for. The 49 without identity fields all pass
`config=`, which is the second-most-common kwarg overall (69%), ahead of
`tools`, ahead of `llm`, ahead of `role`.

**4. `config=` has three dialects, not one — and one of them isn't `self.`**
All 49 Agent `config=` values are `Subscript` with a string-literal key, so
`config_subscript_key` extracts cleanly at 49/49. But the base splits:
44 `self.agents_config[...]` (the `@CrewBase` path-string form) and 5 bare
`agents_config[...]` in `crews/screenplay_writer`, where the module does its own
`yaml.safe_load` at import time and subscripts the resulting dict. Same shape,
completely different resolution story — one is a framework contract, the other is
an arbitrary runtime dict that happens to be subscripted with a literal.

**5. `llm=` almost never holds an LLM.** `llm_shape` is `absent` 64.8%,
`attribute` 21.1%, `name` 12.7%, and **`call` exactly once**. `llm_constant` is
**empty — zero agents pass a model string directly**. The "provider/model-id"
placeholder the spec asks to flag does not occur, and neither does any other bare
string. Every real constructor is reached indirectly, through Pass B: `Ollama`
×9, `ChatOpenAI` ×6, `LLM` ×4, `nvllm` ×4, `AzureChatOpenAI` ×1. **LangChain
constructors outnumber CrewAI's own `LLM` 16 to 4.** Anything reading `llm=` at
the call site sees a name, not a model.

**6. The invisible corpus is notebooks, not config dialects — and
`dialect_only` as specified finds none of it.** `dialect_only` scores **0 of
31**. Every repo carrying `config/agents.yaml` *also* constructs `Agent(...)` in
Python: the YAML dialect here is always paired with a `config=` call site, never
a substitute for one. The premise behind the flag doesn't hold in this corpus.

What *is* invisible is 7 of 31 repo units (22.6%) with zero Agent sites, of which
**6 are notebook-only** and contain crewai code inside `.ipynb`:
`crews/industry-agents`, `notebooks/Coding Assistant`, `notebooks/Flows_101`,
`notebooks/Landing Page Flow`, `notebooks/QA Agent`,
`notebooks/Simple QA Crew + Flow`. The seventh, `flows/content_creator_flow`, is
an uninitialised git submodule (gitlink `160000`) — no content on disk at all.
The `*.py` glob the spec defines makes 19.4% of this corpus structurally
unreachable, and no config-file check will surface it.

**7. Construction surface is nearly monoculture.** 62% of agents are a decorated
method (`@agent`) inside a `@CrewBase` class, returning directly
(`in_return: true`). 28% are plain methods on an undecorated factory class. 10%
are module-level. **Zero agents in comprehensions or lists. Zero `**kwargs`
unpacking. Zero positional args. Zero duplicate kwargs.** The parent-map
machinery for `in_list` earns nothing here. Only three decorator spellings appear
at all: `agent`, `CrewBase`, `tool(...)`.

**8. `tools=` is 8.5% unrecoverable by construction.** 56% are `List`, 35%
absent, and 6 agents pass something with no extractable element list: 4
`ExaSearchTool.tools()` (a `Call`) and 2 list concatenations (`BinOp`,
`[...] + [...]`). No amount of static walking recovers elements from those
without evaluating them.

**9. Import surface is trivial.** Every one of the 184 construction sites imports
from the bare `crewai` module. No `crewai.agent`, no `import crewai as ca`, no
`Attribute` callee form anywhere — `callee_form` is `Name` 184/184. The
`Attribute` matching path, the module-alias map, and the "record the observed
path rather than filtering" hedge all cost code and returned one distinct value.
Worth noting `crewai_tools` is a *different distribution* that string-prefix
matching on `"crewai"` would wrongly capture; the script matches `crewai` and
`crewai.*` only and reports lookalikes separately.

---

## What the build spec did not anticipate

- **Notebooks.** The largest single blind spot, and it is not in the spec at all.
  6 repo units, ~19% of the corpus.
- **Class-body binding read through `self`.** The `@CrewBase` idiom's dominant
  llm pattern; the spec's `self_attr` rule as written misses it entirely.
- **Module-global LLM singletons.** 37.5% of references. `module` scope isn't
  wrong in the spec, but it's listed third of five, after `local` and
  `class_attr`, both of which are dead.
- **LangChain constructors in `llm=`.** 16 of 24 resolved constructors are not
  CrewAI's `LLM`. `Ollama`, `ChatOpenAI`, `AzureChatOpenAI`, and a locally
  defined `nvllm` wrapper. Any model-string extraction has to handle
  `model=`, `model_name=`, and `model_str=` with a string-concat argument
  (`nvllm(model_str='nvidia_nim/' + model, ...)`).
- **YAML loaded by the module itself**, subscripted like the framework's own
  config dict.
- **`Task(...)` asymmetry.** 28 tasks pass `description`, only 16 pass
  `expected_output` — 12 tasks carry a description with no expected output. If
  Task gets the same identity-completeness treatment as Agent, it will not be
  bimodal the way Agent is.

---

## Which spec sections the numbers argue should be reordered

1. **Demote §5's function-scope walker.** Zero hits at kwarg level across the
   whole corpus. Retarget it at `tools=[...]` elements, where locals actually
   appear, or defer it entirely.
2. **Promote `self`-attribute resolution to first position** — including
   class-body binding, which is the majority sub-case (8 of 15). Then module
   globals. Those two rules cover 100% of observed references between them.
3. **Promote `config=` to the same tier as `role`/`goal`/`backstory`.** It is on
   69% of agents versus 31% for the identity triple, and 69% of agents have *no*
   identity fields at all. An adapter that treats `config=` as a fallback path
   handles a minority of this corpus. It needs three bases, not one:
   `self.agents_config`, module-level dicts, and a `Subscript` key extractor
   (which works 49/49).
4. **Add a notebook pass, or state the exclusion explicitly.** 19.4% of repo
   units are otherwise unscoreable, and `dialect_only` — the flag written to
   catch exactly this population — reports 0.
5. **Demote `llm=` model-string extraction.** Zero constant `llm=` values.
   Everything worth reading sits one indirection away inside a constructor call
   the reference resolves to, so this work depends on Pass-B-equivalent
   resolution landing first.
6. **Demote `mcps` and `apps`.** Zero occurrences; they are speculative against
   this corpus.
7. **Drop or defer the `in_list` / comprehension handling and `**kwargs`
   unpacking.** Zero occurrences of each.

---

## Files

| File | Contents |
|---|---|
| `survey.py` | The throwaway script. Standalone, stdlib only, `ast.parse` only. |
| `agent_sites.jsonl` | 184 rows — Pass A + Pass B, all four kinds. |
| `repo_dialects.jsonl` | 31 rows — Pass C. |
| `aggregates.md` | All twelve tables plus an appendix. |

Reproduce with `python3 survey.py /path/to/crewAI-examples`. Delete all four when
the survey is done.

### Verification

Agent-site count was reconciled against an independent regex sweep: 76 raw
`\bAgent\s*\(` matches across `*.py`, of which exactly 5 are string literals
inside `survey.py` itself (now excluded from its own scan), leaving 71 — an exact
match with the AST pass. No corpus code was imported or executed at any point.
