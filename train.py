"""
OpsSim-AI GRPO Training Script
===============================
Trains a language model to be a DevOps incident-response agent using
Group Relative Policy Optimization (GRPO) with TRL's environment_factory.

The agent interacts with DevOpsEnv via tool-calling: it reads the incident
description, chooses actions from the available set, and receives rewards
based on how well it resolves the incident.

Usage:
    # Single GPU (default, small model)
    python train.py

    # Multi-GPU with accelerate
    accelerate launch train.py

    # Override defaults
    python train.py --model Qwen/Qwen3-1.7B --task easy --num_train_epochs 3
"""

import argparse
import json
import os
import sys

from datasets import Dataset
from trl import GRPOConfig, GRPOTrainer

# ---------------------------------------------------------------------------
# Environment wrapper for TRL environment_factory
# ---------------------------------------------------------------------------

class OpsSIMTrainingEnv:
    """
    TRL-compatible environment wrapper around DevOpsEnv.

    TRL's environment_factory expects a class with:
      - reset(**kwargs) -> str | None
      - public methods (exposed as tools) with typed args and Google-style docstrings
    
    The reward is accumulated in self.reward and read by the reward function.
    """

    def __init__(self):
        # Lazy import so the module path is resolved at instantiation time
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from env import DevOpsEnv
        self.env = DevOpsEnv(seed=None, max_steps=8)
        self.reward = 0.0
        self.done = False
        self.task_type = "easy"
        self._available_actions = []

    def reset(self, prompt=None, **kwargs) -> str:
        """Reset the environment and return the initial incident description."""
        # Extract task type from the prompt metadata if provided
        task = "easy"
        if prompt and isinstance(prompt, list):
            # Conversational format: check the user message for task hints
            for msg in prompt:
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                if "[CASCADE]" in content:
                    task = "cascade"
                elif "[MEDIUM]" in content:
                    task = "medium"
                elif "[HARD]" in content:
                    task = "hard"

        self.task_type = task
        self.reward = 0.0
        self.done = False

        obs = self.env.reset(task=task)
        self._available_actions = obs.available_actions or []

        # Build a textual observation for the LLM
        parts = []
        if obs.user_message:
            parts.append(f"Incident Report: {obs.user_message}")
        if obs.user_messages:
            parts.append("User Reports:\n" + "\n".join(f"  - {m}" for m in obs.user_messages))
        if obs.logs:
            parts.append(f"System Logs:\n{obs.logs}")
        if obs.config:
            parts.append(f"Current Config: {json.dumps(obs.config)}")
        if obs.system_metrics:
            parts.append(f"System Metrics: {json.dumps(obs.system_metrics)}")
        if obs.system_state:
            parts.append(f"System State: {json.dumps(obs.system_state, default=str)}")
        if obs.playbook_text:
            parts.append(f"Playbook:\n{obs.playbook_text}")
        if obs.alerts:
            parts.append("Alerts:\n" + "\n".join(f"  - {a}" for a in obs.alerts))

        parts.append(f"\nAvailable Actions: {', '.join(self._available_actions)}")
        parts.append(
            "\nYour task: Analyze the incident and take the best action to resolve it. "
            "Use the take_action tool to execute an action."
        )

        return "\n\n".join(parts)

    def take_action(self, action_type: str) -> str:
        """
        Execute a DevOps action in the environment.

        Args:
            action_type: The action to execute. Must be one of the available actions.

        Returns:
            A string describing the result of the action and updated system state.
        """
        if self.done:
            return "The incident has already been resolved or the episode has ended."

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from models import Action

        action = Action(action_type=action_type)
        obs, reward_obj, done, info = self.env.step(action)

        self.reward += reward_obj.value
        self.done = done

        # Build response text
        parts = []
        if obs.logs:
            parts.append(f"Logs: {obs.logs}")
        if obs.config:
            parts.append(f"Config: {json.dumps(obs.config)}")
        if obs.system_metrics:
            parts.append(f"Metrics: {json.dumps(obs.system_metrics)}")
        if obs.system_state:
            parts.append(f"State: {json.dumps(obs.system_state, default=str)}")
        if obs.user_messages:
            parts.append("User Messages:\n" + "\n".join(f"  - {m}" for m in obs.user_messages))

        parts.append(f"Step Reward: {reward_obj.value:.3f}")
        parts.append(f"Cumulative Reward: {self.reward:.3f}")
        parts.append(f"Done: {done}")

        if not done:
            parts.append(f"\nAvailable Actions: {', '.join(self._available_actions)}")
            parts.append("Choose your next action wisely.")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Reward function
# ---------------------------------------------------------------------------

def reward_func(environments, **kwargs):
    """Read cumulative reward from each environment instance."""
    return [env.reward for env in environments]


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------

def build_dataset(task_types=None):
    """
    Build a training dataset of incident prompts from the task JSON files.
    Each prompt describes an incident and asks the agent to resolve it.
    """
    if task_types is None:
        task_types = ["easy", "medium", "hard"]

    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompts = []

    task_file_map = {
        "easy": ("tasks/easy.json", "easy_tasks_dataset"),
        "medium": ("tasks/medium.json", "medium_tasks_dataset"),
        "hard": ("tasks/hard.json", "hard_tasks_dataset"),
        "cascade": ("tasks/cascade.json", "cascade_tasks_dataset"),
    }

    for task_type in task_types:
        if task_type not in task_file_map:
            continue
        filepath, key = task_file_map[task_type]
        full_path = os.path.join(base_dir, filepath)
        if not os.path.exists(full_path):
            print(f"Warning: {full_path} not found, skipping {task_type} tasks")
            continue

        with open(full_path, "r") as f:
            scenarios = json.load(f)[key]

        tag = f"[{task_type.upper()}] " if task_type != "easy" else ""

        for scenario in scenarios:
            scenario_id = scenario.get("scenario_id", "unknown")

            # Build the incident description
            parts = [f"{tag}DevOps Incident: {scenario_id}"]

            if "observation" in scenario:
                obs = scenario["observation"]
                if "user_message" in obs:
                    parts.append(f"\nIncident Report: {obs['user_message']}")

            if "initial_messages" in scenario:
                parts.append("\nUser Reports:")
                for msg in scenario["initial_messages"]:
                    parts.append(f"  - {msg}")

            if "description" in scenario:
                parts.append(f"\nDescription: {scenario['description']}")

            parts.append(
                "\nYou are a DevOps engineer. Analyze this incident and use the "
                "take_action tool to resolve it step by step."
            )

            prompt_text = "\n".join(parts)
            prompts.append({
                "prompt": [{"role": "user", "content": prompt_text}],
            })

    # Repeat to ensure enough data for training
    if len(prompts) < 32:
        repeat_factor = max(1, 32 // len(prompts))
        prompts = prompts * repeat_factor

    return Dataset.from_list(prompts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="OpsSim-AI GRPO Training")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-0.6B",
                        help="HuggingFace model ID or local path")
    parser.add_argument("--output_dir", type=str, default="./opssim-grpo-output",
                        help="Directory to save model checkpoints")
    parser.add_argument("--task", type=str, default="all",
                        choices=["easy", "medium", "hard", "cascade", "all"],
                        help="Which task difficulty to train on")
    parser.add_argument("--num_train_epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--per_device_batch_size", type=int, default=2,
                        help="Batch size per device")
    parser.add_argument("--num_generations", type=int, default=4,
                        help="Number of completions per prompt for GRPO")
    parser.add_argument("--max_completion_length", type=int, default=512,
                        help="Maximum completion token length")
    parser.add_argument("--learning_rate", type=float, default=1e-6,
                        help="Learning rate")
    parser.add_argument("--max_tool_calling_iterations", type=int, default=8,
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

    # Determine task types
    if args.task == "all":
        task_types = ["easy", "medium", "hard", "cascade"]
    else:
        task_types = [args.task]

    print(f"Building dataset for task types: {task_types}")
    dataset = build_dataset(task_types)
    print(f"Dataset size: {len(dataset)} prompts")

    # PEFT config for memory-efficient training
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
            peft_config = None

    # Training config
    training_args = GRPOConfig(
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

    print(f"Training model: {args.model}")
    print(f"Output dir: {args.output_dir}")

    trainer = GRPOTrainer(
        model=args.model,
        args=training_args,
        train_dataset=dataset,
        reward_funcs=reward_func,
        environment_factory=OpsSIMTrainingEnv,
        peft_config=peft_config,
    )

    trainer.train()

    # Save final model
    trainer.save_model(os.path.join(args.output_dir, "final"))
    print(f"Training complete. Model saved to {args.output_dir}/final")


if __name__ == "__main__":
    main()
