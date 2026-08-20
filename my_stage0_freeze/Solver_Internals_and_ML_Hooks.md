# MILP Solver Internals, and Exactly Where Machine Learning Plugs In

> **Audience:** anyone who cannot yet judge which stage of the solver "pruning" and "variable selection" belong to.
> **How to read:** Chapters 1–3 in order, no skipping. Chapter 4 onward is reference material.
> **Companion script:** `看懂求解器.py` — instruments the solver and prints the main loop step by step.

---

## Contents

- [1. Getting the right mental model first](#1-getting-the-right-mental-model-first)
- [2. The three phases](#2-the-three-phases)
- [3. The main loop: what actually happens at one node](#3-the-main-loop-what-actually-happens-at-one-node)
- [4. Every ML intervention point (hook inventory)](#4-every-ml-intervention-point-hook-inventory)
- [5. Why learning variable selection is safe and learning pruning is not](#5-why-learning-variable-selection-is-safe-and-learning-pruning-is-not)
- [6. This project vs. Lee et al. 2020, at the hook level](#6-this-project-vs-lee-et-al-2020-at-the-hook-level)
- [7. Branching rules, from weakest to strongest](#7-branching-rules-from-weakest-to-strongest)
- [8. How to read SCIP's log](#8-how-to-read-scips-log)
- [9. Terminology](#9-terminology)
- [10. Learning order and time budget](#10-learning-order-and-time-budget)

---

## 1. Getting the right mental model first

### 1.1 The fundamental difficulty

Your problem contains **integer variables** (e.g. "deploy a UAV at this site or not" must be 0 or 1).

If every variable could take fractional values, the problem is a **linear program (LP)**, for which mature algorithms exist (simplex, interior point). An LP solves to **provable optimality** in milliseconds to seconds.

> **"Provable optimality"** means two things at once, not one: the method returns a solution *and* a certificate that no better solution exists. Heuristic methods (SCA, BCD, DRL) deliver only the first — they return an answer with no way to tell whether it is 1% or 40% from the optimum. The certificate here is the bound argument of §1.3: once the dual bound and the primal bound coincide, nothing better can exist. **This distinction is the entire basis for using an exact solver as a measuring instrument for heuristic methods.**

**Adding the integrality requirement makes the problem dramatically harder**, because the feasible set is no longer a connected convex region but a scattered set of isolated points — you cannot simply slide downhill along a gradient.

Enumerate instead? With `n` binary variables there are `2^n` combinations. At `n = 60` that is `10^18`; the age of the universe is not enough.

### 1.2 The core idea of branch and bound, in one sentence

> **Do not enumerate solutions. Prove that large regions cannot contain a better solution, then discard those regions wholesale.**

How do you prove it? Via **relaxation**:

1. **Drop** the integrality requirement and solve an ordinary LP.
2. Because the constraints were loosened, the LP optimum is **no worse than** the true optimum *of that node's subregion*.
   → For a maximization problem, the LP value is a **local upper bound**: nothing inside this node's region can exceed it.
3. If that local upper bound is **worse than a feasible solution you already hold** (found elsewhere in the tree), then this region cannot contain anything better → **discard the entire region**.

**This is what "bound" in "branch and bound" refers to.**

> **⚠ Do not confuse three different bounds.** The word "bound" is overloaded, and step 3 above only makes sense once they are kept apart:
>
> | Bound | Scope | Example from a real run |
> |---|---|---|
> | **Local (node) upper bound** | **This node's subregion only** — "nothing under *me* beats this" | 132.0 at the root, 130.5 at node 3, 129.6 at node 5 |
> | **Global dual bound** | The whole problem — the max local bound over all *open* nodes | reported as `dualbound` in the log |
> | **Global primal bound (incumbent)** | The whole problem — the best solution actually in hand | 114, later 124 |
>
> A node with local bound 110 is discarded when the incumbent is already 114: that subregion may contain thousands of combinations, but every one of them has been *proven* no better than 114 — without examining a single one.
>
> The incumbent that enables this was found **elsewhere in the tree**. Branch and bound does not descend in order; it digs in one place, then another. **This is also why step ⑤ (primal heuristics) matters so much: the earlier a strong incumbent appears, the more regions can be discarded.**

### 1.3 Two bounds, two names

| Name | Aliases | What it is | Where it comes from |
|---|---|---|---|
| **Dual bound** | best bound, upper bound (for max) | "How good could this still possibly get" | The relaxation (LP) |
| **Primal bound** | incumbent, lower bound (for max) | "The best solution actually in hand" | A feasible integer solution that was found |

**gap = dual bound − primal bound** (for maximization).

- Initially the gap is large (the dual bound is optimistic; the primal bound may not exist yet).
- Solving = **pushing the dual bound down while pulling the primal bound up**.
- **The instant gap = 0, optimality has been proven.**

> **Note:** this naming does *not* flip between maximization and minimization. Under minimization the dual bound sits below and the primal bound above, but the names are unchanged. **That is precisely why solvers say "primal/dual" instead of "upper/lower".**

---

## 2. The three phases

From reading the model to emitting an answer, SCIP passes through three phases.

```
┌─────────────────────────────────────────────────────────┐
│  Phase A: Preparation (before the search starts)         │
│  ─────────────────────────────────────────────────────  │
│  A1  Read the model → build the internal representation  │
│  A2  Presolve: simplify the model                        │
│        · delete redundant constraints, fix variables     │
│        · aggregate equivalent variables                  │
│        · tighten variable bounds                         │
│        · probing: tentatively set x=0, see what follows  │
│  A3  Produce the TRANSFORMED model                       │
│      ★ note: it is NOT the model you wrote               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Phase B: Solving (the main loop — see Chapter 3)        │
│  ─────────────────────────────────────────────────────  │
│  B0  Process the root node (special: cuts applied hard)  │
│  B1  Loop: select node → propagate → solve LP → cut →    │
│            heuristics → fathom test → branch             │
│  B2  Until the open-node list is empty, or a limit hits  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Phase C: Wrap-up                                        │
│  C1  Map the transformed-model solution back to yours    │
│  C2  Report solution, dual bound, gap, statistics        │
└─────────────────────────────────────────────────────────┘
```

### 2.1 One thing about presolve that will bite you

**Presolve rewrites your model.** Specifically, a variable `x_ul` that you declared may, in the transformed model, be:

- already **fixed** (`SCIP_VARSTATUS_FIXED`),
- **aggregated** into another variable (`AGGREGATED`, e.g. SCIP discovered `x1 = 1 − x2`),
- **multi-aggregated** (`MULTAGGR`, expressed as a linear combination of several variables).

**Consequence:** when the GNN sees a list of branching candidates at a node, those are variables of the **transformed model**, not of your original model. You must be able to map between them.

> This is why **Gate 2 (candidate-mapping correctness)** exists, and why `getStatus()` returning `FIXED / AGGREGATED / MULTAGGR` must be checked.
> **Skip this check and your GNN will score the wrong objects — silently, with no error.**

### 2.2 SCIP stages

```python
model.getStage()
```

Key values: `PROBLEM` → `TRANSFORMED` → `PRESOLVING` → `PRESOLVED` → `SOLVING` → `SOLVED`.

**Why you need this:** many APIs are only valid in specific stages. `getLPBranchCands()` is only meaningful during `SOLVING`, at a node whose LP has been solved. **Call it in the wrong stage and SCIP returns garbage or crashes.**

---

## 3. The main loop: what actually happens at one node

This chapter is the core of the document. The commonly-taught "four steps" version is a simplification; the real loop has **seven**.

```
      ┌────────────────────────────────────────────┐
      │  Is the open-node list non-empty?          │
      └───────────────┬────────────────────────────┘
                      │ yes
                      ▼
  ①  ┌──────────────────────────────────────────────────┐
      │ NODE SELECTION                                   │
      │ Pick one node from the open list.                │
      │ Default: a hybrid of depth-first and best-first.  │
      │ 【hook: Nodesel】                                 │
      └───────────────┬──────────────────────────────────┘
                      ▼
  ②  ┌──────────────────────────────────────────────────┐
      │ DOMAIN PROPAGATION                               │
      │ No LP — pure logical inference tightening bounds.│
      │ e.g. x1=1 and x1+x2≤1  ⟹  deduce x2=0            │
      │ Cheap, often free progress, can prove infeasible.│
      │ 【hook: Prop】                                    │
      └───────────────┬──────────────────────────────────┘
                      ▼
  ③  ┌──────────────────────────────────────────────────┐
      │ LP RELAXATION SOLVE                              │
      │ Drop integrality, solve a linear program.        │
      │ Yields: this node's dual bound + a (usually      │
      │ fractional) solution.                            │
      │ 【hook: Relax (rare)】                            │
      └───────────────┬──────────────────────────────────┘
                      ▼
  ④  ┌──────────────────────────────────────────────────┐
      │ SEPARATION LOOP  ★ iterates several times        │
      │ Find inequalities satisfied by every integer     │
      │ solution but violated by the current fractional  │
      │ one. Add them → LP tightens → re-solve → repeat. │
      │ Goal: push the bound down WITHOUT branching.     │
      │ 【hooks: Sepa (generate cuts), Cutsel (pick)】    │
      └───────────────┬──────────────────────────────────┘
                      │  (loops back to ③ until no new
                      │   cuts, or returns diminish)
                      ▼
  ⑤  ┌──────────────────────────────────────────────────┐
      │ PRIMAL HEURISTICS                                │
      │ Quickly construct a feasible integer solution to │
      │ push the primal bound up.                        │
      │ e.g. round the fractional solution and repair;   │
      │ local search; large-neighbourhood search.        │
      │ Better incumbent ⟹ smaller gap ⟹ more pruning.   │
      │ 【hook: Heur】                                    │
      └───────────────┬──────────────────────────────────┘
                      ▼
  ⑥  ┌──────────────────────────────────────────────────┐
      │ FATHOMING / BOUNDING TEST                        │
      │ Three ways to close a node without expanding it: │
      │   (a) LP infeasible      → region has no solution│
      │   (b) LP solution integral → new incumbent       │
      │   (c) LP bound ≤ incumbent → cannot be better    │
      │ ★ all three are PROVABLE, none is a guess        │
      │ 【SCIP exposes NO hook here — see Chapter 5】     │
      └───────────────┬──────────────────────────────────┘
                      │ none of the three ⟹ must branch
                      ▼
  ⑦  ┌──────────────────────────────────────────────────┐
      │ BRANCHING = VARIABLE SELECTION                   │
      │ Pick one integer variable x taking a fractional  │
      │ value v. Split into two children:                │
      │      x ≤ ⌊v⌋   and   x ≥ ⌈v⌉                     │
      │ (for binaries: x = 0 and x = 1)                  │
      │ Push both children onto the open list.           │
      │ 【hook: Branchrule】★ this is what you replace   │
      └───────────────┬──────────────────────────────────┘
                      │
                      └──────► back to ①
```

### 3.1 A worked example

Let `x1, x2, x3 ∈ {0,1}`, maximize `5x1 + 4x2 + 3x3` subject to `2x1 + 3x2 + x3 ≤ 4` and `x1 + x2 ≤ 1`.

| Step | What happens |
|---|---|
| ① | Only the root node is open; select it |
| ② | Propagation: nothing deducible yet |
| ③ | Solve LP (fractional allowed) → say `x1=1, x2=0.33, x3=1`, objective `9.33` |
| ④ | Separation: perhaps a cut can remove that fractional `x2` |
| ⑤ | Heuristic: round `x2` down to 0, check feasibility → feasible solution with objective `8`. **Primal bound = 8** |
| ⑥ | Test: LP value `9.33` > incumbent `8`, and the solution is not integral → **cannot close** |
| ⑦ | Branch: `x2 = 0.33` is fractional → split into `x2 = 0` and `x2 = 1` |

The loop restarts at ① with one of the two new nodes.

**gap here = 9.33 − 8 = 1.33.** As the tree grows, the left side descends and the right side rises; **when they meet, optimality is proven.**

### 3.2 The key realization

**Step ⑦ is the thing you do only when nothing else worked.**

Steps ②③④⑤⑥ are all attempts to *resolve the node without branching*. Branching happens only when propagation cannot tighten, cuts cannot separate, heuristics cannot construct, and the bound cannot prune.

**Therefore: the number of branchings = the number of times every cheaper mechanism failed.** Tree size is a direct measure of how hard the model is to *prove*.

**This also explains why tightening big-M shrinks measured headroom.** A tighter formulation gives a better bound at ③, which prunes more at ⑥, which invokes ⑦ less often. The tree is already small — so there is less room for a smarter branching rule to improve on it.

---

## 4. Every ML intervention point (hook inventory)

SCIP has a plugin architecture. **Each plugin type is a position where ML can intervene.**

| # | Step | SCIP plugin | PySCIPOpt base class | What ML decides | **Can it break optimality?** | Literature |
|---|---|---|---|---|---|---|
| ① | Node selection | `nodesel` | `Nodesel` | Which node to process next | ❌ No (order only) | Medium |
| ② | Domain propagation | `prop` | `Propagator` | How aggressively to propagate | ❌ No (inference is provable) | Low |
| ③ | Relaxation | `relax` | `Relax` | Which relaxation to use | ⚠️ Relaxation must be valid | Low |
| ④a | Cut generation | `sepa` | `Sepa` | Which cuts to generate | ⚠️ Cuts must be valid | Medium |
| ④b | Cut selection | `cutsel` | `Cutsel` | Which generated cuts to add | ❌ No (all are valid cuts) | **Rising** |
| ⑤ | Primal heuristics | `heur` | `Heur` | How to construct feasible solutions | ❌ No (solutions are checked) | **High** |
| ⑥ | **Fathoming** | **no such plugin** | — | — | — | — |
| ⑦ | **Variable selection** | `branchrule` | **`Branchrule`** | **Which variable to branch on** | **❌ No** | **Highest** |
| — | Pricing (column generation) | `pricer` | `Pricer` | Which columns to add | ⚠️ | Low |
| — | Configuration | (external) | — | Which parameter set to use | ❌ | Medium |

### 4.1 Note row ⑥: SCIP exposes no pruning hook

**This is a design decision, not an oversight.**

The three fathoming conditions (infeasible / integral / bound-dominated) are all **provable**. The architecture does not let you insert "I think this node is hopeless, discard it", because that would directly destroy the optimality guarantee.

**Lee et al. (2020) wanted to learn pruning, so they could not use SCIP. They wrote their own B&B in Python + MATLAB.**

> **This is the important point: the plugin architecture itself encodes the safety boundary.** Whatever you do at SCIP's legal hooks, you cannot lose the optimum. To lose it, you must first leave SCIP.

### 4.2 Code shapes

```python
# ⑦ Variable selection — what this project does
from pyscipopt import Branchrule, SCIP_RESULT

class GNNBranching(Branchrule):
    def branchexeclp(self, allowaddcons):
        cands, sols, fracs, ncands, nprio, nimpl = self.model.getLPBranchCands()
        # ... GNN scores cands[:nprio] ...
        chosen = cands[argmax_index]
        self.model.branchVar(chosen)
        return {"result": SCIP_RESULT.BRANCHED}

model.includeBranchrule(GNNBranching(), "gnn", "GNN branching",
                        priority=536870911, maxdepth=-1, maxbounddist=1.0)
```

```python
# ① Node selection
from pyscipopt import Nodesel

class MyNodesel(Nodesel):
    def nodeselect(self):
        return {"selnode": self.model.getBestNode()}
    def nodecomp(self, node1, node2):
        return -1     # node1 has higher priority
```

```python
# ⑤ Primal heuristic
from pyscipopt import Heur, SCIP_RESULT

class MyHeur(Heur):
    def heurexec(self, heurtiming, nodeinfeasible):
        sol = self.model.createSol(self)
        # ... assign values to variables ...
        accepted = self.model.trySol(sol)
        return {"result": SCIP_RESULT.FOUNDSOL if accepted
                          else SCIP_RESULT.DIDNOTFIND}
```

### 4.3 How priority works

`priority = 536870911` is `2^29 − 1`, SCIP's maximum. Setting it this high guarantees **your rule is consulted before any built-in rule**.

If your rule returns `DIDNOTRUN`, **SCIP automatically falls through to the next-highest-priority rule.** This is the mechanism behind the claim "any failure falls back to the default rule" — it is not a wrapper you write, it is built into the plugin dispatch.

---

## 5. Why learning variable selection is safe and learning pruning is not

### 5.1 In one sentence

> **Step ⑥ decides *whether to keep*. Step ⑦ decides *in what order*.**

### 5.2 Expanded

**⑦ Variable selection:**

- Branch on `x1` → two children: `x1 = 0` and `x1 = 1`.
- Branch on `x2` → two children: `x2 = 0` and `x2 = 1`.
- **Either way, the two children together still cover the entire feasible region. Nothing is lost.**
- Choose well → the bound tightens fast → small tree.
- Choose badly → the bound tightens slowly → large tree, **but the final answer is identical**.

**Variable selection affects efficiency only, never correctness. This is a mathematical fact, not an empirical observation.**

**⑥ Fathoming:**

- You declare "discard this node."
- If the optimum happened to live in that subtree, **the optimum is now unreachable**.
- And **you will not know**: the solver still returns an answer, it just is not optimal.

Lee et al. (2020) state this explicitly:

> *"If an optimal node is misclassified as non-optimal and is pruned, the optimal solution cannot be found either."*

Their reported optimality gap of **2.01% – 14.54%** is exactly this effect.

### 5.3 How to phrase it in the paper

> *The learned policy scores only the solver's legal branching candidates at each node. Since branching partitions the feasible region exhaustively regardless of which variable is selected, the feasible region and all optimality certificates are preserved **by construction**; the policy can affect search efficiency but not correctness.*

**The phrase "by construction" carries weight** — it signals that this is a logical property, not an experimental finding, so a reviewer cannot demand an experiment to establish it.

---

## 6. This project vs. Lee et al. 2020, at the hook level

```
                    Main loop
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
    ▼                   ▼                   ▼
 ① Node sel.        ⑥ Fathoming        ⑦ Variable sel.
    │                   │                   │
    │            ┌──────┴──────┐            │
    │            │ Lee et al.  │            │  ┌────────────────┐
    │            │    2020     │            └──│ This project   │
    │            └─────────────┘               │ & Gasse 2019   │
    │              ⚠ loses optimality          └────────────────┘
    │              requires custom B&B           ✅ optimality safe
    │                                             SCIP plugin suffices
```

| | Lee et al. 2020 | This project |
|---|---|---|
| Hook | ⑥ Fathoming (no SCIP hook exists) | ⑦ Variable selection (`Branchrule`) |
| Therefore, solver | **must write own B&B** | **can use SCIP** |
| Their variable selection | "first undetermined variable" — the crudest possible | **this is the object being optimized** |
| Their presolve / cuts / heuristics | essentially none | full SCIP stack |
| Optimality | lost; Ogap 2.01% – 14.54% | preserved by construction |
| Reported speedup | 2.06× – 22.13× | to be measured, **expect far lower** |
| Instance size | K=5,L=2 up to K=10,L=2 (~10–20 binaries) | 60–150 users |

### 6.1 The speedup-number trap

**Their 22× is relative to an essentially unoptimized hand-written B&B.**
**Your speedup will be relative to SCIP's default (reliability pseudocost + presolve + cuts + heuristics, decades of tuning).**

**These two numbers are not comparable — and a reviewer who does not notice this will conclude your work is weaker than a 2020 paper.**

**Required mitigation experiment:** run "naive B&B (DFS + first-fractional variable + all presolve/cuts/heuristics off)" against "SCIP default" and quantify how much SCIP's default alone wins by. **Include this in the paper so readers know the two speedups were measured against different yardsticks.**

Simulating a naive B&B inside SCIP:

```python
m.setPresolve(SCIP_PARAMSETTING.OFF)
m.setSeparating(SCIP_PARAMSETTING.OFF)
m.setHeuristics(SCIP_PARAMSETTING.OFF)
m.setParam("branching/random/priority", 536870911)     # or a custom "first fractional"
m.setParam("nodeselection/dfs/stdpriority", 536870911)
```

---

## 7. Branching rules, from weakest to strongest

| Rule | How it picks | Cost per node | Tree size |
|---|---|---|---|
| **Most infeasible** | The variable whose fractional part is closest to 0.5 | ~0 | Poor (often worse than random) |
| **Random / first fractional** | Literally that (Lee et al. use this) | 0 | Very poor |
| **Pseudocost** | Uses history: how much did branching on this variable improve the bound in the past | Very low | Good |
| **Strong branching** | **Actually tries each candidate** (two LP solves each) and picks the one that tightens the bound most | **Very high** | **Best** |
| **Full strong branching (FSB)** | Strong branching over *all* candidates, none skipped | Highest | **Best — this is the ceiling** |
| **Reliability pseudocost (RPB)** ← **SCIP default** | Hybrid: use pseudocost when its history is statistically reliable; otherwise run a few strong-branching probes to build history | Medium | Very good |

### 7.1 The intuition behind pseudocost

*"Last time I branched on `x7`, the down-child improved the bound by 0.8 and the up-child by 1.2. So `x7` is probably a useful variable."*

**Problem:** a fresh variable has no history, so the estimate is unreliable. **That is what "reliability" means** — SCIP counts how often each variable has been branched on and runs strong-branching probes to fill the gap when the count is too low.

### 7.2 The strong branching score

For candidate `x` at a node with LP objective `z`:

```
Try down: fix x ≤ ⌊v⌋, solve LP  →  z_down
Try up:   fix x ≥ ⌈v⌉, solve LP  →  z_up

gain_down = z_down − z        (SCIP minimizes internally — mind the direction)
gain_up   = z_up   − z

score = max(gain_down, ε) × max(gain_up, ε)        ← product score
```

**Why a product rather than a sum:** the product favours variables that help **on both sides**. A variable that tightens a lot going down but does nothing going up produces a badly unbalanced tree; the product penalizes that automatically.

### 7.3 What the GNN actually learns

**Input:** the node's state encoded as a **bipartite graph**
- One side: variable nodes (features: type, objective coefficient, current LP value, fractionality, bounds, …)
- Other side: constraint nodes (features: type, right-hand side, slack, …)
- Edges: "this variable appears in this constraint", with the coefficient as an edge feature

**Output:** one score per candidate variable

**Labels:** the FSB product scores (or their ranking)

**Loss:** make the GNN's argmax agree with FSB's argmax (cross-entropy or a ranking loss)

**In one sentence: the GNN learns to guess what strong branching would have chosen, without paying for the trial LPs.**

---

## 8. How to read SCIP's log

Enable output:

```python
model.hideOutput(False)      # or simply never call hideOutput()
```

Header (most important columns only):

```
 time | node  | left  |LP iter|LP it/n| mdpt |frac |vars |cons |rows |cuts |  dualbound   | primalbound |  gap
```

| Column | Meaning | What to watch |
|---|---|---|
| `time` | Elapsed seconds | |
| `node` | **Nodes processed** | **This is the quantity Gate 3 compares** |
| `left` | **Nodes still open** | Monotonically rising = the tree is exploding |
| `LP iter` | Cumulative simplex iterations | |
| `mdpt` | Current maximum depth | Very deep = diving down a rabbit hole |
| `frac` | Fractional variables at the current node | This is the branching-candidate count |
| `cuts` | Cuts added so far | |
| `dualbound` | **Dual bound** | The line coming down |
| `primalbound` | **Primal bound / incumbent** | The line going up |
| `gap` | Difference between them | **Reaching 0 = optimality proven** |

The leading character of a line indicates what triggered it: `*` = a new incumbent was found; `R`, `s`, `f`, etc. identify which heuristic produced it.

**Exercise:** run a moderately hard instance, save the log, and walk through it column by column. **Reading the log fluently *is* understanding what the solver is doing.**

---

## 9. Terminology

| Term | Chinese | One-line definition |
|---|---|---|
| Branch and Bound (B&B) | 分支定界 | The core algorithmic framework |
| Branch and Cut | 分支切割 | B&B plus cutting planes — what modern solvers actually run |
| **Node** | 节点 | A subproblem in the tree (= the residual problem after fixing some variables) |
| **Open nodes / node list** | 待办清单 | Nodes created but not yet processed |
| **LP relaxation** | 线性松弛 | The problem with integrality dropped |
| **Dual bound / best bound** | 对偶界 | "How good it could still get", from the relaxation |
| **Primal bound / incumbent** | 原始界 | "The best solution actually in hand" |
| **Gap** | 间隙 | Difference between the bounds; 0 = optimality proven |
| **Fathom / prune** | 结案 / 剪枝 | Closing a node without expanding it |
| **Branching variable selection** | 变量选择 | Which variable to split on (**this project**) |
| **Node selection** | 节点选择 | Which node to process next |
| **Domain propagation** | 域传播 | Tightening bounds by pure logical inference |
| **Cutting plane / cut** | 割平面 | An inequality that cuts off the fractional point but no integer point |
| **Separation** | 分离 | The process of generating cuts |
| **Valid inequality** | 有效不等式 | An inequality satisfied by every integer feasible solution |
| **Primal heuristic** | 原始启发式 | A fast method for constructing feasible solutions |
| **Presolve** | 预处理 | Simplifying the model before the search |
| **Aggregation** | 变量合并 | Presolve merging two variables into one |
| **Pseudocost** | 伪代价 | Estimating branching payoff from historical data |
| **Strong branching** | 强分支 | Actually trying each candidate before deciding |
| **Full strong branching (FSB)** | 完全强分支 | Strong branching over all candidates — most accurate, slowest |
| **Reliability pseudocost (RPB)** | 可靠性伪代价 | SCIP's default; pseudocost + strong-branching top-ups |
| **Plugin / callback** | 插件 / 回调 | A position where user code can intervene |
| **Integer hull** | 整数包 | The convex hull of all integer feasible solutions |
| **Big-M** | 大 M | The trick for writing if-then logic as a linear inequality |

---

## 10. Learning order and time budget

| Layer | Content | Time | How to verify you learned it |
|---|---|---|---|
| **1** | Chapters 1–3: the seven-step loop | ½ day | Recite the seven steps without notes |
| **2** | **Run `看懂求解器.py`, change parameters, re-run** | **1 day** | **Explain why disabling cuts changes the node count** |
| **3** | Read a full log, column by column | ½ day | Point at `left` and say whether the tree is exploding |
| **4** | Chapter 7: the branching-rule spectrum | 1 day | Explain why RPB is a hybrid |
| **5** | Write a `Branchrule` implementing "most fractional" | 1 day | It runs, and the node count is worse than default |
| **6** | Reproduce FSB scores via `getVarStrongbranch` | 2 days | Scores are non-zero and correctly ordered (mind the sign!) |
| **7** | Presolve / cuts / heuristics | as needed | Know they exist, know how to disable them |

**Roughly one week.** After that week your understanding of the solver will exceed that of most people who use it — because most people treat it as a black box behind an API.

### 10.1 Three known traps (all found empirically, not theoretically)

1. **The strong-branching gain is `down − lpobj`, not `lpobj − down`.** SCIP minimizes internally even when you wrote `maximize`. Getting the sign wrong makes **every score zero, with no error raised** — silently producing a batch of useless labels.
2. **The method is `v.getStatus()`, not `v.getVarStatus()`.** Getting it wrong emits a cascade of `[branch.c:1625] ERROR` lines followed by `SCIP: unspecified error!`, which reveals nothing about the real cause.
3. **Take only the first `nprio` candidates** (`npriolpcands`), not all `ncands`.

---

## Appendix: the companion script

`看懂求解器.py` installs a "narrator" branching rule. Every time SCIP reaches step ⑦ it prints the current state of ①–⑦, then returns `DIDNOTRUN` to hand the decision back to the default rule — it observes without intervening.

**Suggested modifications:**

1. Re-enable `setSeparating` → watch the node count change
2. Re-enable `setHeuristics` → watch when the primal bound first appears
3. Re-enable `setPresolve` → watch the variable count change (this is §2.1 in practice)
4. Add `m.setParam("branching/fullstrong/priority", 536870911)` → measure the node-count reduction. **This is Gate 3.**
5. Change the item count from 12 to 40 → watch the tree explode
