# `_graph_name()` — the production-practical subset

Narrowed to signals that are **declared by the author** and **parsed
deterministically**. No prose parsing, no string surgery on identifiers.
Measured on 8 real `StateGraph` sites across 5 repos.

---

## Dropped, and why

| Dropped | Reason |
|---|---|
| **README H1** | Prose parsing. Needs emoji stripping, "with LangGraph" suffix rules, markdown-shape assumptions. Marketing copy, not an identifier. Unmaintainable at crawler scale — every new repo is a new special case. |
| **State-class strip-and-cut** | Invents tokens that appear nowhere in the source. `MultiMemoryInput` → `MultiMemory` is a name no one wrote. And it never fixes `JobKickoff`, which is a correct name for the *wrong thing* (the input payload, not the graph). |
| **Docstrings** | 35% coverage on nodes, and demonstrably wrong at least once in the corpus (a copy-pasted docstring). No static check can catch that. |
| **Module-stem suffix stripping** | Produced `lang` from `langgraph`, and `agent` from `agent_graph` — the generic name the exercise exists to eliminate. |

---

## Kept — three signals, in order

### 1. `compile(name="…")` when it is `ast.Constant`

Author-declared through LangGraph's own API. Zero interpretation: read the kwarg,
use the string. **1 of 8 sites.** Small, but when it fires it beats everything —
on the gemini site it gives `pro-search-agent` where the manifest says `agent`.

`JoinedStr` → record `name_source=compile_name_dynamic` with the expression and
fall through. Do not attempt to resolve the f-string; that needs cross-module
resolution plus a `getenv`-default rule for one site in this corpus.

### 2. `langgraph.json` graphs key

A config file with a defined schema — a deterministic parse, not a heuristic.
**6 of 8 sites carry one**, the highest coverage of any signal here.

Two distinctions worth keeping straight for prioritisation:

- The **signal** is worth 6/8.
- The **fix** (removing `len(graphs) == 1`) is worth 4/8 — single-graph manifests
  already work today; it is `executive-ai-assistant`'s four that are discarded.

Two resolution details that are not optional:

- Entries point at the **compiled** variable (`:graph`), not the builder. You
  need the `compile()` assignment to link back to the `StateGraph` site — they
  share a name in `reflection_graphs.py` and differ in `main/graph.py`.
- **One wrapper hop**: `company-research-agent`'s entry is
  `./langgraph_entry.py:graph` → `Graph().compile()` → `StateGraph` in
  `backend/graph.py`.

### 3. Graph variable name, verbatim

The compiled variable, else the builder variable. No stripping, no casing
changes beyond trimming a leading `self.`. Deterministic and always present.
This is the honest fallback — it says what the code says.

---

## Qualification: use the repo name you already have

Not the README — the **repository name from git metadata**, which the crawler
already carries on every asset record. Zero parsing, always available.

Qualify when the local name is generic (`agent`, `graph`, `main`, `workflow`,
`app`, `builder`, `state`) or when it collides with a sibling in the same repo.
On a collision after qualification, append the module stem verbatim.

### Result — 8 of 8, fully deterministic

| Site | Name | Source | Confidence |
|---|---|---|---|
| gemini-fullstack | `pro-search-agent` | `compile_name` | high |
| executive-ai-assistant | `cron` | `manifest_key` | high |
| executive-ai-assistant | `general_reflection_graph` | `manifest_key` | high |
| executive-ai-assistant | `multi_reflection_graph` | `manifest_key` | high |
| executive-ai-assistant | `executive-ai-assistant/main` | `manifest_key` + repo | medium |
| company-research-agent | `company-research-agent/agent` | `manifest_key` + repo | medium |
| graph_websearch_agent | `graph_websearch_agent/workflow` | `graph_variable` + repo | **low** |
| fastapi-…-template | `fastapi-…-template/_graph` | `graph_variable` + repo | **low** |

All unique, no invented tokens, every name traceable to a literal in the repo.

---

## The part worth accepting rather than engineering around

**2 of 8 graphs have no author-declared name anywhere** — no
`compile(name=)`, no `langgraph.json`. For those, the best honest output is a
structural identifier plus a low-confidence flag. That is the correct production
behaviour: a stable, unique, traceable name that is visibly not a good one, so a
consumer can filter or a human can fix it upstream by adding
`compile(name=...)`.

The alternative — README titles and stripped class names — buys prettier strings
for those two sites at the cost of a heuristic surface that will misfire
unpredictably on repos you have not seen.

**Emit `name_source` and `confidence` on every record.** That is what makes the
low-coverage cases safe: consumers filter on confidence rather than trusting
every name equally, and `name_source` makes a regression in any one strategy
visible in the data instead of silent.

---

## Recommended order

| # | Change | Fixes | Notes |
|---|---|---|---|
| 1 | Drop `len(graphs) == 1`; resolve manifest by path + **compiled var**, with one wrapper hop | 4 / 8 | highest-value fix; keep the generic check after it |
| 2 | Repo-name qualification for generic and colliding names | 3 / 8 | git metadata, no parsing |
| 3 | Read `compile(name=)` when `ast.Constant`; record + fall through on `JoinedStr` | 1 / 8 | ranks **first** in the cascade when it fires |
| 4 | Graph variable verbatim as terminal fallback + `confidence: low` | 2 / 8 | replaces state-name and README paths entirely |

Four changes, all deterministic, no heuristic surface added.

## Caveats

Eight sites, five repos. `compile(name=)` has one static occurrence, so its top
ranking rests on being correct in principle rather than on frequency. The
`langgraph.json` coverage of 6/8 is the number most likely to fall on a wider
corpus — repos that are libraries rather than deployables will not have one, and
those land on the low-confidence path.
