# LangGraph agent naming — four strategies, a quality gate, and a cascade

Designed against the three repos named in the request, then validated on a
fourth held-out repo (`langchain-ai/executive-ai-assistant`) whose node sites
use the opposite idiom. All numbers below come from an AST scan of the real
trees — 40 node sites, 4 repos.

The unit being named is the **node**: LangGraph has no `Agent` constructor, and
the survey found 100% raw-`StateGraph` construction with zero
`langgraph.prebuilt.create_react_agent`. `add_node` is where an addressable
component appears.

---

## Why one signal is never enough

Signal availability across all 40 node sites:

| Signal | Present | Notes |
|---|---|---|
| explicit `add_node("name", …)` string | 24 / 40 (60%) | absent entirely in the one-arg idiom |
| callable identifier | 31 / 40 (78%) | but 11 of those are generic |
| callable identifier, non-generic | 20 / 40 (50%) | |
| class constructed in the node body | 25 / 40 (63%) | |
| docstring on the node function | 14 / 40 (35%) | |
| import module path | 8 / 40 (20%) | |

The decisive fact is not coverage but **collapse** — each signal degenerates to
one value in at least one repo:

| Repo | explicit | callable | docstring | class in body |
|---|---|---|---|---|
| graph_websearch_agent | 9/9, 9 distinct | 0/9 | 0/9 | 7/9, 7 distinct |
| gemini-fullstack | 4/4, 4 distinct | 4/4, 4 distinct | 4/4, 4 distinct | 3/4, 2 distinct |
| company-research-agent | 10/10, 10 distinct | 10/10, **1 distinct** | 10/10, **1 distinct** | 10/10, 10 distinct |
| executive-ai-assistant | **1/17** | 17/17, 17 distinct | 0/17 | 5/17, 4 distinct |

Two cells explain the "everything is called `agent`" problem:

- **`company-research-agent`**: all ten nodes are `self.<x>.run`, so the callable
  name is `run` ten times, and every docstring is *"Execute the research
  workflow"* ten times. Naming from either signal yields ten identical names.
- **`executive-ai-assistant`**: 16 of 17 nodes use `add_node(callable)` with no
  string at all, so anything keyed on the declared name yields nothing.

No strategy that reads a single signal survives both repos. That is the whole
argument for a cascade with a gate.

---

## Strategy 1 — Declared node identity

**Algorithm.** Take the first positional argument of `add_node` when it is a
string constant. Split on `_`/camelCase, title-case, preserve acronyms.

**Signals.** `add_node("<name>", target)`.

**Strengths.** It is the author's own label for the component, and it is the name
that appears in LangGraph traces, checkpoints and the studio UI — so it matches
what a consumer already sees elsewhere. Unique within a graph by construction
(LangGraph rejects duplicate node names at runtime). Highest precision of any
signal: 23/23 distinct where present in the three design repos.

**Weaknesses.** Absent in 40% of sites corpus-wide and 94% in the held-out repo.
Sometimes terser than the implementation warrants (`grounding` where the class is
`GroundingNode`), and occasionally *disagrees* with the implementation —
`industry_analyst` vs class `IndustryAnalyzer`. Names a graph position, which is
not always a semantic role (`end`, `serper_tool`).

**Examples.**

| Input | Output |
|---|---|
| `graph.add_node("planner", lambda …)` | `Planner` |
| `self.workflow.add_node("financial_analyst", self.financial_analyst.run)` | `Financial Analyst` |
| `builder.add_node("generate_query", generate_query)` | `Generate Query` |
| `graph_builder.add_node(human_node)` | *(no output — no string)* |

---

## Strategy 2 — Implementation identity

**Algorithm.** In priority order: (a) the first non-infrastructure class
constructed in the node body or lambda; (b) the callable's own identifier, if it
is not in the generic blocklist. Strip a trailing `_node`/`_agent`/`_tool`
suffix **only when stripping does not collide with a sibling node**.

**Signals.** Class constructors inside the node body; the `add_node` target
identifier; `self.<x> = SomeClass()` assignments for dotted targets.

**Strengths.** The only strategy that works on the one-arg idiom (16/17 in the
held-out repo). Class names are the most *descriptive* signal in the corpus —
`PlannerAgent`, `NewsScanner`, `IndustryAnalyzer` — because a class name is
chosen to describe a thing, whereas a method name describes an action. Recovers
a real name where the declared one is missing.

**Weaknesses.** Needs an infrastructure blocklist or it names the LLM client
instead of the agent — without one, two `executive-ai-assistant` nodes came out
as `Chat Open AI`. Collapses entirely when the target is a shared method
(`run` ×10). Suffix stripping is dangerous: `send_cal_invite_node` and
`send_cal_invite` are two different nodes in the same graph that both strip to
`Send Cal Invite`.

**Examples.**

| Input | Output |
|---|---|
| `lambda state: PlannerAgent(state=…).invoke(…)` | `Planner` |
| `self.workflow.add_node("news_scanner", self.news_scanner.run)` → `self.news_scanner = NewsScanner()` | `News Scanner` |
| `graph_builder.add_node(triage_input)` | `Triage Input` |
| `graph_builder.add_node(main)` | *(rejected — generic)* |
| `general_reflection_graph.add_node(update_general)` (body builds `ChatOpenAI`) | `Update General` *(client suppressed)* |

---

## Strategy 3 — Documentary / semantic

**Algorithm.** Take the node function's docstring, strip boilerplate prefixes
(`LangGraph node that …`, `This node …`), keep the first clause, cap at ~5 words.

**Signals.** Docstrings on node functions, including across a module boundary;
system-prompt constants near the node.

**Strengths.** The only strategy producing genuinely *purpose*-shaped text rather
than an identifier — `Identifies Knowledge Gaps And Generates` says more about
what the node does than `Reflection` does. Useful as a **description** field even
when it is not used as the name.

**Weaknesses.** The weakest signal in this corpus and the most dangerous.
Present on only 35% of sites. It collapses in `company-research-agent` (ten
identical docstrings). And in `executive-ai-assistant` it is actively **wrong**:
`find_meeting_time` carries the docstring *"Write an email to a customer."*,
copy-pasted from `draft_response`. A naming system that trusted docstrings would
confidently emit a wrong name. Also produces long, sentence-shaped names that
read badly as identifiers.

**Recommendation: use it for `description`, not for `name`** — and never without
the duplicate check below.

**Examples.**

| Input | Output |
|---|---|
| `"""LangGraph node that generates search queries…"""` | `Generates Search Queries` |
| `"""Execute the research workflow"""` (×10) | *(rejected — collapses)* |
| `"""Write an email to a customer."""` on `find_meeting_time` | *(wrong — would need the gate to catch it; it does not)* |

---

## Strategy 4 — Structural / contextual composition

**Algorithm.** Compose from location: the defining module's basename, or the
imported module's last segment, or the containing package — skipping
non-semantic path parts (`src`, `backend`, `app`) and non-semantic filenames
(`graph`, `main`). Append a positional disambiguator only if still colliding.

**Signals.** File path, package name, import source module, builder variable
name, graph entry/finish points.

**Strengths.** Always produces something — it is the only strategy that cannot
return nothing, which is what makes it a viable terminal fallback. Import paths
are surprisingly good in the held-out repo: `eaia.main.find_meeting_time`,
`eaia.main.triage`. Guarantees termination of the cascade.

**Weaknesses.** Lowest information content. Degenerates to the repo or graph name
when files are called `graph.py`/`main.py`, which is common — it produced
`Agent Graph` for all nine `graph_websearch_agent` nodes as a candidate. Cannot
distinguish sibling nodes in the same file, so it needs the disambiguator, and a
name with a line number in it is a signal of failure, not a good name.

**Examples.**

| Input | Output |
|---|---|
| `eaia/cron_graph.py`, target `main` | `Cron Graph` |
| target imported `from eaia.main.triage` | `Triage` |
| `backend/graph.py` in `company-research-agent` | `Graph` *(rejected — generic)* |

---

## The quality gate — what "confirm the name is good" means

Applied to each candidate before accepting it. A candidate failing any check
falls through to the next strategy.

1. **Non-empty**, ≥3 characters after normalisation.
2. **Not in the generic blocklist** — `run`, `main`, `agent`, `node`, `call`,
   `execute`, `invoke`, `process`, `handler`, `step`, `start`, `end`, `graph`,
   `workflow`, `chain`, `app`, `fn`, `wrapper`.
3. **Not an infrastructure class** — `ChatOpenAI`, `ChatAnthropic`,
   `ChatGoogleGenerativeAI`, `AzureChatOpenAI`, `LLM`, `AIMessage`,
   `ToolMessage`, `Send`, `Command`, `RunnableConfig`, `BaseModel`, …
4. **Unique within the graph**, not globally. This scoping matters: two different
   repos legitimately both have a `Reflection` node, and a global uniqueness
   check falsely rejected the good `Reflection` name and forced an ugly
   docstring-derived one. **Scope collision detection to the graph.**
5. **Does not collapse** — if this strategy would emit the same name for more
   than one node *in the same graph*, reject it for all of them. This is the
   check that catches `run` ×10 and `Execute The Research Workflow` ×10.
6. **Suffix-strip safety** — never strip `_node`/`_agent` if a sibling node
   would collide as a result.

---

## The cascade, and what it actually produces

`S1 → S2 → S3 → S4 → S4 + positional disambiguator`, each gated.

Run over all 40 real sites:

| Source | Nodes | Share |
|---|---|---|
| S1 declared node id | 23 | 57.5% |
| S2 implementation identity | 16 | 40.0% |
| S3 docstring | 0 | 0% |
| S4 module/package context | 1 | 2.5% |
| S4 + disambiguator | 0 | 0% |

- **40 / 40 named**, no failures.
- **Zero generic names** in the output.
- **100% unique within each graph** (6 graphs, checked individually).
- Only one node — `eaia/cron_graph.py:51`, whose target is literally `main` —
  falls all the way to context, yielding `Cron Graph`. That is the honest answer
  for a node named `main`.

Selected outputs, showing where each strategy earns its place:

| Site | Naive (callable) | Cascade | Source |
|---|---|---|---|
| `company-research/graph.py:60` | `Run` | `Financial Analyst` | S1 |
| `company-research/graph.py:65` | `Run` | `Curator` | S1 |
| `graph_websearch/graph.py:166` | *(lambda — none)* | `End Node` | S2 (class `EndNodeAgent`) |
| `executive-ai/graph.py:164` | `Triage Input` | `Triage Input` | S2 |
| `executive-ai/graph.py:180` | `Find Meeting Time` | `Find Meeting Time` | S2 |
| `executive-ai/reflection_graphs.py:98` | `Update General` | `Update General` | S2, `ChatOpenAI` suppressed |
| `executive-ai/cron_graph.py:51` | `Main` | `Cron Graph` | S4 |

---

## Three failure modes worth knowing before you build this

Each was produced by a first draft of the cascade and fixed:

1. **Global uniqueness is the wrong scope.** Checking names across the whole
   corpus rejected `Reflection` in `gemini-fullstack` because
   `executive-ai-assistant` also had one, and pushed it down to the docstring
   strategy, producing `Identifies Knowledge Gaps And Generates`. Scope to the
   graph.
2. **Without an infra blocklist, S2 names the model client.** Two nodes came out
   as `Chat Open AI` because `ChatOpenAI(...)` was the first constructor in the
   body. The agent is never the LLM client.
3. **Suffix stripping creates collisions.** `send_cal_invite_node` and
   `send_cal_invite` are distinct nodes in one graph; stripping `_node` merged
   them. Strip only when it is collision-free.

And one the gate does **not** catch: `find_meeting_time` carries a docstring
copy-pasted from another node (*"Write an email to a customer."*). Nothing
static can detect a plausible-but-wrong docstring. This is the strongest reason
to keep S3 out of the name path and confine it to `description`.

---

## Recommendation

- **Name** = cascade S1 → S2 → S4, gated. S3 excluded from the name path.
- **Description** = S3 when available, clearly marked as author-supplied text.
- **Emit provenance** — record which strategy produced each name
  (`name_source: declared_node_id | class_in_body | callable | module_context`)
  so consumers can tell a high-confidence name from a fallback, and so a
  regression in one strategy is visible.
- **Emit a confidence signal** rather than hiding the fallback: a name sourced
  from S4, or one carrying a positional disambiguator, should be surfaceable as
  low-confidence for review.

## Caveats

Four repos, 40 nodes, one framework. The `run` ×10 collapse and the one-arg
idiom are each a single repo's convention, so the *ordering* S1 → S2 is well
supported but the *rates* are not stable. The blocklists are seeded from what
appears in these four trees and will need extending. And this names nodes, not
the assets inside them — the survey found 67.5% of node bodies are not even
inspectable from the graph file, so a node's name is not the same thing as
knowing what model or tools it uses.
