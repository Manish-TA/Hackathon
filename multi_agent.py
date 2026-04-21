"""
OpsSim-AI Multi-Agent War Room (Theme #1)
==========================================
Wraps DevOpsEnv to simulate an incident war room with two cooperating agents:

  - Diagnostics Agent ("Eyes"): Can only investigate/observe. Writes findings
    to a shared message board.
  - Remediation Agent ("Hands"): Can only act/fix. Reads the message board
    to decide what to do.

Neither agent alone can solve the incident. The diagnostics agent discovers
the root cause but can't fix it; the remediation agent can fix things but
doesn't know what's broken unless the diagnostics agent tells it.

Usage:
    from multi_agent import WarRoom

    room = WarRoom(task="cascade", seed=42)
    obs_diag, obs_remed = room.reset()

    # Diagnostics agent investigates
    obs_diag, shared = room.step_diagnostics("investigate_payment_service")

    # Remediation agent reads shared board and acts
    obs_remed, shared = room.step_remediation("reboot_redis")

    print(room.get_reward())
"""

import json
import os
import sys
import re

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from env import DevOpsEnv
from models import Action, Observation


def _classify_actions(available_actions):
    """Split actions into diagnostic (investigate/check/audit/scan/trace)
    and remediation (restart/reboot/fix/deploy/rollback/flush/etc.) sets."""
    diag_patterns = re.compile(
        r"^(investigate|check|scan|trace|audit|inspect|analyze|view|monitor)"
    )
    # "do_nothing" is available to both
    diag_actions = []
    remed_actions = []

    for action in available_actions:
        if action == "do_nothing":
            diag_actions.append(action)
            remed_actions.append(action)
        elif diag_patterns.match(action):
            diag_actions.append(action)
        else:
            remed_actions.append(action)

    # Ensure both sides have at least do_nothing
    if not diag_actions:
        diag_actions = ["do_nothing"]
    if not remed_actions:
        remed_actions = ["do_nothing"]

    return sorted(diag_actions), sorted(remed_actions)


class WarRoom:
    """
    Two-agent cooperative wrapper around DevOpsEnv.

    Agents take alternating turns (diagnostics first, then remediation).
    They share a message board: diagnostics writes findings, remediation reads them.
    """

    def __init__(self, task="cascade", seed=42, max_steps=15):
        self.env = DevOpsEnv(seed=seed, max_steps=max_steps)
        self.task = task

        # Shared communication channel
        self.message_board = []

        # Track per-agent rewards
        self.diag_reward = 0.0
        self.remed_reward = 0.0

        self.diag_actions = []
        self.remed_actions = []
        self.done = False
        self.turn = "diagnostics"  # who goes first

    def reset(self):
        """Reset the environment and return observations for both agents."""
        obs = self.env.reset(task=self.task)
        self.message_board = []
        self.diag_reward = 0.0
        self.remed_reward = 0.0
        self.done = False
        self.turn = "diagnostics"

        all_actions = obs.available_actions or []
        self.diag_actions, self.remed_actions = _classify_actions(all_actions)

        # Each agent gets a partial view
        diag_obs = Observation(
            task_type=obs.task_type,
            user_message=obs.user_message,
            logs=obs.logs,
            system_state=obs.system_state,
            playbook_text=obs.playbook_text,
            available_actions=self.diag_actions,
            step_count=0,
        )

        remed_obs = Observation(
            task_type=obs.task_type,
            user_message=obs.user_message,
            logs="Waiting for diagnostics report...",
            available_actions=self.remed_actions,
            playbook_text=obs.playbook_text,
            step_count=0,
        )

        return diag_obs, remed_obs

    def step_diagnostics(self, action_type):
        """Diagnostics agent takes an investigate/check action.
        Findings are automatically posted to the shared message board."""
        if self.done:
            return self._make_done_obs(self.diag_actions), self.message_board

        action = Action(action_type=action_type)
        obs, reward, done, info = self.env.step(action)
        self.diag_reward += reward.value
        self.done = done

        # Extract findings and post to message board
        finding = f"[DIAG] Action: {action_type}"
        if obs.logs:
            finding += f" | Result: {obs.logs.split(chr(10))[-1].strip()}"

        # Include any state changes the diagnostics agent discovered
        if obs.system_state:
            discovered = obs.system_state.get("discovered", {})
            new_findings = {k: v for k, v in discovered.items() if v is True}
            if new_findings:
                finding += f" | Discovered: {', '.join(new_findings.keys())}"

        self.message_board.append(finding)
        self.turn = "remediation"

        diag_obs = Observation(
            task_type=obs.task_type,
            logs=obs.logs,
            system_state=obs.system_state,
            available_actions=self.diag_actions,
            step_count=obs.step_count,
        )

        return diag_obs, list(self.message_board)

    def step_remediation(self, action_type):
        """Remediation agent takes a fix/restart/deploy action.
        Can read the message board to decide what to do."""
        if self.done:
            return self._make_done_obs(self.remed_actions), self.message_board

        action = Action(action_type=action_type)
        obs, reward, done, info = self.env.step(action)
        self.remed_reward += reward.value
        self.done = done

        result = f"[REMED] Action: {action_type} | Reward: {reward.value:.3f}"
        self.message_board.append(result)
        self.turn = "diagnostics"

        remed_obs = Observation(
            task_type=obs.task_type,
            logs=obs.logs,
            system_state=obs.system_state,
            available_actions=self.remed_actions,
            step_count=obs.step_count,
        )

        return remed_obs, list(self.message_board)

    def get_reward(self):
        """Return combined reward (cooperative — both agents share the goal)."""
        return self.diag_reward + self.remed_reward

    def get_message_board(self):
        """Return the shared message board."""
        return list(self.message_board)

    def is_done(self):
        return self.done

    def _make_done_obs(self, actions):
        return Observation(
            task_type=self.task,
            logs="Incident resolved or episode ended.",
            available_actions=actions,
            step_count=self.env.step_count,
        )


# ---------------------------------------------------------------------------
# LLM-driven agents
# ---------------------------------------------------------------------------

class LLMDiagnosticsAgent:
    """LLM-powered diagnostics agent that decides which investigation action to take."""

    def __init__(self, client, model_name):
        self.client = client
        self.model = model_name

    def choose_action(self, obs, message_board, available_actions):
        board_text = "\n".join(message_board) if message_board else "No findings yet."

        prompt = f"""You are the DIAGNOSTICS engineer in an incident war room.
Your role: INVESTIGATE and DISCOVER what is broken. You CANNOT fix anything.

Current system state:
{json.dumps(obs.system_state, indent=2, default=str) if obs.system_state else "Unknown — investigate to discover."}

Logs:
{obs.logs or "No logs yet."}

Shared Message Board (findings so far):
{board_text}

Your available actions (investigation only):
{json.dumps(available_actions)}

Rules:
- Pick the most informative investigation action based on what's already known.
- Don't repeat investigations that are already on the message board.
- Your findings will be shared with the Remediation engineer.

Return ONLY JSON:
{{"action": "<exact_action_from_list>"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=50,
            )
            text = response.choices[0].message.content or ""
            data = json.loads(text)
            action = data.get("action", "")
            if action in available_actions:
                return action
        except Exception:
            pass
        # Fallback: pick first unused investigation action
        used = {m.split("Action: ")[1].split(" |")[0] for m in message_board if "[DIAG]" in m and "Action: " in m}
        for a in available_actions:
            if a not in used and a != "do_nothing":
                return a
        return available_actions[0]


class LLMRemediationAgent:
    """LLM-powered remediation agent that reads the message board and decides what to fix."""

    def __init__(self, client, model_name):
        self.client = client
        self.model = model_name

    def choose_action(self, obs, message_board, available_actions):
        board_text = "\n".join(message_board) if message_board else "No findings yet — wait for diagnostics."

        prompt = f"""You are the REMEDIATION engineer in an incident war room.
Your role: FIX the issues that the Diagnostics engineer has discovered. You CANNOT investigate.

Shared Message Board (diagnostics findings + your previous actions):
{board_text}

System state (may be partial):
{json.dumps(obs.system_state, indent=2, default=str) if obs.system_state else "Waiting for diagnostics."}

Logs:
{obs.logs or "No logs yet."}

Your available actions (fixes only):
{json.dumps(available_actions)}

Rules:
- Only act on issues that diagnostics has CONFIRMED on the message board.
- If diagnostics hasn't found the root cause yet, use "do_nothing" and wait.
- Don't repeat actions that already succeeded.
- Fix the most critical issue first.

Return ONLY JSON:
{{"action": "<exact_action_from_list>"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=50,
            )
            text = response.choices[0].message.content or ""
            data = json.loads(text)
            action = data.get("action", "")
            if action in available_actions:
                return action
        except Exception:
            pass
        # Fallback: if board has diagnostics findings, pick first fix action
        if any("[DIAG]" in m for m in message_board):
            used = {m.split("Action: ")[1].split(" |")[0] for m in message_board if "[REMED]" in m and "Action: " in m}
            for a in available_actions:
                if a not in used and a != "do_nothing":
                    return a
        return "do_nothing"


def run_war_room(task="cascade", seed=42, max_steps=15, model_name=None, hf_token=None):
    """Run a full war room episode with two LLM agents coordinating."""
    from dotenv import load_dotenv
    load_dotenv()

    api_base = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    model = model_name or os.getenv("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
    token = hf_token or os.getenv("HF_TOKEN")

    if not token:
        raise ValueError("HF_TOKEN required. Set it in .env or pass hf_token=")

    client = OpenAI(base_url=api_base, api_key=token)
    diag_agent = LLMDiagnosticsAgent(client, model)
    remed_agent = LLMRemediationAgent(client, model)

    room = WarRoom(task=task, seed=seed, max_steps=max_steps)
    diag_obs, remed_obs = room.reset()

    print(f"=== LLM WAR ROOM ({model}) ===")
    print(f"Task: {task}")
    print(f"Diagnostics actions: {room.diag_actions}")
    print(f"Remediation actions: {room.remed_actions}")
    print()

    step = 0
    while not room.is_done() and step < max_steps:
        # Diagnostics turn
        if not room.is_done():
            action = diag_agent.choose_action(diag_obs, room.get_message_board(), room.diag_actions)
            diag_obs, board = room.step_diagnostics(action)
            step += 1
            print(f"Step {step} [DIAG] {action}")
            print(f"  → {board[-1]}")

        # Remediation turn
        if not room.is_done():
            action = remed_agent.choose_action(remed_obs, room.get_message_board(), room.remed_actions)
            remed_obs, board = room.step_remediation(action)
            step += 1
            print(f"Step {step} [REMED] {action}")
            print(f"  → {board[-1]}")

        print()

    print(f"=== RESULTS ===")
    print(f"Diagnostics reward: {room.diag_reward:.3f}")
    print(f"Remediation reward: {room.remed_reward:.3f}")
    print(f"Combined reward:    {room.get_reward():.3f}")
    print(f"Resolved: {room.is_done()}")
    return room


# ---------------------------------------------------------------------------
# Quick demo / test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpsSim-AI War Room")
    parser.add_argument("--mode", choices=["scripted", "llm"], default="scripted",
                        help="scripted = hardcoded steps, llm = LLM agents decide")
    parser.add_argument("--task", default="cascade", help="Task type")
    parser.add_argument("--model", default=None, help="HuggingFace model name")
    args = parser.parse_args()

    if args.mode == "llm":
        run_war_room(task=args.task, model_name=args.model)
    else:
        room = WarRoom(task=args.task, seed=42)
        diag_obs, remed_obs = room.reset()

        print("=== WAR ROOM SIMULATION (scripted) ===")
        print(f"Diagnostics can: {diag_obs.available_actions}")
        print(f"Remediation can: {remed_obs.available_actions}")
        print()

        # Scripted optimal sequence for cascade_001
        steps = [
            ("diag", "investigate_payment_service"),
            ("diag", "investigate_cache"),
            ("remed", "reboot_redis"),
            ("diag", "investigate_database"),
            ("remed", "flush_db_connections"),
            ("remed", "restart_checkout"),
        ]

        for agent, action in steps:
            if room.is_done():
                break
            if agent == "diag":
                obs, board = room.step_diagnostics(action)
                print(f"[DIAG] {action}")
            else:
                obs, board = room.step_remediation(action)
                print(f"[REMED] {action}")
            print(f"  Latest message: {board[-1]}")
            print(f"  Done: {room.is_done()}")
            print()

        print(f"=== RESULTS ===")
        print(f"Diagnostics reward: {room.diag_reward:.3f}")
        print(f"Remediation reward: {room.remed_reward:.3f}")
        print(f"Combined reward:    {room.get_reward():.3f}")
        print()
        print("Message Board:")
        for msg in room.get_message_board():
            print(f"  {msg}")
