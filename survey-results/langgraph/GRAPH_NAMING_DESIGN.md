# Naming the StateGraph — four strategies, a gate, and a cascade

Revised for the correct unit: **the `StateGraph` is the agent.** Nodes are where
AI assets (models, tools, prompts) are harvested from; the harvested assets and
the graph they hang off need one name, and that name belongs to the graph.

Measured against the same four repos — **7 graph sites**, all `StateGraph`, from
an AST scan plus the deployment manifests.

---

## Your problem, confirmed in the data

Every signal a parser reaches for first is generic at these sites:

| Signal | Values across the 7 graph sites |
|---|---|
| builder variable | `graph`, `builder`, `self.workflow`, `graph_builder`, `graph`, `general_reflection_graph`, `multi_reflection_graph` |
| compiled variable | `workflow`, `graph` ×4, `general_reflection_graph`, `multi_reflection_graph` |
| enclosing function/class | `create_graph`, `_build_workflow` / `class Graph` |
| **`langgraph.json` key** | **`agent`**, **`agent`**, `main`, `cron`, `general_reflection_graph`, `multi_reflection_graph` |

Five of seven builder variables are `graph`/`builder`/`workflow`, and the
deployment manifest — the most authoritative-looking source — literally says
**`"agent"`** in two of the three repos that have one. That is precisely the
name you're getting, and it comes from a source that looks canonical.

Signal coverage:

| Signal | Present | Usable after generic filter |
|---|---|---|
| `compile(name="…")` | 1 / 7 | 1 / 7 |
| `langgraph.json` graph key | 6 / 7 (5 direct, 1 via wrapper module) | 4 / 7 |
| state schema class | 7 / 7 | 4 / 7 |
| builder / compiled variable | 7 / 7 | 2 / 7 |
| README H1 | 4 / 4 repos | 4 / 4 |
| `pyproject` name | 1 / 4 repos | 1 / 4 (`eaia` — an acronym) |

---

## The structural insight: count the graphs in the repo first

Three of the four repos contain **exactly one graph**. One contains **four**.
That distinction decides the whole naming approach:

- **One graph in the repo** → the repo *is* the agent. Repo identity is by far
  the best name available: `Agentic Company Researcher` instead of `agent`.
- **Several graphs** → repo identity cannot discriminate, so it becomes a
  *qualifier* and a per-graph discriminator supplies the tail:
  `Executive AI Assistant: Cron`.

Get this wrong in either direction and you either emit `agent` four times or
emit the repo name four times.

---

## Strategy 1 — Declared graph name (`compile(name=…)`)

**Algorithm.** Find `<builder>.compile(...)`; if it carries a `name=` string
constant, use it.

**Signals.** LangGraph's own graph-naming API.

**Strengths.** The only in-code, author-declared, purpose-built graph name. It is
what LangGraph itself reports for the graph at runtime, so it matches traces and
Studio. Highest precision available. In `gemini-fullstack` it yields
**`Pro Search Agent`** — while that same graph's manifest key is `agent`, so this
strategy is *strictly better than the manifest* where both exist.

**Weaknesses.** Rare: 1 of 7 sites. Optional in the API and almost nobody sets
it. Cannot be relied on as a primary path.

**Example.** `graph = builder.compile(name="pro-search-agent")` → **`Pro Search Agent`**

---

## Strategy 2 — Deployment identity (`langgraph.json`)

**Algorithm.** Parse `langgraph.json`; each `graphs` entry maps a key to
`./path/to/file.py:variable`. Resolve the variable back to the `StateGraph(...)`
site — usually via the compiled variable, sometimes through a wrapper module.
Use the key.

**Signals.** The deployment manifest — the same file LangGraph Platform and
`langgraph dev` use.

**Strengths.** Best coverage of any per-graph signal (6 of 7) and it is a
*deliberate* name: it is how the graph is addressed when served, so it matches
what an operator sees. Uniquely valuable in multi-graph repos — it is the only
signal that cleanly separates `eaia`'s four graphs. Also acts as a filter for
what matters: a graph listed in the manifest is a deployed entry point, not an
internal helper.

**Weaknesses.** Frequently generic — `agent` ×2, `main` ×1, so 2 of 6 keys are
unusable and a third is weak. Resolution is not always direct: in
`company-research-agent` the manifest points at `langgraph_entry.py:graph`, which
is `Graph().compile()`, whose `StateGraph` lives in `backend/graph.py` — a
three-hop trace. Absent entirely in `graph_websearch_agent`. Keys often carry a
redundant `_graph` suffix.

**Examples.**

| Manifest entry | Output |
|---|---|
| `"cron": "./eaia/cron_graph.py:graph"` | `Cron` |
| `"general_reflection_graph": "…:general_reflection_graph"` | `General Reflection` |
| `"agent": "./langgraph_entry.py:graph"` | *(rejected — generic)* |

---

## Strategy 3 — Repository identity

**Algorithm.** README first `# ` heading, cleaned: strip emoji, strip trailing
framework boilerplate (`with LangGraph`, `LangGraph Quickstart`). Fall back to
`pyproject` `name`, then the repo directory name. Use as the **name** when the
repo has one graph; as a **qualifier prefix** when it has several.

**Signals.** `README.md`, `pyproject.toml`, directory name.

**Strengths.** The only signal written for humans, and it shows: `Agentic Company
Researcher`, `Custom WebSearch Agent`, `Executive AI Assistant`. Present in all
four repos. Solves the single-graph case outright, which is 3 of the 4 repos
here. Gives the qualifier that makes multi-graph names readable.

**Weaknesses.** Repo-scoped, so it cannot discriminate between sibling graphs —
useless alone in a multi-graph repo. Vulnerable to marketing/template titles:
`Gemini Fullstack LangGraph Quickstart` describes a template, not an agent.
Cleanup is heuristic. `pyproject` names are often unhelpful acronyms (`eaia`).
Breaks down for monorepos holding several unrelated agents.

**Examples.**

| Input | Output |
|---|---|
| `# Agentic Company Researcher 🔍` | `Agentic Company Researcher` |
| `# Custom WebSearch Agent with LangGraph` | `Custom WebSearch Agent` |
| `# Gemini Fullstack LangGraph Quickstart` | `Gemini Fullstack` *(weak — beaten by S1 here)* |

---

## Strategy 4 — Structural composition

**Algorithm.** State schema class first — strip a trailing `State` — if it is not
generic. Otherwise the defining module basename, skipping non-semantic names
(`graph`, `main`, `__init__`) and path segments (`src`, `backend`, `app`),
stripping a `_graph`/`_graphs` suffix.

**Signals.** `StateGraph(<StateClass>)` first argument, file path, package name.

**Strengths.** Always available — the state schema is a required argument, so
there is always something. The state class is genuinely descriptive when authors
name it well: `JobKickoff`, `MultiMemoryInput`, `ReflectionState`,
`AgentGraphState`. Module paths are informative (`cron_graph`,
`reflection_graphs`, `agent_graph`). Guarantees the cascade terminates.

**Weaknesses.** The state class is generic about as often as it is useful —
`State`, `InputState`, `OverallState` are 3 of 7. Names the *data shape*, not the
behaviour, which can mislead: `Job Kickoff` describes the cron graph's input,
not the graph. Module names collapse when every file is `graph.py`.

**Examples.**

| Input | Output |
|---|---|
| `StateGraph(MultiMemoryInput)` | `Multi Memory Input` |
| `StateGraph(AgentGraphState)` in `agent_graph/graph.py` | `Agent Graph` |
| `StateGraph(InputState)` in `backend/graph.py` | *(both generic — rejected)* |

---

## The quality gate

Applied to each candidate; failure falls through to the next strategy.

1. **Not in the generic blocklist** — `agent`, `graph`, `main`, `app`,
   `workflow`, `chain`, `state`, `builder`, `default`, `langgraph`, `backend`,
   `entry`, `src`. This one rule is what stops the manifest's `"agent"` from
   winning.
2. **Not a bare state-schema word** — `State`, `InputState`, `OverallState`,
   `GraphState`, `AgentState`.
3. **≥3 characters** after normalisation.
4. **Unique within the repository.** Scope matters again: two repos may both have
   a `Cron` graph, and that is fine.
5. **Redundant-suffix strip** — drop a trailing `Graph`/`Graphs` from a
   discriminator (`General Reflection Graph` → `General Reflection`), never when
   it would collide with a sibling.

---

## Cascade and composition

```
S1 compile(name=)  →  S2 langgraph.json key  →  S3 repo identity  →  S4 structural
```
then: **if the repo holds more than one graph and the winner was not S1**, emit
`"<repo identity>: <discriminator>"`, where the discriminator is the first
non-generic of {manifest key, structural}. If that still collides with a sibling,
fall to the structural tail, then to a line disambiguator.

### Results — all 7 sites

| Graph site | Naive (builder var) | Cascade output | Source |
|---|---|---|---|
| `graph_websearch/agent_graph/graph.py:35` | `graph` | **Custom WebSearch Agent** | S3 repo identity |
| `gemini-fullstack/…/graph.py:269` | `builder` | **Pro Search Agent** | S1 `compile(name=)` |
| `company-research/backend/graph.py:56` | `self.workflow` | **Agentic Company Researcher** | S3 repo identity |
| `eaia/cron_graph.py:50` | `graph` | **Executive AI Assistant: Cron** | S2 + repo qualifier |
| `eaia/reflection_graphs.py:97` | `general_reflection_graph` | **Executive AI Assistant: General Reflection** | S2 + repo qualifier |
| `eaia/reflection_graphs.py:186` | `multi_reflection_graph` | **Executive AI Assistant: Multi Reflection** | S2 + repo qualifier |
| `eaia/main/graph.py:162` | `graph_builder` | **Executive AI Assistant** | S3 repo identity |

**7 / 7 named, 7 / 7 unique within their repo, zero generic names.**

Note the last row is a desirable emergent property rather than a special case:
`eaia`'s `main` graph has a generic manifest key (`main`) and a generic state
class (`State`), so it falls through to repo identity and becomes
**`Executive AI Assistant`** — the primary graph inherits the product name, and
the secondary graphs are qualified beneath it. That is the right shape.

---

## Recommendation

- **Name the graph, not the nodes.** Harvested assets roll up to the graph's name.
- **Cascade S1 → S2 → S3 → S4**, gated, with the multi-graph qualifier rule.
- **Count graphs per repo before naming** — it selects between "repo identity is
  the name" and "repo identity is the prefix".
- **Prefer `compile(name=)` over `langgraph.json`.** It is rarer but strictly
  better where both exist, and the manifest's key is generic more often than not.
- **Emit provenance and confidence.** Record
  `name_source: compile_name | manifest_key | repo_identity | structural` — a
  name from S1 or a non-generic S2 is high confidence; one from S3 in a
  multi-graph repo, or from S4, deserves review.
- **Treat manifest membership as a signal of importance**, separate from naming:
  a graph listed in `langgraph.json` is a deployed entry point; one that is not
  may be an internal sub-graph.

## Caveats

Seven graph sites in four repos. The single-graph-repo case is 3 of 4 here and
that ratio will not hold for larger codebases, where the qualifier path — which
has only one repo of evidence behind it — becomes the common path. `compile(name=)`
has exactly one occurrence, so its ranking rests on being correct in principle
rather than on frequency. The README-cleanup heuristics are tuned to four titles
and will need extending; `Gemini Fullstack LangGraph Quickstart` shows the failure
mode already, and it was only rescued because that repo happened to set
`compile(name=)`.
