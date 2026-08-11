# Survey run 2 — `essmzzh/academic-commercialization-agent`

Same `survey.py`, second corpus. Commit `893d270`, shallow clone, read-only.
No corpus code imported or executed.

**1 project, 55 `.py` files, 0 parse failures, 6 Agent sites, 1 Crew, 6 Tasks,
1 `LLM` site.** Only 2 of 55 files touch crewai symbols.

This is a real application, not an examples gallery, and it inverts almost every
result from run 1. It is the more useful of the two runs.

---

## Script changes this run forced

Running on a differently-shaped corpus exposed four defects, all now fixed:

1. **Single-project roots were being shredded into fake repos.** The unit
   heuristic split this repo on its top-level directories and produced 10
   "repos", 9 of them flagged invisible — reporting `tests/`, `ui/`, `api/` and
   `assets/` as CrewAI repos with no agents. That 90% figure was an artefact of
   the split, not a fact about the code. A root carrying its own packaging
   manifest is now one unit; Table 11 has a single row.
2. **Three passages of prose were hardcoded to run 1's corpus** — the repo-unit
   note named `crews/`/`flows/`/`integrations/`/`notebooks/` verbatim, the
   `dialect_only` explanation asserted a fact about `config/agents.yaml`
   pairing, and the invisibility section asserted "the cause is notebooks".
   On this corpus all three printed confident statements that were false. Now
   derived from the data.
3. **Table 6 emitted a table with no body row** when nothing resolves.

Re-ran run 1 afterwards: 31 units, 71 agent sites, 0 parse failures — unchanged.
Only prose differs.

---

## What this corpus shows that run 1 did not

**1. Pass B has nothing to do here, and the reason matters.** Zero
reference-valued kwargs. Not one kwarg on any Agent is a bare `Name` or
`Attribute` — every value is a `Call`, a `Subscript`, or a `Constant`. In run 1
Pass B carried the whole result (24 references, 100% resolvable) and the §5
scope walker was dead. Here **Pass B itself is dead** and the value has moved
into a call.

Between the two corpora, all three of the spec's resolution mechanisms have now
been observed contributing nothing on at least one corpus. What survives is
whatever can read a `Call`.

**2. `llm=` is a cross-module factory, 6 of 6.** Every agent gets
`llm=create_llm(...)` — `create_llm(json_mode=True, temperature=0.0)` ×4 and
`create_llm()` ×2. `create_llm` is imported from `academic_agent.llm_config`,
so the model is one module boundary away, which the spec explicitly declines to
cross.

Following that import would not help. The factory ends in:

```python
return _wrap_with_retry(LLM(**kwargs))
```

**`LLM(**kwargs)` — double-star, zero readable keywords.** The one `LLM` site in
the repo has `has_double_star: true` and an empty `kwargs` object. The model
string is not statically reachable at any depth. Run 1 said "demote `llm=` model
extraction because everything is one indirection away"; this corpus says the
indirection can be unbounded, and the terminal call can be opaque even when you
reach it.

Worth noting the file's own comment on why: `LLM(...)` returns a provider class
such as `OpenAICompatibleCompletion`, so `isinstance(LLM(...), LLM)` is **False**.
Any adapter that type-checks the result of a CrewAI `LLM` call against `LLM`
will be wrong.

**3. First genuine Table 12 hit: `inject_date`.** 3 of 6 agents pass
`inject_date=True`. Across both corpora — 77 Agent sites — this is the only
kwarg the build spec does not anticipate.

**4. Identity fields: 0%. Tools: 0%.** Not one `role`, `goal`, or `backstory`,
and **`tools=` does not appear anywhere in the repository** (`grep` confirms, not
just the AST pass). All six agents are `config=` + `llm=` + `verbose=`
(+ `inject_date`) and nothing else. Four kwargs carry the entire corpus; 12 of
the 15 the spec anticipates are unused.

Run 1's identity split was bimodal (22 fully inline / 49 fully config-driven).
This corpus is entirely at the config-driven pole, and it is the pole the spec
treats as the fallback path.

**5. `config=self.agents_config[...]` 6 of 6, keys extract cleanly** — including
one split across three source lines by the formatter, which the AST reads
without trouble. `pyproject.toml` declares `type = "crew"` and the `tools` extra.

**6. New surface on Task and Crew that the spec has no view of.** `Task(...)`
carries `guardrail` (6/6), `guardrail_max_retries` (6/6), `markdown`, `context`,
`async_execution`. `Crew(...)` carries `task_callback`, `step_callback`,
`max_rpm`. Note `step_callback` is on the spec's anticipated **Agent** list but
appears here on **Crew** — the spec has it at the wrong level.

**7. New import paths.** `from crewai.agents.agent_builder.base_agent import
BaseAgent`, `from crewai import TaskOutput`, `from crewai.events.event_bus import
crewai_event_bus`, and a function-local `from crewai.events.types.tool_usage_events
import ...`. The construction sites themselves are all bare `crewai`, so Table 9
still reads `crewai` 13/13 — but the surrounding surface is wider than the four
construction symbols, and one of those imports is inside a function body. The
script scans all import nodes rather than top-level only, so it catches that;
a top-level-only scan as the spec describes would have missed it.

---

## What the two runs together argue

| | run 1 — crewAI-examples | run 2 — academic-commercialization-agent |
|---|---|---|
| Agent sites | 71 | 6 |
| `config=` | 69% | 100% |
| identity fields | 31% all three | 0% |
| `tools=` present | 65% | 0% |
| `llm=` shape | `attribute` 21%, `name` 13%, `call` 1% | `call` 100% |
| reference kwargs | 24, all resolvable | 0 |
| unanticipated kwargs | 0 | 1 (`inject_date`) |
| model string reachable | via 1 indirection | not at any depth |

Run 1's headline — 100% of references locally resolvable — was a property of
curated example code, and I flagged that caveat. Run 2 confirms it: real
application code does not put values in variables for an adapter to find, it puts
them behind factory functions.

**Revised ordering.** Run 1 argued for promoting self-attribute and module-global
resolution to first position. Run 2 argues those two rules cover 100% of one
corpus and 0% of the other. The stable conclusion across both is narrower:

1. **`config=` handling is the only thing that is load-bearing on both corpora**
   (69% and 100%). Subscript-key extraction works 55/55 across both runs. This
   should be tier one, ahead of the identity triple, which covers 31% and 0%.
2. **Treat `llm=` as unresolvable by default and design for that**, rather than
   ranking extraction strategies. Zero constant `llm=` values across 77 agent
   sites. A `Call` you cannot follow is the common case, not the edge case.
3. **`step_callback` belongs on Crew, not Agent** in the anticipated set, and
   `guardrail` / `guardrail_max_retries` belong on Task.
4. **Keep the all-imports scan**; the top-level-only rule the spec describes
   would miss function-local crewai imports, which occur here.
5. Run 1's demotions still hold and are now better supported: `mcps`, `apps`,
   `max_iter`, `cache`, `function_calling_llm` are at **zero across both
   corpora**, as are `**kwargs` unpacking, positional args, and
   list/comprehension construction.

One caveat, stated plainly: this is 6 agent sites in one application. It is
enough to falsify run 1's generalisations, not enough to replace them. A third
corpus of independently-authored application code would be worth more than
either run so far.
