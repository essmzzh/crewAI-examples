# crewAI-examples fixture — trimmed corpus, re-measured

This checkout is no longer the full `crewAI-examples` tree. It has been cut down
to three hand-picked sub-projects for use as a validation fixture, and
re-measured so the ground-truth total matches what is on disk.

The pre-trim measurement is preserved verbatim in
`survey-results/crewAI-examples-full/` (aggregates, both JSONL row files, and the
original narrative). Nothing was lost; it is one directory over.

---

## Ground truth after the trim

| Metric | Full tree | **Trimmed** |
|---|---|---|
| Repo units | 31 | **3** |
| `.py` files | 116 | **14** |
| `.ipynb` files | 8 | **0** |
| Parse failures | 0 | **0** |
| **Agent sites** | **71** | **13** |
| Crew sites | 30 | **3** |
| Task sites | 81 | **14** |
| LLM sites | 2 | **0** |
| Units invisible to an AST pass | 7 (22.6%) | **0** |

**13 agent sites** is the number the harness should gate on. It was predicted
from the pre-trim per-project counts (5 + 4 + 4) before the deletion and
confirmed by re-running the survey against the trimmed tree — the two agree
exactly, so the trim removed whole projects cleanly and did not disturb the
three keepers.

| Kept project | `.py` | Agents | Crews | Tasks |
|---|---|---|---|---|
| `crews/screenplay_writer` | 1 | 5 | 1 | 5 |
| `crews/stock_analysis` | 6 | 4 | 1 | 4 |
| `crews/trip_planner` | 7 | 4 | 1 | 5 |

Removed: all other `crews/` sub-projects (and `crews/README.md`, which indexed
projects that no longer exist), plus the whole of `flows/`, `integrations/`, and
`notebooks/`.

A side effect worth recording: the notebook blind spot is gone. The full tree had
6 notebook-only units — 19.4% of it structurally unreachable by a `*.py` scanner.
The trimmed fixture has zero `.ipynb` files and zero units an AST pass cannot
see, so `invisible_to_ast` is now 0 of 3. That was one of the stated reasons for
trimming, and it is achieved.

---

## The three shapes, verified present after the trim

Each was re-checked against the regenerated `agent_sites.jsonl`, not assumed.

**`screenplay_writer` — module-level `yaml.safe_load` config base. Confirmed,
and unique across all four fixtures.** All 5 agents are module-level (no
enclosing class, no enclosing function) and subscript a bare `agents_config[...]`
loaded by the module itself, against 4 sites in `stock_analysis` using the
framework's `self.agents_config[...]`. Both config bases are therefore live in
this one fixture: 5 bare, 4 framework.

**`stock_analysis` — module-global LLM resolution. Confirmed, and unique across
all four fixtures.** All 4 agents carry `llm=` resolving at `module` scope to
`Ollama(model='llama3.1')`. No other fixture resolves an LLM at module scope
(corpus 2 has no references at all, corpus 3 binds in `__init__`, corpus 4 has no
`llm=` on any agent). This is the whole of `ref_scope` in the trimmed corpus:
4 of 4 references, 100% resolvable, all `module`.

**`trip_planner` — namespace-attribute tools and the older plain-class surface.
Confirmed.** Three agents sit in a plain undecorated `TripAgents` class; a fourth
is constructed inside a `@tool`-decorated method on a `BrowserTools` class, which
is a construction site none of the other fixtures contain. Its tool elements are
`BrowserTools.scrape_and_summarize_website`, `SearchTools.search_internet`,
`CalculatorTools.calculate` — 7 `namespace_attr` elements, unresolvable without a
cross-module hop.

### One correction to the selection rationale

The brief justified keeping `stock_analysis` for "namespace-attribute tools
(dotted names like `SECTools.search_10k`)". **It has none.** Every one of its tool
elements is a constructor call — `SEC10KTool('AMZN')`, `SEC10QTool()`,
`ScrapeWebsiteTool()`, `WebsiteSearchTool()`, `CalculatorTool()`. The
namespace-attribute shape lives entirely in `trip_planner` within this fixture.
(`SECTools.search_10k` is real, but it is in `ai-crewai-multi-agent`, a different
fixture.)

The keep decision still stands on its other leg — module-global LLM resolution is
genuinely unique to `stock_analysis` and worth a fixture slot. But the stated aim
that "no shape rests on a single example" is not met for namespace-attribute
tools *within this corpus*: it now rests on `trip_planner` alone. Across the full
four-fixture set it is covered twice (`trip_planner`, `ai-crewai-multi-agent`),
which is probably enough — flagging it so the choice is deliberate rather than
assumed.

---

## Coverage regression the trim introduces

**Kwarg-level `self.<attr>` resolving to a class-body binding is no longer
covered by any fixture.**

The full tree had 15 kwarg-level `self_attr` references: 7 bound in `__init__`,
**8 bound in the class body**. All 8 came from projects this trim removes —
`flows/write_a_book_with_flows` (4), `flows/email_auto_responder_flow` (3),
`flows/meeting_assistant_flow` (1). The trimmed corpus has **zero** `self_attr`
references of any kind.

That shape matters more than its count suggests. It is the `@CrewBase` idiom
where `llm = ChatOpenAI(model="gpt-4o")` sits at class-body level and is read as
`self.llm`, and it is the one that broke the resolver during the original survey
— the first implementation classified all 8 as `unresolved`, understating local
resolvability by 33 points. It is precisely the case a validation gate should
hold onto.

What the other three fixtures still cover:

| Shape | Covered by |
|---|---|
| `self.<attr>` → `__init__`, kwarg level | `ai-crewai-multi-agent` (2), `academic-commercialization-agent` (2) |
| `self.<attr>` → `__init__`, tools element | `PurpleCrew` (6) |
| `self.<attr>` → **class body**, tools element | `PurpleCrew` (9) |
| `self.<attr>` → **class body**, **kwarg level** | **nothing** |

So the binding rule is still exercised — `PurpleCrew` hits the class-body path 9
times — but only through `tools=[...]` elements, never through a kwarg value.
A regression that broke class-body resolution for kwargs while leaving elements
working would pass the gate.

Two ways to close it, if it should be closed:

1. Add one small `@CrewBase` project with a class-body `llm` back to this
   fixture. `flows/email_auto_responder_flow` is the cheapest — 6 `.py` files,
   3 agents, and it carries the shape directly.
2. Accept the gap deliberately and record it, on the grounds that `PurpleCrew`
   exercises the same resolver branch at element level.

I have not done either — the trim is what was asked for and it is complete as
specified. This is flagged for the call to be made explicitly rather than by
omission.

---

## Reproducing

```
python3 survey.py /home/user/crewAI-examples
```

Writes `aggregates.md`, `agent_sites.jsonl`, `repo_dialects.jsonl` to the working
directory. `survey-results/` is excluded from the scan, so re-running in place is
safe and idempotent. No corpus code is imported or executed at any point.
