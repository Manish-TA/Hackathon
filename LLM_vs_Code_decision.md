# LLM vs Code Decision Audit

## Current state: ~70% LLM-driven, ~30% code-driven

The LLM picks the action most of the time, but three code-driven overrides are still active.

---

## What the LLM controls

Steps 1→2 in `_parse_planning_response`:

1. The LLM outputs `next_action`, `target_agent`, `plan`, `reasoning`, `confidence`.
2. If `next_action` is valid (in available_actions, not repeated, not failed, not obs, not phase-violating) → it is used **as-is**. `llm_decided=True`.
3. If `next_action` fails validation but `plan[]` contains a valid action → that's used. Still `llm_decided=True`.

The LLM also controls:
- Root cause analysis (observability prompt)
- Plan generation and updates
- Confidence reporting
- Reasoning and analysis

---

## Where code takes over (3 overrides)

### Override 1: Safety fallback (line ~501–512 in inference.py)

**When it fires:** LLM returns invalid JSON, or every action it suggested fails validation.

**What it does:** Picks the first available action by linearly iterating the list — **no intelligence**, just takes whatever comes first.

**Label:** `safety_fallback_invalid_llm`

**Problem:** No re-prompting. The LLM doesn't get a second chance. A dumb linear pick replaces what should be an LLM decision.

---

### Override 2: Supervisor veto (line ~598–606 in inference.py)

**When it fires:** LLM's chosen action has `penalty ≤ -0.3` AND the action's condition is not met in current state.

**What it does:** Calls `_state_aware_select` — the old **code-driven scoring heuristic** — to pick a replacement action. The LLM is not consulted for the replacement.

**Problem:** The replacement action is chosen by a scoring function (`_state_aware_select`) that ranks actions by expected reward, condition-met bonus, investigation bonus, failed penalty, conflict penalty. This is rule-based optimization, not LLM reasoning.

---

### Override 3: StrategyTracker phase gating (line ~467–472 in inference.py)

**When it fires:** `investigation_count >= 3` OR `confidence >= 0.6` OR `root_cause_locked = True`.

**What it does:** Removes all investigate/check/diagnose actions from the available-actions list **before the LLM even sees them**. The LLM cannot choose to investigate even if it has a good reason.

**Problem:** The investigate→execute phase transition is decided by code thresholds (`CONFIDENCE_THRESHOLD=0.6`, `INVESTIGATION_LIMIT=3`), not by the LLM. The LLM reports confidence, but the **code** decides when to flip the phase. The LLM is stripped of agency over this strategic decision.

---

## Summary table

| Component | Who decides | Method |
|---|---|---|
| Root cause analysis | LLM | Observability prompt |
| Plan generation | LLM | Planning prompt |
| Next action (happy path) | LLM | `next_action` from JSON |
| Confidence reporting | LLM | `confidence` field in JSON |
| Phase transition (investigate→execute) | **Code** | `StrategyTracker` thresholds |
| Supervisor veto replacement | **Code** | `_state_aware_select` scoring |
| Invalid output fallback | **Code** | Linear iteration of available actions |
| Plan stability (when to revise) | **Code** | `should_revise_plan` checks stagnation/failure |

---

## Fixes needed to make it truly LLM-driven

### Fix 1: Remove StrategyTracker phase gating from available-actions filter

**Current:** Code removes investigate actions from the list before the LLM sees them.

**Target:** Keep all actions visible to the LLM. Put the phase/confidence info in the prompt and let the LLM decide whether to investigate or execute. Keep StrategyTracker for logging/observability only, not for filtering.

### Fix 2: On supervisor veto, re-prompt the LLM

**Current:** `_state_aware_select` picks the replacement action (code-driven scoring).

**Target:** Re-prompt the LLM with: "Your action {X} was vetoed because {reason}. Pick another action from: {remaining_actions}." Let the LLM choose the alternative.

### Fix 3: On fallback (invalid LLM output), re-prompt once

**Current:** Linear iteration picks the first available action.

**Target:** Re-prompt the LLM with: "Your output was invalid because {reason}. Available actions are: {list}. Return valid JSON." Give the LLM one retry before falling back to linear pick.

---

## After these 3 fixes

| Component | Who decides |
|---|---|
| Root cause analysis | LLM |
| Plan generation | LLM |
| Next action (happy path) | LLM |
| Confidence reporting | LLM |
| Phase transition | **LLM** (was code) |
| Supervisor veto replacement | **LLM** (was code) |
| Invalid output retry | **LLM** (was code) |
| Final safety fallback (after retry fails) | Code (acceptable — true last resort) |

This would bring the system to **~95% LLM-driven**, with code only as a final safety net when the LLM fails twice.
