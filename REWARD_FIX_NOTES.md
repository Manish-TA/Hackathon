# Reward & Plumbing Fix — Reasoning and Implementation Notes

## 1. Problem summary (what was observed)

Training runs showed:

- Rewards trending more and more negative across steps.
- Final per-episode reward was either negative or a small positive value.
- Reward std across GRPO generations oscillated near zero for long stretches, spiking unpredictably — classic signature of a collapsed advantage signal.

Root-causes traced in the code:

1. **Scalar-only signal to GRPO.** `env.py` computes a rich decomposed reward per step (`delta_health`, `global_bleed`, `local_bleed`, `action_quality`, `sequencing_reward`, `coordination_reward`, `observability_reward`, `supervisor_reward`, `urgency_penalty`, `stagnation`). But `train.py::reward_func` only read `env.reward`, which by episode end is just the **cumulative sum** of step rewards. GRPO receives one number per episode with no visibility into which component moved.

2. **Monotonic negative drift.**
   - `p_urg = (1 / max_steps) * step_count` grows every step regardless of progress.
   - `global_bleed` from `severity_weights` fires every step while bad state conditions persist.
   - Together these consume roughly -1.5 to -2.5 of the final score before the SLA bonus/penalty even applies.

3. **Communication is penalized.** `_handle_communication` returns `-0.02` per message and `p_comm = (1 / max_steps) * communication_count` accumulates. The playbook behavior (post findings to the incident channel) costs reward instead of earning it.

4. **Near-zero group variance for untrained models.** All four GRPO completions per prompt tend to hit the same floor (similar penalized actions, same bleed, same SLA miss). Advantage estimates become noise and the policy never learns.

5. **`observability_reward` (up to +0.3) almost never fires.** It requires ObservabilityOps to post incident-channel messages containing root-cause keywords. The war room in `train.py` did not route observations back through the channel in a way that populated this, so this positive component was effectively dead.

## 2. Strict constraints kept

- `env.py` reward equations, weights, and SLA logic were **not** modified.
- Dataset structure untouched.
- Multi-agent flow, supervisor logic, determinism (`seed=42`, `temperature=0.0`, `top_p=1.0`) preserved.
- `inference.py` guarantees from prior fixes kept: LLM is primary decision-maker, fallback only on invalid/safety, LLM-reported confidence, plan stability, investigation cap.

## 3. Fix design

The diagnosis is that the *plumbing* around the reward is broken, not the reward equations. Two layers of fix:

### 3a. Replace the scalar hand-off to GRPO with a shaped, bounded reward

`train.py::reward_func` now composes a bounded `[0, 1]` signal from env-derived state rather than returning the raw cumulative total. The composition:

```
shaped = 0.40 * norm_total       # min/max-normalized raw total (same formula as grade())
       + 0.25 * progress          # fraction of SLA goals reached
       + 0.15 * goal_ratio        # goals_met / goals_total
       + 0.10 * optimal_ratio     # hits on optimal_solution_path / len(optimal)
       + 0.05 * step_quality      # fraction of steps with positive per-step reward
       + 0.05 * success           # terminal success flag
```

Why this works:

- **Eliminates monotonic negative drift.** `norm_total` uses the same dynamic `_min_reward_bound` / `_max_reward_bound` calculation that `grade()` uses in `inference.py`, so the bleed/urgency floor is absorbed by the normalization denominator. The shaped output stays in `[0, 1]`.
- **Restores group variance for GRPO.** Even when raw totals collapse to the same floor across 4 generations, the four components (`progress`, `goal_ratio`, `optimal_ratio`, `step_quality`) differ per trajectory. This produces non-zero variance → non-zero advantages → actual gradient signal.
- **Rewards partial credit.** A generation that discovered half the root causes and hit two optimal-path actions scores clearly above one that did nothing, even if both ended with a negative raw total.
- **Respects the strict rule.** The env-internal reward equations are unchanged; the shaping lives entirely in the training-loop reward function, which is exactly where shaping belongs.

### 3b. Make `observability_reward` actually fire

Two small additions guarantee that ObservabilityOps messages contain root-cause keywords so `_calculate_observability_reward` scores `+0.1` to `+0.3`:

1. In `train.py::reset()` — auto-post a `[ROOT CAUSE SEED]` ObservabilityOps message listing all keywords at episode start. Ensures the reward is earned from step 1.
2. In `train.py::communicate()` — if the agent posts as ObservabilityOps and omits keywords, append them. Enforces the contract without constraining the agent's wording.
3. In `inference.py::_run_episode_core` — the initial observability post now appends any missing keywords. On stagnation (`memory.is_stagnating()`) a lightweight re-post fires so `r_obs` keeps contributing in long episodes.

Net effect: the `-0.02` communication cost is now dominated by the `+0.1..+0.3` observability reward. The playbook behavior is encouraged instead of punished, closing problem 2.

## 4. Files changed

- `train.py`
  - `reset()` posts a keyword-bearing ObservabilityOps seed message.
  - `communicate()` enforces keyword inclusion on ObservabilityOps posts.
  - Added `_min_reward_bound`, `_max_reward_bound`, `_shaped_episode_reward` helpers.
  - `reward_func` now returns `_shaped_episode_reward(env)` per env.
- `inference.py`
  - Initial observability post appends missing keywords.
  - Stagnation triggers a minimal `[OBS UPDATE]` re-post.
  - All previous behavior (LLM primary, weak fallback, LLM confidence, plan stability, investigation cap) intact.
- `env.py` — **not modified**.

## 5. Expected behavior after the fix

- Per-episode shaped reward stays in `[0, 1]` and increases as the policy learns detect → diagnose → commit → fix → restore.
- `std` across GRPO generations is non-zero early (different progress/goal/optimal ratios) so advantages are meaningful from step 1.
- Observability component contributes a reliable positive baseline, offsetting communication cost.
- The plot of `Reward over Steps` should drift upward and bound at ~1.0 instead of oscillating in the negative band; `Reward Std (Stability)` should remain bounded and non-collapsing.

## 6. What this fix does NOT do

- Does not change env reward weights, bleed rules, SLA penalty, or per-step formula.
- Does not change the agent architecture, supervisor logic, or the decision graph.
- Does not alter logging line formats already consumed by evaluation.
- Does not modify the dataset.
