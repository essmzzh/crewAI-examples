# LangGraph agent naming — implementation spec

**Unit:** the `StateGraph` is the agent. Nodes are where AI assets (models,
tools, prompts) are harvested; the harvested assets and the graph they attach to
share one name, and that name belongs to the graph.

**Principle:** prefer names the author *declared*. Where none exists, emit a
stable structural identifier and mark it low confidence. Never invent a token
that does not appear in the repository.

Measured on 8 `StateGraph` sites across 5 repos (`graph_websearch_agent`,
`gemini-fullstack-langgraph-quickstart`, `company-research-agent`,
`executive-ai-assistant`, `fastapi-langgraph-agent-production-ready-template`).

---

## The cascade

Walk tiers in order; first non-empty result wins. The terminal tier always
yields, so naming never fails.

### T1 — `compile(name="…")`, static only

```python
graph = builder.compile(name="pro-search-agent")   # ast.Constant  -> use verbatim
```

LangGraph's own naming API and the only author-declared graph name in the
language. Ranks first because where it coexists with a manifest key it is
strictly better (`pro-search-agent` vs the manifest's `agent`).

- `ast.Constant` → use the string verbatim.
- `ast.JoinedStr` (f-string) → **do not resolve.** Record
  `name_source = compile_name_dynamic` with the unparsed expression as evidence,
  and fall through. Resolving it needs cross-module lookup plus a
  `os.getenv(X, "<default>")` rule — three capabilities for one site.

**Coverage: 1 / 8.**

### T2 — `langgraph.json` graphs key

```json
"graphs": {
  "main":                     "./eaia/main/graph.py:graph",
  "cron":                     "./eaia/cron_graph.py:graph",
  "general_reflection_graph": "./eaia/reflection_graphs.py:general_reflection_graph"
}
```

A schema'd config file — a deterministic parse, not a heuristic. Highest
coverage of any signal here.

Resolution rules that are **not optional**:

1. **Remove the `len(graphs) == 1` guard.** It discards the entire file for
   multi-graph repos. `executive-ai-assistant` registers four correctly-named
   graphs and gets none of them today.
2. **Match on the compiled variable, not the builder.** Entries point at
   `:graph`, the result of `builder.compile()`; the `StateGraph` site is bound to
   `graph_builder`. Follow the `compile()` assignment to link them — they share a
   name in `reflection_graphs.py` and differ in `main/graph.py`.
3. **Allow one wrapper hop.** `company-research-agent`'s entry is
   `./langgraph_entry.py:graph` → `Graph().compile()` → `StateGraph` in
   `backend/graph.py`.

**Coverage: 6 / 8 sites carry a manifest entry. The guard removal alone fixes
4 / 8** (single-graph manifests already work).

### T3 — Graph variable, verbatim

Compiled variable, else builder variable. Strip a leading `self.` and nothing
else. No suffix stripping, no case surgery.

`workflow`, `graph`, `general_reflection_graph`, `_graph`

**Coverage: 8 / 8** (always present when the graph is assigned).

### T4 — Enclosing class, then enclosing function

Gated by the same blocklist. Expect it to fire rarely.

**Coverage: class 2 / 8, function 3 / 8 — and all five values are generic**
(`Graph`, `LangGraphAgent`, `create_graph` ×2, `_build_workflow`). It changes
exactly one output on this corpus. Included because it is ~5 lines and reuses
machinery T3 already needs; not because it is expected to pay.

The structural reason it is weak: an enclosing scope names the *builder*
(`create_graph`, `_build_workflow`) — the agent's purpose lives in the graph, not
in the factory around it. Contrast the node level, where class names are strong
(`PlannerAgent`, `NewsScanner`) because there the class *is* the thing.

### T5 — Terminal

If the graph is not bound to any variable (`StateGraph(X).compile()` chained),
use `<module_stem>:<line>`. Always yields.

---

## Gate and qualification

The gate does **not** decide whether to use a name — the cascade already picked
one. It decides whether to **qualify** it and what confidence to attach.

```python
GENERIC = {"agent", "graph", "main", "app", "workflow", "builder", "state",
           "default", "chain", "entry", "langgraph", "backend", "frontend",
           "src", "core"}
```

1. If `local_name.lower()` is in `GENERIC`, **or** it collides with another
   graph already named in this repository → qualify.
2. Qualify with the **repository name from git metadata** — already on every
   asset record, zero parsing.
   `company-research-agent/agent`, `executive-ai-assistant/main`
3. If still colliding after qualification, append the module stem verbatim.

**Not the README.** Prose parsing (emoji stripping, "with LangGraph" suffix
rules, markdown-shape assumptions) is an unbounded heuristic surface and reads
marketing copy rather than an identifier.

---

## Output fields

Emit on every graph record:

| Field | Values |
|---|---|
| `name` | the resolved name |
| `name_source` | `compile_name` \| `manifest_key` \| `graph_variable` \| `enclosing_scope` \| `structural` |
| `name_qualified` | bool — was the repo prefix applied |
| `confidence` | `high` \| `medium` \| `low` |
| `name_evidence` | for `compile_name_dynamic`, the unparsed expression |

Confidence rule:

- **high** — T1, or T2 with a non-generic key
- **medium** — T2 with a generic key, repo-qualified
- **low** — T3, T4 or T5

This is what makes the weak cases safe: consumers filter on confidence rather
than trusting every name equally, and `name_source` makes a regression in any one
tier visible in the data instead of silent.

---

## Measured result

| Site | Name | Source | Confidence |
|---|---|---|---|
| gemini-fullstack | `pro-search-agent` | `compile_name` | high |
| executive-ai-assistant | `cron` | `manifest_key` | high |
| executive-ai-assistant | `general_reflection_graph` | `manifest_key` | high |
| executive-ai-assistant | `multi_reflection_graph` | `manifest_key` | high |
| executive-ai-assistant | `executive-ai-assistant/main` | `manifest_key` + repo | medium |
| company-research-agent | `company-research-agent/agent` | `manifest_key` + repo | medium |
| graph_websearch_agent | `graph_websearch_agent/workflow` | `graph_variable` + repo | low |
| fastapi-…-template | `fastapi-…-template/LangGraphAgent` | `enclosing_scope` + repo | low |

**8 / 8 named, all unique, every name traceable to a literal in the repository.**

**2 / 8 have no author-declared name anywhere** — no `compile(name=)`, no
`langgraph.json`. That is the honest floor. A stable, unique, visibly-weak name
plus `confidence: low` is the correct output; a consumer can filter it, and the
upstream fix is for the repo to add `compile(name=...)`.

---

## Rejected, and why

| Rejected | Reason |
|---|---|
| README H1 | Prose parsing; unbounded special-casing; marketing copy, not an identifier. |
| State-class strip-and-cut | Invents tokens present nowhere in source (`MultiMemoryInput` → `MultiMemory`), and still admits `JobKickoff` — a correct name for the *input payload*, not the graph. State classes name data, not behaviour. |
| Docstrings | 35% coverage and demonstrably wrong at least once in the corpus (copy-pasted docstring). No static check catches that. |
| Module-stem suffix stripping | Produced `lang` from `langgraph` and `agent` from `agent_graph` — the generic name the exercise exists to eliminate. Module stem survives only inside T5, verbatim. |

---

## Build order

| # | Change | Fixes | Cost |
|---|---|---|---|
| 1 | Drop `len(graphs) == 1`; resolve manifest by path + compiled var, one wrapper hop | 4 / 8 | medium |
| 2 | Repo-name qualification for generic and colliding names | 3 / 8 | low — git metadata |
| 3 | Read `compile(name=)` when `ast.Constant`; record + fall through on `JoinedStr` | 1 / 8 | low |
| 4 | Graph variable verbatim + `confidence: low` | 2 / 8 | low |
| 5 | Enclosing class/function, gated | 1 / 8 | low |

---

## Caveats

Eight graph sites, five repos — thin. Specifically:

- `compile(name=)` has one static occurrence, so its top ranking rests on being
  correct in principle rather than on frequency.
- `langgraph.json` coverage of 6/8 is the number most likely to fall on a wider
  corpus: libraries rather than deployables will not carry one, and those land
  on the low-confidence path.
- The T4 verdict (0/8 usable) is consistent with the structural argument but is
  not proven by 8 sites; the argument is what to lean on.
- The blocklist is seeded from what these five trees contain and will need
  extending.
