# Survey v2 — all five corpora in one run

`survey_v2.py`, one run, five corpora, v2 categories throughout. Four `original`
(already surveyed under v1) and one `new`: `essmzzh/AITradingCrew` @ `2f974ca`.

**110 `.py` files, 0 parse failures, 45 agent sites** — 37 original (unchanged
from v1, so the v2 recategorisation did not disturb discovery) + 8 new.

| Cohort | Corpus | Units | Agents | Crews | Tasks |
|---|---|---|---|---|---|
| original | crewAI-examples (trimmed) | 3 | 13 | 3 | 14 |
| original | academic-commercialization-agent | 1 | 6 | 1 | 6 |
| original | ai-crewai-multi-agent | 1 | 2 | 1 | 2 |
| original | PurpleCrew | 1 | 16 | 3 | 29 |
| **new** | **AITradingCrew** | 1 | **8** | 3 | 8 |

---

## The headline: reachability by cohort

| Reachability | new (n=8) | original (n=6) | Total |
|---|---|---|---|
| `terminal_constructor` | 0 (0%) | **6 (100%)** | 6 |
| `imported` | **6 (75%)** | 0 (0%) | 6 |
| `unresolved_local` | 2 (25%) | 0 (0%) | 2 |
| `local` | 0 | 0 | 0 |
| `argument_passed` | 0 | 0 | 0 |
| `factory_call` (at agent sites) | 0 | 0 | 0 |
| `runtime_external` (at agent sites) | 0 | 0 | 0 |

**The two cohorts do not overlap on a single category.** Every original-cohort
reference resolves to a constructor in the same module. Every new-cohort
reference leaves the module — 6 through an import, 2 through class inheritance.
That divergence is the finding, and it is total: 6/6 vs 0/8.

Under v1 this would have read as `module`/`self_attr` ×6 versus `imported` ×6 and
`unresolved` ×2 — the same numbers, but with no way to see that the originals
are *done* resolving and the new corpus has *not started*.

---

## Change 1 — the Call split, and why the agent-site view is a trap

At agent sites, `ref_call_kind` is 100% `terminal_constructor` (6/6, all
original). `factory_call` is **zero**.

That is misleading, and v2 needed one addition beyond the spec to show why: a
**binding census** over every module-level and class-body binding whose RHS is a
call — the population a reference could resolve *to*, rather than the ones it
happens to reach inside one module.

| call_kind | new (n=18) | original (n=29) | Total |
|---|---|---|---|
| `terminal_constructor` | 8 (44%) | 24 (83%) | 32 |
| `call_unknown` | 5 (28%) | 5 (17%) | 10 |
| **`factory_call`** | **5 (28%)** | **0 (0%)** | 5 |

Every factory in the corpus is in the new repo, and all five are invisible from
the agent sites because they sit one import away.

Spot-checks, per the done-when (`file:line`, one per bucket):

| Bucket | Site | Binds | RHS | Basis |
|---|---|---|---|---|
| `factory_call` | `AITradingCrew/ai_trading_crew/config.py:150` | `DEFAULT_STOCKTWITS_LLM` | `create_default_llm('OPENROUTER_API_KEY', …)` | matches a `def` in this module |
| `terminal_constructor` | `crewAI-examples/crews/stock_analysis/src/stock_analysis/crew.py:23` | `llm` (kwarg) | `Ollama(model='llama3.1')` | imported from `langchain.llms`, class by PEP 8 naming |
| `call_unknown` | `crewAI-examples/crews/screenplay_writer/screenplay_writer.py:10` | `current_dir` | `Path.cwd()` | callee neither defined nor imported in this module |

Two classification rules worth stating, both chosen to avoid inflating
`factory_call`:

- `factory_call` is reserved for the spec's definition — a callee matching a
  `def` in *this* module. An imported function-shaped callee is `call_unknown`
  with the evidence recorded ("latent factory"), never a factory.
- An imported **CamelCase** callee is `terminal_constructor` on PEP 8 convention
  *plus* observed import provenance. `Ollama` from `langchain.llms` is evidence,
  not a guess — the import statement names the origin. My first pass called these
  `call_unknown`, which made the original cohort look unreachable when it is in
  fact the best case in the corpus.

---

## Where the factories terminate — the prioritisation answer

Following each `factory_call` into its `def` in the same module, up to 3 hops:

| Terminus | Count | % of factories |
|---|---|---|
| **`runtime_external`** | **4** | **80%** |
| `static` | 1 | 20% |

The chain in full, and it is worth reading end to end:

```
market_overview_agents.py:28   Agent(llm=PROJECT_LLM)     → imported
config.py:176                  PROJECT_LLM = create_default_llm(...)   → factory_call
config.py:124                  def create_default_llm(...): return LLM(model=get_env_var(model), …)
config.py:115                  def get_env_var(v): value = os.getenv(v); return value   → runtime_external
```

**Build the cross-module hop and the factory follower — two substantial
resolver capabilities — and on this corpus you arrive at `os.getenv`.** The
model string is not in the repository at any depth.

This required one fix mid-build worth flagging: the first version of the factory
follower only inspected `return` expressions, so `value = os.getenv(v); return
value` scored `static`. Resolving a returned bare name against the function's own
locals is what makes it `runtime_external` — and calling it static would have been
exactly the over-claim of reachability the spec warns against, in the opposite
direction.

---

## The narrative questions, answered

**Did the new repo move `local`?** No. **0 of 8**, matching 0 of 6 original and
v1's 0 of 95. Across 103 agent sites now surveyed, not one kwarg reference
resolves to a function-local variable. The deferred scope walker stays deferred —
this is the third independent corpus to say so.

**Did it move `factory_call`?** At agent sites, no (0). In the binding census,
**yes, decisively**: 5 of 5 factories in the corpus are new-cohort. But the
follow-through says the capability does not pay: 80% of them terminate in
`os.getenv`.

**Did it move `runtime_external`?** At agent sites, no — 0, because the runtime
dependency is three hops away and v2 correctly declines to claim what it cannot
see. In the factory census, yes: 4 of 5. The honest summary is that
`runtime_external` is **reachable only by the resolver capabilities that would
have to be built first**, which is itself the argument against building them.

**Does anything argue for reordering resolver priorities?** Yes — one thing, and
it is not what I expected:

`imported` at **75% of new-cohort references** is now the single largest
addressable category. Cross-module import following is the only capability the
new corpus argues for, and it is cheap relative to factory-following (resolve a
module path, re-run the existing module-scope pass). But the two latent chains it
would recover both end in `os.getenv`. **The correct move is to follow the import
one hop, discover the factory, and then stop and report `runtime_external` with
evidence** — the three-state model already has the vocabulary for this, and it is
what the C2 scanner already does correctly for `create_llm(...)`.

Ranked, on 103 agent sites:

1. **Cross-module import following, one hop, terminating honestly.** 6 of 8
   new-cohort references; 0 original. Recovers the *shape* even when the value is
   runtime.
2. **Inheritance-aware `self.<attr>`.** The 2 `unresolved_local` are
   `self.stocktwit_llm` / `self.technical_ind_llm`, bound in a **base class** via
   `super().__init__(...)` — a construction shape no original corpus contained.
   Small, cheap, and currently a silent miss.
3. **Nothing else.** `local` 0/103, `argument_passed` 0/103, agent-site
   `factory_call` 0/103.

---

## What else the new repo changed

- **Kwarg surface is 3 wide**: `config` 8/8, `llm` 8/8, `verbose` 8/8. Nothing
  else. Zero identity fields — a fourth corpus at 0% for `role`/`goal`/`backstory`.
- **`config=` holds at 100%** — now 69/100/100/100/100% across five corpora.
- **A construction surface not in the schema**: 6 of 8 agents are `@agent` in
  `@CrewBase`; the other 2 are plain methods on an undecorated class that loads
  its own YAML with `os.path.dirname(__file__)` — the `__file__`-relative config
  base, distinct from both `self.agents_config` and `screenplay_writer`'s
  `Path.cwd()`.
- **`llm_shape`** is `name` ×6 / `attribute` ×2 — no calls, no constants. Fifth
  corpus, fifth distribution.

---

## Caveat

One new repo, 8 agent sites, same author as the other four. The `local` result
is now robust across 103 sites and three independent additions. The cohort
divergence on `imported` (6/6 vs 0/8) is stark but rests on a single new corpus —
it should be confirmed by a second `new` repo before it reorders a roadmap.
