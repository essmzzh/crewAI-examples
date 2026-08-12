# Survey run 3 — `essmzzh/ai-crewai-multi-agent`

Same `survey.py`, third corpus. Commit `d14aa0c`, shallow clone, read-only.
No corpus code imported or executed.

**1 project, 3 `.py` files, 0 parse failures, 2 Agent sites, 1 Crew, 2 Tasks,
0 `LLM` sites.** The entire crew is one 52-line file.

Small, but it lands squarely between the two previous corpora and settles a
question they disagreed on.

---

## Script bugs this run found

**1. UTF-16 manifests silently read as false.** This repo's `requirements.txt` is
UTF-16 (Windows-authored). Reading it as UTF-8 turns `crewai==0.30.11` into
`c r e w a i = = 0 . 3 0 . 1 1`, so `"crewai" in text.lower()` returned **False**
and Table 11 reported `manifest crewai` blank for a repo that pins CrewAI on its
first line. Pass C's whole job is file-existence and manifest checks, and it was
failing the check on a real repo. Now BOM- and NUL-sniffed before decoding.

This one matters beyond the bug: if a corpus of user repos is scored on
`has_pyproject_crewai`, every Windows-authored `requirements.txt` in it was
scoring zero.

**2. Added `crewai_pin`.** Once the manifest decoded, the extras regex still
missed the version — it only looked for `crewai[...]`. The pins turn out to be
the most interesting cell in Table 11 (below).

**3. My own output directory contaminated corpus 1.** Committing run 2's results
into `survey-results/` inside the crewAI-examples checkout made the survey
discover it as a 32nd repo unit on the next run. Added to `SKIP_DIRS`; corpus 1
is back to 31 units / 71 agent sites.

**4. One more leftover hardcoded phrase** in the repo-unit note (it named
`tests/` and `ui/`, directories from corpus 2 that do not exist here). That is
the second time this class of bug has appeared — generated prose asserting
specifics from a previous corpus.

All three corpora re-run after the fixes. Corpus 1: 31 units, 71 agents.
Corpus 2: 6 agents. Both unchanged except for the newly-correct manifest cells.

---

## Results

The whole crew, verbatim in structure:

```python
@CrewBase
class FinancialAnalystCrew():
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self) -> None:
        self.chatopenai_llm = ChatOpenAI(temperature=0.7, model_name="gpt-4-turbo")

    @agent
    def company_researcher(self) -> Agent:
        return Agent(
            config = self.agents_config['company_researcher'],
            tools = [SECTools.search_10k, SECTools.search_10q],
            llm = self.chatopenai_llm
        )
```

- **3 kwargs total**: `config`, `tools`, `llm` — each on 2 of 2 agents. No
  `verbose`, no `role`/`goal`/`backstory`. 12 of the spec's 15 anticipated
  kwargs unused.
- **`config=self.agents_config[...]` 2/2**, keys extract cleanly. Third corpus
  running, still 100%.
- **`llm=self.chatopenai_llm`, bound in `__init__`** → `ChatOpenAI(temperature=0.7,
  model_name="gpt-4-turbo")`. Pass B resolves both, 100%.
- **`tools=[SECTools.search_10k, SECTools.search_10q]`** — 4 elements, all
  `namespace_attr`, none resolvable without crossing into `tools/sec_tools.py`.
- **100% `@agent` in `@CrewBase`, in `return`.** Third corpus, same surface.
- **Table 12 empty.** No unanticipated kwargs.

**`Crew(verbose = 2)` — an integer, not a bool.** That is the pre-1.0 CrewAI API.
Which brings up the finding this run actually contributes.

---

## The version spread is the real result

`crewai_pin`, now that manifests decode:

| corpus | pin | `verbose` on Crew |
|---|---|---|
| run 1 — crewAI-examples | `>=0.152.0` | `True` |
| run 2 — academic-commercialization-agent | `==1.14.7` | `True` |
| run 3 — ai-crewai-multi-agent | `==0.30.11` | `2` |

**A spread from 0.30 to 1.14 across three repos**, and the oldest one is writing
against an API where `verbose` took an integer. Nothing in the build spec
mentions CrewAI version at all — not as a field, not as a caveat. An adapter
that assumes one kwarg vocabulary is assuming one version. `inject_date` (run 2,
CrewAI 1.14) and `verbose=2` (run 3, CrewAI 0.30) cannot both be current.

**Recommendation: add `crewai_pin` to the anticipated Pass C fields and treat the
kwarg vocabulary as version-dependent.** This is the one structural gap all three
runs point at that the spec has no field for.

---

## Where three runs now agree, and where they don't

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| Agent sites | 71 | 6 | 2 |
| `config=` | 69% | 100% | 100% |
| identity fields (all 3) | 31% | 0% | 0% |
| `tools=` present | 65% | 0% | 100% |
| `llm=` shape | attribute/name | `call` 100% | attribute 100% |
| reference kwargs resolvable | 24/24 | 0 refs | 2/2 |
| `@agent` in `@CrewBase` | 62% | 100% | 100% |
| unanticipated kwargs | 0 | 1 | 0 |
| CrewAI pin | `>=0.152` | `==1.14.7` | `==0.30.11` |

**Settled across all three (79 agent sites):**

1. **`config=` is the single load-bearing kwarg** — 69%, 100%, 100%. Subscript-key
   extraction is now 57/57 across every run. It should be tier one, ahead of the
   identity triple, which is 31%, 0%, 0%.
2. **`@agent` inside `@CrewBase`, returning directly, is the dominant surface** —
   62%, 100%, 100%.
3. **Zero across all three:** `mcps`, `apps`, `max_iter`, `cache`,
   `function_calling_llm`, `**kwargs` unpacking, positional args,
   list/comprehension construction, and any constant `llm=` model string.
   `role`/`goal`/`backstory` are absent from 69%, 100%, 100% of agents.
4. **`callee_form` is `Name` and `import_path` is bare `crewai`, 197/197 sites.**
   The `Attribute` matching path has never fired.

**Still unsettled — and run 3 breaks the tie in run 1's favour:**

Run 2 suggested references were dead (0 refs, everything behind a cross-module
factory) and that `llm=` was unresolvable in principle. Run 3 is back to
`self.<attr>` → `ChatOpenAI(...)` in `__init__`, resolving 2/2. So run 2's
factory-indirection pattern is real but **not** the norm; two of three corpora
resolve `llm=` cleanly through the self-attribute rule.

Revised from run 2's overcorrection: **self-attribute + module-global resolution
is worth building** — it covers 26 of 26 references across runs 1 and 3. What run
2 shows is that it must **fail gracefully**, not that it is not worth having.
`tools=` is the weaker case: element-level references are `namespace_attr` in
runs 1 and 3, needing a cross-module hop the spec declines to make.

`tools=` presence itself is still unpredictable — 65%, 0%, 100% — so nothing
should be inferred from its absence.

---

## Caveat

Three corpora, 79 agent sites, one author. Run 3 is 2 agents in one file. These
are consistent enough on `config=` and the `@CrewBase` surface to act on, and too
thin on everything else to treat as settled. Independently-authored repos would
still be worth more than a fourth from the same source.
