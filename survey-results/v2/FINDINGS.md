# Survey v2 — all six corpora in one run

`survey_v2.py`, one run, v2 categories throughout. Four `original` (surveyed
under v1) and two `new`.

**118 `.py` files, 0 parse failures, 50 agent sites** — 37 original (unchanged
from v1) + 13 new.

| Cohort | Corpus | Author | Units | Agents | Crews | Tasks |
|---|---|---|---|---|---|---|
| original | crewAI-examples (trimmed) | crewAI | 3 | 13 | 3 | 14 |
| original | academic-commercialization-agent | essmzzh | 1 | 6 | 1 | 6 |
| original | ai-crewai-multi-agent | essmzzh | 1 | 2 | 1 | 2 |
| original | PurpleCrew | essmzzh | 1 | 16 | 3 | 29 |
| new | AITradingCrew | essmzzh | 1 | 8 | 3 | 8 |
| **new** | **crewai-gmail-automation** | **tonykipkemboi** | 1 | **5** | 1 | 5 |

`crewai-gmail-automation` @ `0946e17` is the **first corpus by an independent
author**. Every previous run carried a caveat that the corpus was single-author;
this is the first evidence that isn't.

---

## Headline: the clean cohort split from the last run does not survive

Run 5 (one new repo) reported that the two cohorts shared no reachability
category — 6/6 original resolved in-module, 8/8 new left the module. Adding a
second new repo **walks that back**:

| Reachability | new (n=13) | original (n=6) | Total |
|---|---|---|---|
| `terminal_constructor` | **5 (38%)** | 6 (100%) | 11 |
| `imported` | 6 (46%) | 0 (0%) | 6 |
| `unresolved_local` | 2 (15%) | 0 (0%) | 2 |
| `local` | 0 | 0 | 0 |
| `argument_passed` | 0 | 0 | 0 |
| `factory_call` (agent sites) | 0 | 0 | 0 |
| `runtime_external` (agent sites) | 0 | 0 | 0 |

All 5 of the new repo's references are `terminal_constructor` — the same
category that was 100% of the original cohort. **The cohort divergence was a
property of AITradingCrew, not of "new code".** Recorded plainly because I
called it "total" and "stark" last run on a single corpus, and one more data
point halved it.

What remains true: **`imported` and `unresolved_local` are still exclusively
new-cohort** (8 of 8, all AITradingCrew). Cross-module resolution is still a
capability only the new cohort demands — but it is now demanded by one repo out
of six, not by "the new cohort".

---

## The new repo restores a shape the trim deleted

All 5 gmail agents read `llm=self.llm`, bound at **class-body** level:

```python
@CrewBase
class GmailCrewAi():
    llm = LLM(model="openai/gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

    @agent
    def categorizer(self) -> Agent:
        return Agent(config=self.agents_config['categorizer'],
                     tools=[FileReadTool()], llm=self.llm)
```

This is **kwarg-level `self.<attr>` → class-body binding** — the exact shape I
flagged as a coverage regression after trimming crewAI-examples. It had 8
occurrences in the pre-trim tree, all in removed `flows/` projects, and **zero
coverage in any fixture** afterwards. It is also the shape that broke the v1
resolver, which classified all 8 as `unresolved` and understated reachability by
33 points.

`crewai-gmail-automation` covers it again, at 5 sites. Across all six corpora,
`self_attr` now splits **5 `class_body` / 2 `__init__`** — the class-body form is
the majority, and it is back under test.

---

## It also validates the `runtime_external` boundary

`LLM(model="openai/gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))` is
classified `terminal_constructor`, not `runtime_external` — and that is the right
call. The **model is a static literal**; only the API key is runtime. v2's
`runtime_evidence` deliberately asks whether the value *is* runtime data, not
whether it *contains* a runtime sub-expression. Had it done the latter, this
constructor would have been written off as unreachable and a perfectly
recoverable model string lost.

`openai/gpt-4o-mini` is also the **first constant model string reachable from an
agent site** since crewAI-examples' `llama3.1`, and the corpus-wide model list is
now: `openai/gpt-4o-mini` ×6, `llama3.1` ×4, `gpt-4-turbo` ×2, plus
`GPT-4o` ×2 on `Crew(manager_llm=)` (still flagged: not lowercase).

---

## What did not move

**`local`: 0 of 13 new, 0 of 6 original, 0 of 108 agent sites surveyed to date.**
Fourth independent corpus addition, still zero. The deferred function-scope
walker stays deferred; this is now about as settled as anything in the survey.

**`factory_call` at agent sites: still 0.** The binding census is unchanged by
the gmail repo — all 5 factories in the corpus remain AITradingCrew's, and 4 of 5
still terminate in `os.getenv`. The gmail repo contributes 9 `terminal_constructor`
bindings and no factories at all.

**`argument_passed`: 0 across all six corpora.** Added in v2 as a distinct
resolver capability; it has yet to fire once.

**`config=`: 46 of 50 (92%)**, and 5/5 in the gmail repo via
`self.agents_config[...]`. Sixth corpus, still the only universal kwarg.
**Identity fields: 4 of 50 agents** carry all three — the gmail repo is the fifth
corpus at 0%.

---

## Does anything reorder the resolver priorities?

Marginally, and in the direction of doing *less*:

1. **Class-body `self.<attr>` resolution just became the highest-value confirmed
   capability.** 5 of 13 new-cohort references, majority of all `self_attr`
   bindings, previously untested, and cheap — it is a lookup in the class body
   the resolver already walks.
2. **Cross-module import following drops in priority.** Last run it was 75% of
   new-cohort references; with a second new repo it is 46%, all from one repo,
   and both latent chains it would recover end in `os.getenv`. Still worth one
   hop that terminates honestly, but no longer the headline.
3. **Inheritance-aware `self.<attr>`** (AITradingCrew's 2 `unresolved_local`,
   bound in a base class via `super().__init__`) is unchanged and still a silent
   miss.
4. **Nothing else.** `local` 0/108, `argument_passed` 0/108, agent-site
   `factory_call` 0/108.

---

## Fixture recommendation

`crewai-gmail-automation` is a better fixture than its size suggests: 8 `.py`
files, 5 agents, an independent author, and it is the **only** corpus covering
kwarg-level class-body binding. If the validation set takes one more repo, this
is the one — it closes the coverage gap the crewAI-examples trim opened, at a
fraction of the labelling cost of restoring `flows/email_auto_responder_flow`.

## Caveat

Two new repos, 13 agent sites, one of them by an independent author. The `local`
result is robust across 108 sites and four additions. The cohort story is now
visibly unstable — it inverted on the second data point — so cohort-level claims
should be treated as provisional until several more independent repos land.
