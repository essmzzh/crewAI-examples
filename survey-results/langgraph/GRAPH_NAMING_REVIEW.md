# Review of the `_graph_name()` assessment

Checked each of the four points against 8 real `StateGraph` sites — the four
survey repos plus `fastapi-langgraph-agent-production-ready-template`, cloned to
verify the example cited.

**All four points confirmed.** Two need a correction to the proposed fix, and one
signal is missing from the assessment entirely.

---

## 1. `compile(name=…)` never read — confirmed, with a caveat that changes the fix

Both cited examples verified in source:

```python
# gemini-fullstack/backend/src/agent/graph.py:293
graph = builder.compile(name="pro-search-agent")                    # ast.Constant — resolvable

# fastapi-langgraph-template/app/core/langgraph/graph.py:241-243
self._graph = graph_builder.compile(
    checkpointer=checkpointer,
    name=f"{settings.PROJECT_NAME} Agent ({settings.ENVIRONMENT.value})")   # ast.JoinedStr — not
```

Frequency across the 8 sites: **2 of 8 carry `name=`, but only 1 is a static
constant.** So the fix cannot be "read `name=`" — it has to branch:

- `ast.Constant` → use it. This is the highest-intentionality signal and it wins
  outright: on the gemini site it yields `Pro Search Agent` where the manifest
  key is `agent`.
- `ast.JoinedStr` → **do not guess and do not discard silently.** Record
  `name_source=compile_name_dynamic` with the unparsed expression as evidence,
  and fall through.

Worth knowing before you decide how hard to try on the dynamic case: it is
partially resolvable here.

```python
# app/core/config.py:136
self.PROJECT_NAME = os.getenv("PROJECT_NAME", "FastAPI LangGraph Template")
```

`os.getenv(X, "<literal>")` has a **static default**, so the f-string resolves to
`"FastAPI LangGraph Template Agent (…)"`. That is a real option, but it is a
cross-module resolution plus an f-string join plus a getenv-default rule — three
capabilities for one site in this corpus. My recommendation is to record the
dynamic case and fall through for now; the same repo's README H1 gets you
`FastAPI LangGraph Template` for free.

---

## 2. The `len(graphs) == 1` guard — confirmed, and it is the highest-volume fix

`executive-ai-assistant` registers four graphs, all correctly named, all
discarded today:

```json
"graphs": {
  "main":                     "./eaia/main/graph.py:graph",
  "cron":                     "./eaia/cron_graph.py:graph",
  "general_reflection_graph": "./eaia/reflection_graphs.py:general_reflection_graph",
  "multi_reflection_graph":   "./eaia/reflection_graphs.py:multi_reflection_graph"
}
```

**4 of 8 sites (50%)** sit behind this guard. Path+varname matching against the
scan results is the right fix, with two details worth building in from the start:

- **Match on the compiled variable, not the builder.** Entries point at
  `:graph`, which is the result of `graph_builder.compile()`; the `StateGraph`
  site is bound to `graph_builder`. You need the `compile()` assignment to link
  them. In `reflection_graphs.py` builder and compiled share a name, in
  `main/graph.py` they do not.
- **One hop for wrapper modules.** `company-research-agent`'s manifest points at
  `./langgraph_entry.py:graph`, which is `Graph().compile()`, whose `StateGraph`
  lives in `backend/graph.py`. Direct path matching misses it.

But lifting the guard is **necessary, not sufficient**: 2 of the 6 manifest keys
are literally `"agent"` and a third is `"main"`. The generic gate still has to
run after the manifest lookup, or you will have swapped one source of `"agent"`
for another.

---

## 3. State type names — confirmed, but the proposed filter is wrong in both directions

The proposed rule is *"anything ending in `State`, `Input`, or `Output`, or
containing `Graph`"*. Run against the 8 real state classes:

| State class | Proposed rule rejects? | Verdict |
|---|---|---|
| `AgentGraphState` | yes | correct |
| `OverallState` | yes | correct |
| `InputState` | yes | correct |
| `GraphState` | yes | correct |
| `State` | yes | correct |
| **`JobKickoff`** | **no** | **leaks — the exact case cited as bad** |
| **`ReflectionState`** | yes | **over-filters — `Reflection` is a good name** |
| **`MultiMemoryInput`** | yes | **over-filters — `MultiMemory` is usable** |

It still admits `JobKickoff`, which the assessment names as a failure, and it
discards two of the better structural names available.

**Strip-then-check does better** — remove `State`/`Schema`/`Input`/`Output`
suffixes and any `Graph` infix, *then* apply the same generic-word blocklist the
rest of the cascade uses:

| Input | Output |
|---|---|
| `AgentGraphState` → `Agent` | rejected (generic) |
| `OverallState` → `Overall` | rejected (generic) |
| `InputState` → `Input` | rejected (generic) |
| `GraphState` → `` | rejected (empty) |
| `State` → `` | rejected (empty) |
| `ReflectionState` → **`Reflection`** | kept |
| `MultiMemoryInput` → **`MultiMemory`** | kept |
| `JobKickoff` → `JobKickoff` | kept |

`JobKickoff` still survives, and no pattern rule will fix that, because it is not
a *malformed* name — it is an accurate name for the wrong thing. It describes the
cron graph's **input payload**, not the graph's behaviour. That is the general
property of state classes and the reason to rank them low in the cascade rather
than try to filter them into shape. In the cron case the manifest key `cron`
outranks it anyway.

---

## 4. Module path stem — confirmed missing, but much weaker than "the most honest name available"

Tested against all 8 sites:

| Site | Stem yields | |
|---|---|---|
| `agent_graph/graph.py` | `agent` | **generic — the exact bad name** |
| `backend/src/agent/graph.py` | `agent` | generic |
| `backend/graph.py` | `graph` | generic |
| `eaia/main/graph.py` | `main` | generic |
| `app/core/langgraph/graph.py` | `lang` | **broken — naive `graph` strip mangles `langgraph`** |
| `eaia/cron_graph.py` | `cron` | usable |
| `eaia/reflection_graphs.py` | `reflection` | usable |
| `eaia/reflection_graphs.py` | `reflection` | **collides with its sibling** |

**Usable in 3 of 8, and one of those three collides.** The assessment's own
example proves the problem: `agent_graph/graph.py → "agent"` is the generic name
the whole exercise is trying to eliminate.

It is still worth adding — `cron` is a genuinely good name and nothing else
produces it — but as a **guarded last resort**, with: the generic blocklist
applied, a sibling-collision check (two graphs in one file is not hypothetical),
and a suffix strip that will not turn `langgraph` into `lang`.

---

## What the assessment misses: repository identity

There is no repo-level signal in the current cascade or the proposed fixes. That
is the largest remaining gap, because **3 of the 4 surveyed repos contain exactly
one graph**, and for a single-graph repo the repo *is* the agent.

Applying all four proposed fixes and nothing else, versus adding repo identity
(README H1, cleaned) after the manifest step:

| Site | All four fixes applied | With repo identity added |
|---|---|---|
| `graph_websearch_agent/graph.py` | **(nothing)** | Custom WebSearch Agent |
| `gemini-fullstack/graph.py` | Pro Search Agent | Pro Search Agent |
| `company-research-agent/graph.py` | **(nothing)** | Agentic Company Researcher |
| `eaia/cron_graph.py` | Cron | Executive AI Assistant: Cron |
| `eaia/reflection_graphs.py` | General Reflection Graph | Executive AI Assistant: General Reflection |
| `eaia/reflection_graphs.py` | Multi Reflection Graph | Executive AI Assistant: Multi Reflection |
| `eaia/main/graph.py` | **(nothing)** | Executive AI Assistant |
| `fastapi-langgraph-template/graph.py` | **(nothing)** | FastAPI LangGraph Template |
| **Named** | **4 / 8** | **8 / 8** |

The four fixes take the cascade from mostly-wrong to **half the sites unnamed**.
Repo identity closes the other half, and it is the cheapest signal of the set —
one file read, no AST work.

The rule that makes it safe: **count graphs in the repo first.** One graph → repo
identity *is* the name. More than one → it becomes a qualifier prefix and the
manifest key or structural signal supplies the tail.

---

## Recommended order, by measured impact

| # | Change | Sites fixed | Cost |
|---|---|---|---|
| 1 | Repo identity (README H1) + graph-count rule | 4 / 8 | lowest — no AST |
| 2 | Drop the `len(graphs) == 1` guard; match manifest by path + compiled var | 4 / 8 | medium — needs the compile() link and a wrapper hop |
| 3 | Read `compile(name=)` when it is `ast.Constant`; record and fall through when `JoinedStr` | 1 / 8 | low |
| 4 | Replace the state-type filter with strip-then-generic-check, ranked below module path | 2 / 8 | low |
| 5 | Add module stem as a guarded last resort | 1 / 8 net | low |

Items 1 and 2 are worth roughly the same on this corpus and together cover every
site. Item 3 is small by frequency but should still rank *first in the cascade*
when it fires, because it is the only author-declared graph name in the framework
and it beats the manifest where both exist.

## Caveats

Eight graph sites, five repos. The single-graph ratio (4 of 5 repos) drives the
value of repo identity and will not hold on larger codebases, where the qualifier
path — one repo of evidence — becomes the common path. `compile(name=)` has two
occurrences and only one statically resolvable, so its ranking rests on being
correct in principle. The blocklists here are seeded from what these five trees
contain and will need extending.
