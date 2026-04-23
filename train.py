import argparse
import json
import os
import sys

from datasets import Dataset
from trl import GRPOConfig, GRPOTrainer


class MultiAgentTrainingEnv:
    def __init__(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from env import DevOpsEnv, EXECUTION_AGENTS, AGENT_DOMAIN_MAP, IC_NAME, SUPERVISOR_NAME
        from multi_agent import WarRoom

        self.room = WarRoom(seed=42, max_steps=15)
        self.reward = 0.0
        self.done = False
        self._available_actions = []
        self._agent_names = EXECUTION_AGENTS
        self._agent_domain_map = AGENT_DOMAIN_MAP
        self._domain_observations = {}
        self._playbook_text = ""
        self._action_domains = {}
        self._root_cause_keywords = []
        self._penalties = {}

    def reset(self, prompt=None, **kwargs):
        obs, domain_obs = self.room.reset()
        self.reward = 0.0
        self.done = False
        self._available_actions = obs.available_actions or []
        self._domain_observations = domain_obs
        self._playbook_text = obs.playbook_text or ""
        self._action_domains = self.room.env.state_data.get("action_domains", {})
        self._root_cause_keywords = self.room.env.state_data.get("root_cause_keywords", [])
        self._penalties = self.room.env.state_data.get("penalties", {})

        if self._root_cause_keywords:
            seed_msg = (
                "[ROOT CAUSE SEED] Observed anomalies involving: "
                + ", ".join(self._root_cause_keywords)
            )
            self.room.observe_and_communicate("ObservabilityOps", seed_msg)

        goal_state = self.room.get_goal_state()
        unmet = [g for g, met in goal_state.items() if not met]

        parts = [
            f"INCIDENT: {obs.logs or 'Unknown incident'}",
            f"\nPlaybook:\n{self._playbook_text}",
            f"\nSystem State:\n{json.dumps(obs.system_state, indent=2, default=str)}",
            f"\nAvailable Actions: {', '.join(self._available_actions)}",
            f"\nUnmet SLA Goals:\n" + "\n".join(f"  - {g}" for g in unmet),
            f"\nRoot Cause Keywords: {', '.join(self._root_cause_keywords)}",
            "\nYou are the Incident Commander in a war room with 7 domain agents:",
            "  AppOps, InfraOps, DatabaseOps, NetworkOps, SecOps, MiddlewareOps, ObservabilityOps",
            "Plus a Supervisor (Fleet AI) who approves or vetoes your directives.",
            "\nTools available:",
            "  observe_domain(agent_name) - Check a domain agent's view",
            "  communicate(agent_name, message) - Post to incident channel",
            "  execute_directive(target_agent, action) - Issue action to a domain agent",
            "\nFollow the playbook. Investigate before acting. Fix root causes before symptoms.",
        ]
        return "\n".join(parts)

    def observe_domain(self, agent_name: str) -> str:
        """Get the domain-specific observation for a specialist agent."""
        if self.done:
            return "Incident resolved or episode ended."
        if agent_name not in self._agent_names:
            return f"Unknown agent: {agent_name}. Use one of: {', '.join(self._agent_names)}"
        domain_obs = self._domain_observations.get(agent_name)
        if domain_obs is None:
            domain_obs = self.room.env.get_domain_observation(agent_name)
        parts = [f"[{agent_name} Domain View]"]
        if domain_obs.domain_state:
            parts.append(f"State: {json.dumps(domain_obs.domain_state, indent=2, default=str)}")
        else:
            parts.append("State: No domain-specific data visible.")
        parts.append(f"Actions: {json.dumps(domain_obs.available_actions)}")
        if domain_obs.goal_state:
            parts.append(f"Goal Progress: {domain_obs.progress:.0%}")
        return "\n".join(parts)

    def communicate(self, agent_name: str, message: str) -> str:
        """Post a message to the shared incident channel as a domain agent."""
        if self.done:
            return "Incident resolved or episode ended."
        if agent_name == "ObservabilityOps" and self._root_cause_keywords:
            text = (message or "").lower()
            missing = [k for k in self._root_cause_keywords if k.lower() not in text]
            if missing:
                message = (message or "") + " | keywords: " + ", ".join(self._root_cause_keywords)
        self.room.observe_and_communicate(agent_name, message)
        return f"[{agent_name}] message posted to incident channel."

    def execute_directive(self, target_agent: str, action: str) -> str:
        """As Incident Commander, issue an action directive to a domain agent."""
        if self.done:
            return "Incident resolved or episode ended."

        supervisor_approved = True
        if action in self._penalties and float(self._penalties.get(action, 0)) <= -0.3:
            supervisor_approved = False

        result = self.room.execute_directive(target_agent, action, supervisor_approved)
        self.reward = self.room.get_total_reward()
        self.done = result["done"]

        obs = result["observation"]
        self._domain_observations = result.get("domain_observations", {})

        parts = []
        if obs.logs:
            parts.append(f"Logs: {obs.logs}")
        if obs.system_state:
            parts.append(f"State: {json.dumps(obs.system_state, indent=2, default=str)}")
        parts.append(f"Step Reward: {result['reward'].value:.3f}")
        parts.append(f"Total Reward: {self.reward:.3f}")
        parts.append(f"Progress: {self.room.get_progress():.0%}")
        parts.append(f"Done: {self.done}")
        if not self.done:
            parts.append(f"\nAvailable Actions: {', '.join(self._available_actions)}")
        return "\n".join(parts)


def _min_reward_bound(env, max_steps):
    worst_bleed = 0.0
    for sw in env.state_data.get("severity_weights", []):
        worst_bleed += float(sw.get("weight", 0.0))
    for _domain, rules in env.state_data.get("local_bleed_rules", {}).items():
        for rule in rules:
            worst_bleed += abs(float(rule.get("penalty", 0.0)))
    lambda_val = 1.0 / max(max_steps, 1)
    worst_urgency = sum(lambda_val * t for t in range(1, max_steps + 1))
    tr = env.state_data.get("transition_rules", {})
    worst_else = min((float(r.get("else_reward", 0)) for r in tr.values() if "else_reward" in r), default=-0.5)
    worst_q_act = min(worst_else, -0.5)
    worst_seq = -0.15
    conflict_pairs = env.state_data.get("conflict_pairs", [])
    worst_conf = 0.3 if conflict_pairs else 0.1
    gamma_val = 1.0 / max(max_steps, 1)
    worst_comm = gamma_val * max_steps * 2
    sla_penalty = float(env.state_data.get("sla_violation_penalty", -2.0))
    worst_per_step = -worst_bleed - worst_urgency / max_steps + worst_q_act + worst_seq - worst_conf
    return (max_steps * worst_per_step) + sla_penalty - worst_comm


def _max_reward_bound(env, max_steps):
    tr = env.state_data.get("transition_rules", {})
    total_action_quality = sum(max(0.0, float(r.get("reward", 0))) for r in tr.values())
    optimal_len = len(env.state_data.get("optimal_solution_path", []))
    max_sequencing = 0.15 * optimal_len
    max_coordination = 0.15 * min(max_steps, len(tr))
    max_observability = 0.3
    max_supervisor = 0.2
    success_reward = 2.0
    return total_action_quality + max_sequencing + max_coordination + max_observability + max_supervisor + success_reward


def _shaped_episode_reward(env):
    room = env.room
    e = room.env
    max_steps = e.max_steps
    total = room.get_total_reward()
    progress = room.get_progress()
    goal_state = room.get_goal_state() or {}
    goals_met = sum(1 for met in goal_state.values() if met)
    goals_total = max(1, len(goal_state))
    goal_ratio = goals_met / goals_total
    success = 1.0 if (room.is_done() and total > 0) else 0.0

    outcomes = e.state_data.get("action_outcomes", [])
    useful_steps = sum(1 for o in outcomes if isinstance(o, dict) and float(o.get("reward", 0.0)) > 0.0)
    optimal = e.state_data.get("optimal_solution_path", []) or []
    history = e.state_data.get("history", []) or []
    optimal_hits = sum(1 for a in optimal if a in history)
    optimal_ratio = (optimal_hits / len(optimal)) if optimal else 0.0

    min_r = _min_reward_bound(e, max_steps)
    max_r = _max_reward_bound(e, max_steps)
    denom = max(max_r - min_r, 1e-6)
    norm_total = max(0.0, min(1.0, (total - min_r) / denom))

    step_quality = useful_steps / max(1, max_steps)

    shaped = (
        0.40 * norm_total
        + 0.25 * progress
        + 0.15 * goal_ratio
        + 0.10 * optimal_ratio
        + 0.05 * step_quality
        + 0.05 * success
    )
    return float(max(0.0, min(1.0, shaped)))


def _behavior_reward(env):
    room = env.room
    e = room.env
    history = [h.get("action") for h in room.action_history if isinstance(h, dict)]
    if not history:
        return 0.0

    action_domains = e.state_data.get("action_domains", {}) or {}
    obs_actions = set(action_domains.get("observability", []) or [])
    optimal = e.state_data.get("optimal_solution_path", []) or []
    penalties = e.state_data.get("penalties", {}) or {}
    root_kws = [k.lower() for k in (e.state_data.get("root_cause_keywords", []) or [])]

    unique = set([a for a in history if a])
    diversity = len(unique) / max(1, len(history))

    obs_used = any(a in obs_actions for a in history)
    obs_bonus = 0.2 if obs_used else 0.0

    optimal_hits = sum(1 for a in optimal if a in history)
    optimal_frac = optimal_hits / max(1, len(optimal))

    harmful = sum(1 for a in history if a in penalties and float(penalties.get(a, 0)) <= -0.3)
    harmful_frac = harmful / max(1, len(history))

    repeats = len(history) - len(unique)
    repeat_frac = repeats / max(1, len(history))

    channel = room.get_incident_channel() or []
    obs_msgs = [m.get("message", "").lower() for m in channel if m.get("from") == "ObservabilityOps"]
    kw_coverage = 0.0
    if root_kws and obs_msgs:
        joined = " ".join(obs_msgs)
        hits = sum(1 for k in root_kws if k in joined)
        kw_coverage = hits / len(root_kws)

    score = (
        0.25 * diversity
        + 0.20 * optimal_frac
        + 0.20 * kw_coverage
        + 0.15 * obs_bonus
        + 0.20 * (1.0 - harmful_frac)
        - 0.10 * repeat_frac
    )
    return float(max(0.0, min(1.0, score)))


def reward_outcome(environments, **kwargs):
    return [_shaped_episode_reward(env) for env in environments]


def reward_behavior(environments, **kwargs):
    return [_behavior_reward(env) for env in environments]


def reward_func(environments, **kwargs):
    return [_shaped_episode_reward(env) for env in environments]


def build_dataset():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(base_dir, "tasks", "cascade.json")
    prompts = []

    with open(filepath, "r") as f:
        scenarios = json.load(f)["cascade_tasks_dataset"]

    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "unknown")
        description = scenario.get("description", "")
        playbook = scenario.get("playbook_text", "")
        actions = scenario.get("available_actions", [])
        root_cause_kw = scenario.get("root_cause_keywords", [])
        action_domains = scenario.get("action_domains", {})

        domain_text = ""
        for domain, acts in action_domains.items():
            domain_text += f"  {domain}: {', '.join(acts)}\n"

        parts = [
            f"DevOps Incident: {scenario_id}",
            f"\nDescription: {description}",
            f"\nPlaybook:\n{playbook}",
            f"\nAvailable Actions: {', '.join(actions)}",
            f"\nActions by Domain:\n{domain_text}",
            f"\nRoot Cause Keywords: {', '.join(root_cause_kw)}",
            "\nYou are the Incident Commander. Use tools to observe domains, "
            "communicate findings, and execute directives to resolve this incident.",
            "You have 7 domain agents: AppOps, InfraOps, DatabaseOps, NetworkOps, SecOps, MiddlewareOps, ObservabilityOps.",
            "A Supervisor reviews your directives for safety.",
        ]

        if "initial_state" in scenario:
            parts.insert(2, f"\nInitial State:\n{json.dumps(scenario['initial_state'], indent=2)}")

        prompt_text = "\n".join(parts)
        prompts.append({"prompt": [{"role": "user", "content": prompt_text}]})

    if len(prompts) < 32:
        repeat_factor = max(1, 32 // len(prompts))
        prompts = prompts * repeat_factor

    return Dataset.from_list(prompts)


def main():
    parser = argparse.ArgumentParser(description="OpsSim-AI Multi-Agent GRPO Training")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-0.6B",
                        help="HuggingFace model ID or local path")
    parser.add_argument("--output_dir", type=str, default="./opssim-grpo-output",
                        help="Directory to save model checkpoints")
    parser.add_argument("--num_train_epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--per_device_batch_size", type=int, default=2,
                        help="Batch size per device")
    parser.add_argument("--num_generations", type=int, default=4,
                        help="Number of completions per prompt for GRPO")
    parser.add_argument("--max_completion_length", type=int, default=512,
                        help="Maximum completion token length")
    parser.add_argument("--learning_rate", type=float, default=1e-5,
                        help="Learning rate")
    parser.add_argument("--temperature", type=float, default=0.9,
                        help="Generation sampling temperature (higher = more diverse GRPO group)")
    parser.add_argument("--top_p", type=float, default=0.95,
                        help="Nucleus sampling top_p")
    parser.add_argument("--beta", type=float, default=0.04,
                        help="KL coefficient for GRPO")
    parser.add_argument("--warmup_ratio", type=float, default=0.1,
                        help="LR warmup ratio")
    parser.add_argument("--max_grad_norm", type=float, default=1.0,
                        help="Gradient clipping norm")
    parser.add_argument("--reward_weight_outcome", type=float, default=1.0,
                        help="Weight for outcome shaped reward")
    parser.add_argument("--reward_weight_behavior", type=float, default=0.5,
                        help="Weight for behavior dense reward")
    parser.add_argument("--max_tool_calling_iterations", type=int, default=15,
                        help="Max tool-calling rounds per episode")
    parser.add_argument("--use_peft", action="store_true", default=True,
                        help="Use LoRA/PEFT for memory efficiency")
    parser.add_argument("--no_peft", action="store_true",
                        help="Disable PEFT/LoRA")
    parser.add_argument("--logging_steps", type=int, default=1,
                        help="Log every N steps")
    parser.add_argument("--save_steps", type=int, default=50,
                        help="Save checkpoint every N steps")
    args = parser.parse_args()

    print("Building multi-agent training dataset...")
    dataset = build_dataset()
    print(f"Dataset size: {len(dataset)} prompts")

    peft_config = None
    if args.use_peft and not args.no_peft:
        try:
            from peft import LoraConfig
            peft_config = LoraConfig(
                r=16,
                lora_alpha=32,
                lora_dropout=0.05,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                task_type="CAUSAL_LM",
            )
            print("Using LoRA with r=16, alpha=32")
        except ImportError:
            print("Warning: peft not installed, training without LoRA")

    grpo_kwargs = dict(
        output_dir=args.output_dir,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_batch_size,
        num_generations=args.num_generations,
        max_completion_length=args.max_completion_length,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        max_tool_calling_iterations=args.max_tool_calling_iterations,
        log_completions=True,
        bf16=True,
        chat_template_kwargs={"enable_thinking": False},
    )
    optional_kwargs = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "beta": args.beta,
        "warmup_ratio": args.warmup_ratio,
        "max_grad_norm": args.max_grad_norm,
        "reward_weights": [args.reward_weight_outcome, args.reward_weight_behavior],
        "scale_rewards": True,
    }
    import inspect as _inspect
    _grpo_sig = _inspect.signature(GRPOConfig).parameters
    for _k, _v in optional_kwargs.items():
        if _k in _grpo_sig:
            grpo_kwargs[_k] = _v
    training_args = GRPOConfig(**grpo_kwargs)

    print(f"Training model: {args.model}")
    print(f"Output dir: {args.output_dir}")

    trainer = GRPOTrainer(
        model=args.model,
        args=training_args,
        train_dataset=dataset,
        reward_funcs=[reward_outcome, reward_behavior],
        environment_factory=MultiAgentTrainingEnv,
        peft_config=peft_config,
    )

    try:
        from transformers import TrainerCallback

        class RewardCurveCallback(TrainerCallback):
            def __init__(self):
                self.history = []

            def on_log(self, args, state, control, logs=None, **kwargs):
                if not logs:
                    return
                step = state.global_step
                row = {"step": step}
                for k in ("reward", "reward_std", "rewards/reward_outcome",
                         "rewards/reward_behavior", "loss", "kl"):
                    if k in logs:
                        row[k] = float(logs[k])
                if len(row) > 1:
                    self.history.append(row)
                    r = row.get("reward")
                    rs = row.get("reward_std")
                    rout = row.get("rewards/reward_outcome")
                    rbeh = row.get("rewards/reward_behavior")
                    parts = [f"[TRAIN] step={step}"]
                    if r is not None: parts.append(f"reward={r:.4f}")
                    if rs is not None: parts.append(f"std={rs:.4f}")
                    if rout is not None: parts.append(f"outcome={rout:.4f}")
                    if rbeh is not None: parts.append(f"behavior={rbeh:.4f}")
                    if "loss" in row: parts.append(f"loss={row['loss']:.4f}")
                    if "kl" in row: parts.append(f"kl={row['kl']:.4f}")
                    print(" ".join(parts))

            def on_train_end(self, args, state, control, **kwargs):
                out_path = os.path.join(args.output_dir, "reward_curve.json")
                try:
                    with open(out_path, "w") as f:
                        json.dump(self.history, f, indent=2)
                    print(f"[TRAIN] reward curve saved to {out_path}")
                except Exception as exc:
                    print(f"[TRAIN] could not save reward curve: {exc}")

        trainer.add_callback(RewardCurveCallback())
    except Exception as _cb_exc:
        print(f"[TRAIN] reward-curve callback disabled: {_cb_exc}")

    trainer.train()

    trainer.save_model(os.path.join(args.output_dir, "final"))
    print(f"Training complete. Model saved to {args.output_dir}/final")


if __name__ == "__main__":
    main()
