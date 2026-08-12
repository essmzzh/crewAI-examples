# Scanner output vs. survey ground truth

Validation of the scanner's agent inventory against the four hand-measured
fixtures. Ground truth is `agent_sites.jsonl` in this repo (C1) and under
`survey-results/` (C2–C4), produced by `survey.py` via `ast.parse` only.

---

## Discovery: exact match, 37/37

Compared on `(file, line)` — not just counts.

| Corpus | Scanner | Ground truth | Missed | Extra |
|---|---|---|---|---|
| C1 crewAI-examples (trimmed) | 13 | 13 | 0 | 0 |
| C2 academic-commercialization | 6 | 6 | 0 | 0 |
| C3 ai-crewai-multi-agent | 2 | 2 | 0 | 0 |
| C4 PurpleCrew | 16 | 16 | 0 | 0 |
| **Total** | **37** | **37** | **0** | **0** |

Every line number matches. Component counts match too:

| | Scanner | Ground truth |
|---|---|---|
| Tools attached to agents | 40 | 40 |
| Foundation models | 12 | 12 |
| Prompt-source attribution (inline vs config) | — | 0 mismatches / 37 |

Resolution methods agree with the survey's independent classification in every
case:

| Site | Scanner | Survey |
|---|---|---|
| stock_analysis `llm=` | `module_var` | `module` → `Ollama(model='llama3.1')` |
| ai-crewai-multi-agent `llm=` | `self_attr` | `self_attr`, bound in `__init__` |
| academic-commercialization `llm=` | unresolved, `reason: runtime` | `call`, unresolvable — correct refusal |
| trip_planner tools | `namespace_attr` | `namespace_attr` |
| stock_analysis tools | `call` | `Call` elements |
| PurpleCrew tools | `reference` | `self_attr` ×8 / `module` ×5 |
| trip_planner prompts | `inline` | all three identity fields present |
| everything else | `config` | `config=` subscript present |

Notably correct: the scanner **declines** to resolve
`create_llm(json_mode=True, temperature=0.0)` and records `reason: "runtime"`
with the source expression as evidence. That is the right call — the survey
confirmed the factory terminates in `LLM(**kwargs)`, with no readable model
string at any depth.

Discovery and resolution are sound. Everything below is about the emitted
record, not about what was found.

---

## 0. Prompt values are silently truncated at 300 characters

Found after the first pass. Every emitted prompt `value` is hard-cut at exactly
300 characters — no ellipsis, no flag, cutting mid-word and preserving the
trailing space, which is the signature of a `[:300]` slice rather than display
abbreviation.

Verified against source YAML: the `screenplay_writer` `scorer.goal` is 1,383
characters; the emitted value is its first 300, and the tail carrying the actual
scoring rubric ("7-9: Good... 10: Excellent...") is gone.

Blast radius across the four fixtures' `config/agents.yaml` files:

| Corpus | Prompts over 300 chars | Share |
|---|---|---|
| C1 crewAI-examples | 1 of 24 | 4% |
| C2 academic-commercialization | 6 of 18 | 33% |
| C3 ai-crewai-multi-agent | 0 of 6 | 0% |
| C4 PurpleCrew | 13 of 51 | 25% |
| **Total** | **20 of 99** | **20%** |

Worst losses:

| Prompt | True length | Lost |
|---|---|---|
| C2 `commercialization_scorer.backstory` | 22,224 | 21,924 (**99%**) |
| C2 `report_reviewer.backstory` | 3,748 | 3,448 (92%) |
| C2 `commercialization_report_writer.backstory` | 1,625 | 1,325 (82%) |
| C1 `scorer.goal` | 1,383 | 1,083 (78%) |
| C4 `RedTeamManager.backstory` | 935 | 635 (68%) |

**One in five prompts loses content, and the largest loses 99% of it.**

The compounding problem: `version` is a content hash. If it hashes the emitted
(truncated) value, then **every edit after character 300 is invisible to
versioning** — precisely the long system prompts most likely to be iterated on.
For `commercialization_scorer.backstory`, 99% of the text could be rewritten
without the version moving. That is a one-line check: mutate character 301 of a
prompt and see whether `version` changes.

(If the truncation exists only in this dump and not in the stored record, this
item is moot — worth confirming before acting on it. Nothing else in the payload
suggests that; the cuts land at exactly 300 with no marker.)

---

## 1. Provenance on C1 is wrong, and it breaks the drift check

Every C1 record carries:

```
"branch": "main",
"commit_hash": "da94a91e691e1cf5b3151416bb15b5b62729bea8"
```

`da94a91e` is a real commit in this repository — the upstream
*pre-trim* state ("Bump the uv group across 18 directories"). At that commit the
tree holds **116 `.py` files, all 31 sub-projects, and 71 agent sites**;
`flows/`, `integrations/`, `notebooks/` and `crews/instagram_post` are all
present.

The scanner did not scan that tree. It returned exactly the 13 agents of the
**trimmed** fixture and nothing from the removed projects. It scanned the
trimmed working tree and stamped provenance from an unrelated ref.

The reason line numbers cannot disambiguate this: all three kept files are
byte-identical between `da94a91e` and `HEAD`, so the sites it did find look the
same either way. The only evidence is the 58 agents that are absent.

C2, C3 and C4 provenance is correct — their hashes match the cloned HEADs
exactly (`893d2704`, `d14aa0c3`, `dc593e87`).

**Consequence.** The harness gates fixture drift on `commit_hash`. It will
compare a ground-truth total of 13 against a commit whose actual content yields
71, and report drift permanently — or, once someone silences that, mask a real
regression. `branch: "main"` is wrong too; the fixture lives on
`claude/crewai-corpus-survey-ln0o1w`. **Highest-severity item here**, and the
only one that defeats the stated purpose of the corpus work.

---

## 2. `id` is not unique per emitted record

`crews/stock_analysis/src/stock_analysis/crew.py` lines 23 and 67 are two
distinct methods — `financial_agent()` and `financial_analyst_agent()` — that
both read `self.agents_config['financial_analyst']` with identical kwargs. The
scanner emits both, with **the same `id` and the same `version`**:

```
id      81006a544b98ece4467f7735e4d4ab7397d4e1ac25a4cac07e6750cba7e5ec59
version 56fba282e543c0229f0b51038c5f65be6b634d1fed9102b4a62695d981302ea1
```

Two records, identical on both fields, differing only in `location.line`.
Anything that keys on `id` (or `id`+`version`) will silently drop one and keep
an arbitrary line number.

The same pattern runs through prompts, at much larger scale. Prompt `id` appears
to be `hash(source_file, slot)`, so every agent sharing a config file shares its
`role`/`goal`/`backstory` ids:

- **111 prompt records → 27 distinct `id` values** (9 config sources × 3 slots).
- All 5 screenplay_writer agents share one `role` id; all 7 redteamcrew agents
  share another.

`version` is the real discriminator and does vary by content — except where the
underlying value is genuinely identical, as in the `financial_analyst` case
above, where the collision is total.

This may be intentional (`id` = slot identity, `version` = content). If so it is
worth saying so explicitly, because the natural reading of `id` in an asset
inventory is "primary key", and it is not one. Note the two colliding methods
have *different* names (`financial_agent` / `financial_analyst_agent`) — naming
from the method rather than the config key would have separated them.

---

## 3. Framework label is wrong on all 37 records

Every `description` reads "*is a **LangGraph** agent*". These are CrewAI agents —
`from crewai import Agent`, `@CrewBase`, `@agent`, `config=self.agents_config[...]`.
No LangGraph anywhere in any of the four corpora. Cosmetic in the data model,
but it is the first thing a human reads, and it is wrong 37 times out of 37.

---

## 4. One name is taken from a tool, not an agent

`crews/trip_planner/tools/browser_tools.py:24` is emitted as
`scrape_and_summarize_website`. That is the name of the enclosing
`@tool`-decorated method; the agent constructed inside it has inline
`role="Principal Researcher"`. The survey flagged this site as the corpus's one
agent-inside-a-tool construction, and it is the only place the
name-from-enclosing-function heuristic produces a tool name for an agent. Low
severity, but "Principal Researcher" is the better label and is already
available in the record.

---

## 5. Crew- and Task-level assets are not emitted

Only `asset_type: "agent"` appears. The survey found, across the same four trees:

| Kind | Count |
|---|---|
| agent | 37 (all emitted) |
| task | 51 |
| crew | 8 |
| LLM | 1 |

If that is the intended scope, one consequence should be recorded deliberately:
**PurpleCrew's model configuration becomes invisible.** All 16 of its agents
correctly show `foundation_models: []` — they have no `llm=`. The model lives on
the Crew: `Crew(manager_llm="GPT-4o")`, twice. That string is the **only literal
model identifier across all four corpora**, and no agent-scoped inventory can
see it. PurpleCrew reads as a 16-agent system with no models at all.

(It is also miscased — LiteLLM ids are lowercase `gpt-4o` — a defect in the
surveyed repo, not in the scanner.)

Two other Task-level findings from the survey are likewise unreachable:
`Task(tool=[...])` singular in three places in PurpleCrew, where the field is
`tools` and those four tools are probably not attached; and `guardrail` /
`guardrail_max_retries` on all six academic-commercialization tasks.

---

## Verdict

**Discovery and resolution: pass, cleanly.** 37/37 sites at exact line numbers,
40/40 tools, 12/12 models, resolution methods agreeing with an independently
derived classification, and correct refusal on the one genuinely unresolvable
model. No false positives, no false negatives.

**Emission: four fixes needed before this gates anything.**

0. **Stop truncating prompt values at 300 characters.** 20% of prompts lose
   content, one of them 99% of it, and content hashing over a truncated value
   makes drift undetectable on exactly those prompts.
1. **Stamp provenance from the tree actually scanned.** C1 reports a commit whose
   real content is 5.5× the fixture. This defeats the drift check outright.
2. **Make `id` unique per record, or document that it is not.** 37 agent records
   carry 36 distinct ids; 111 prompt records carry 27.
3. **Fix the framework label.** CrewAI, not LangGraph, on all 37.

Plus two judgment calls to make explicitly rather than by omission: whether
Crew-level `manager_llm` should reach the inventory, and whether an agent nested
in a `@tool` method should be named for its role.
