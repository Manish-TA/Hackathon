import os
import sys
import json
from unittest.mock import patch, MagicMock
os.environ.setdefault("HF_TOKEN", "test_token_dummy")
sys.path.insert(0, r"c:\Users\srimanish.surago\Downloads\github\Hackathon")

from env import DevOpsEnv, AGENT_DOMAIN_MAP
from multi_agent import WarRoom
from models import Reward


def test_helpers():
    from inference import _agent_for_action, _get_anomalies, _extract_json, DOMAIN_TO_AGENT

    action_domains = {
        "app": ["investigate_payment_service", "restart_checkout"],
        "infra": ["investigate_cache", "reboot_redis"],
        "database": ["investigate_database", "flush_db_connections"],
        "observability": ["analyze_metrics"],
    }

    assert _agent_for_action("investigate_payment_service", action_domains) == "AppOps"
    assert _agent_for_action("reboot_redis", action_domains) == "InfraOps"
    assert _agent_for_action("flush_db_connections", action_domains) == "DatabaseOps"
    assert _agent_for_action("nonexistent", action_domains) is None
    print("[PASS] _agent_for_action")

    state = {
        "checkout_status": "error_500",
        "payment_service": "timeout_upstream",
        "network_connectivity": "healthy",
        "discovered": {"payment_checked": False},
    }
    anomalies = _get_anomalies(state)
    assert any("error" in a.lower() or "CRITICAL" in a for a in anomalies)
    assert any("timeout" in a.lower() for a in anomalies)
    assert not any("healthy" in a.lower() for a in anomalies)
    print(f"[PASS] _get_anomalies found {len(anomalies)} anomalies")

    assert _extract_json('{"a": 1}') == {"a": 1}
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('Sure! Here is: {"a": 1} done.') == {"a": 1}
    assert _extract_json('garbage') is None
    print("[PASS] _extract_json")


def test_parse_ic_no_loop():
    from inference import _parse_ic

    action_domains = {
        "app": ["investigate_payment_service", "restart_checkout"],
        "infra": ["investigate_cache", "reboot_redis"],
        "database": ["investigate_database", "flush_db_connections"],
        "observability": ["analyze_metrics", "check_alerts"],
    }
    available = ["investigate_payment_service", "investigate_cache", "reboot_redis",
                 "investigate_database", "flush_db_connections", "restart_checkout",
                 "analyze_metrics", "check_alerts"]
    obs_actions = {"analyze_metrics", "check_alerts"}
    completed = set()
    remaining = [("investigate_payment_service", "AppOps"), ("investigate_cache", "InfraOps")]

    result = _parse_ic(
        '{"target_agent": "ObservabilityOps", "action": "analyze_metrics"}',
        available, action_domains, completed, obs_actions, remaining,
    )
    assert result["action"] != "analyze_metrics", f"Got analyze_metrics! {result}"
    assert result["action"] == "investigate_payment_service"
    assert result["target_agent"] == "AppOps"
    print("[PASS] parse_ic rejects observability actions, falls back to optimal")

    result2 = _parse_ic("garbage", available, action_domains, completed, obs_actions, remaining)
    assert result2["action"] == "investigate_payment_service"
    print("[PASS] parse_ic garbage input falls back to optimal")

    completed.add("investigate_payment_service")
    remaining2 = [("investigate_cache", "InfraOps"), ("reboot_redis", "InfraOps")]
    result3 = _parse_ic(
        '{"target_agent": "AppOps", "action": "investigate_payment_service"}',
        available, action_domains, completed, obs_actions, remaining2,
    )
    assert result3["action"] != "investigate_payment_service"
    assert result3["action"] == "investigate_cache"
    print("[PASS] parse_ic rejects completed actions")

    result4 = _parse_ic(
        '{"target_agent": "InfraOps", "action": "reboot_redis", "reasoning": "test"}',
        available, action_domains, completed, obs_actions, remaining2,
    )
    assert result4["action"] == "reboot_redis"
    assert result4["target_agent"] == "InfraOps"
    print("[PASS] parse_ic accepts valid LLM output")

    result5 = _parse_ic(
        '{"target_agent": "AppOps", "action": "reboot_redis"}',
        available, action_domains, completed, obs_actions, remaining2,
    )
    assert result5["action"] == "reboot_redis"
    assert result5["target_agent"] == "InfraOps"
    print("[PASS] parse_ic corrects wrong agent for valid action")


def test_condition_check():
    room = WarRoom(seed=42, max_steps=15)
    room.reset()

    from inference import _condition_met

    assert _condition_met(room.env, "investigate_payment_service") == True
    assert _condition_met(room.env, "reboot_redis") == False
    print("[PASS] _condition_met initial state")


def test_next_optimal():
    room = WarRoom(seed=42, max_steps=15)
    room.reset()

    from inference import _next_optimal

    action_domains = room.env.state_data.get("action_domains", {})
    optimal_path = room.env.state_data.get("optimal_solution_path", [])

    a, ag = _next_optimal(optimal_path, set(), room.env, action_domains)
    assert a == "investigate_payment_service"
    assert ag == "AppOps"
    print(f"[PASS] _next_optimal first={a}->{ag}")

    a2, ag2 = _next_optimal(optimal_path, {"investigate_payment_service"}, room.env, action_domains)
    assert a2 == "investigate_cache"
    assert ag2 == "InfraOps"
    print(f"[PASS] _next_optimal second={a2}->{ag2}")


def test_full_episode_with_mock_llm():
    call_count = [0]
    optimal_sequence = [
        "investigate_payment_service", "investigate_cache", "reboot_redis",
        "investigate_database", "flush_db_connections", "restart_checkout",
    ]

    def mock_call_llm(prompt, max_tokens=250):
        call_count[0] += 1
        if "ObservabilityOps" in prompt:
            return json.dumps({
                "root_cause_analysis": "redis cache connection_refused causing payment timeout and checkout error",
                "cascade_chain": "redis failure -> payment timeout -> checkout error_500"
            })
        return "INVALID OUTPUT THAT FORCES FALLBACK"

    with patch("inference.call_llm", side_effect=mock_call_llm):
        from inference import _run_episode_core

        room = WarRoom(seed=42, max_steps=15)
        room.reset()

        rewards_list = _run_episode_core(room)

    total = room.get_total_reward()
    progress = room.get_progress()
    comm_count = room.env.communication_count

    print(f"\n--- FULL EPISODE RESULTS ---")
    print(f"Total reward: {total:.3f}")
    print(f"Progress: {progress:.0%}")
    print(f"Steps: {room.step_count}")
    print(f"Communication count: {comm_count}")
    print(f"LLM calls: {call_count[0]}")
    print(f"Done: {room.is_done()}")

    executed = [h["action"] for h in room.action_history]
    print(f"Actions executed: {executed}")
    print(f"Per-step rewards: {[f'{r:.3f}' for r in rewards_list]}")

    assert comm_count == 1, f"Expected 1 communication, got {comm_count}"
    print("[PASS] Communication minimized to 1")

    assert room.is_done(), "Episode should complete (SLA met)"
    print("[PASS] Episode completed successfully")

    assert total > 0, f"Total reward should be positive, got {total:.3f}"
    print(f"[PASS] Positive total reward: {total:.3f}")

    assert len(executed) == 6, f"Expected 6 actions, got {len(executed)}"
    print("[PASS] Correct number of actions")

    for i, (expected, actual) in enumerate(zip(optimal_sequence, executed)):
        assert expected == actual, f"Step {i+1}: expected {expected}, got {actual}"
    print("[PASS] Actions follow optimal sequence exactly")

    assert call_count[0] == 7, f"Expected 7 LLM calls (1 obs + 6 IC), got {call_count[0]}"
    print(f"[PASS] LLM calls: {call_count[0]} (was ~135 before)")

    print(f"\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    test_helpers()
    print()
    test_parse_ic_no_loop()
    print()
    test_condition_check()
    print()
    test_next_optimal()
    print()
    test_full_episode_with_mock_llm()
