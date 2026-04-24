import os
import sys
import json
from unittest.mock import patch
os.environ.setdefault("HF_TOKEN", "test_token_dummy")
sys.path.insert(0, r"c:\\Users\\srimanish.surago\\Downloads\\github\\Hackathon")

from multi_agent import WarRoom


def test_agent_memory():
    from inference import AgentMemory

    mem = AgentMemory()
    assert len(mem.actions) == 0
    assert len(mem.completed_actions) == 0

    prev = {"checkout_status": "error_500", "discovered": {"payment_checked": False}}
    curr = {"checkout_status": "error_500", "discovered": {"payment_checked": True}}
    mem.record(1, "investigate_payment_service", "AppOps", 0.2, prev, curr)

    assert "investigate_payment_service" in mem.completed_actions
    assert "investigate_payment_service" in mem.successful_actions
    assert len(mem.reward_trend) == 1
    assert mem.reward_trend[0] == 0.2
    assert not mem.is_stagnating()
    print("[PASS] AgentMemory basic recording")

    mem.record(2, "bad_action", "InfraOps", -0.5, curr, curr)
    assert "bad_action" in mem.failed_actions
    assert mem.last_failed()["action"] == "bad_action"
    print("[PASS] AgentMemory failure tracking")

    mem.record(3, "another_bad", "InfraOps", -0.3, curr, curr)
    mem.record(4, "third_bad", "InfraOps", -0.2, curr, curr)
    assert mem.is_stagnating()
    print("[PASS] AgentMemory stagnation detection")

    history = mem.format_history()
    assert "[+]" in history
    assert "[x]" in history
    print("[PASS] AgentMemory format_history")


def test_plan_tracker():
    from inference import PlanTracker

    pt = PlanTracker()
    assert "No plan yet" in pt.format_plan()

    pt.update(["investigate_cache", "reboot_redis", "flush_db_connections"])
    assert pt.revision_count == 1
    assert len(pt.current_plan) == 3

    pt.mark_done("investigate_cache")
    assert "investigate_cache" not in pt.current_plan
    assert len(pt.current_plan) == 2

    pt.update(["reboot_redis", "investigate_database", "flush_db_connections", "restart_checkout"])
    assert pt.revision_count == 2
    print("[PASS] PlanTracker plan evolution")


def test_diff_states():
    from inference import _diff_states

    prev = {"checkout_status": "error_500", "discovered": {"payment_checked": False}}
    curr = {"checkout_status": "error_500", "discovered": {"payment_checked": True}}
    diff = _diff_states(prev, curr)
    assert "discovered.payment_checked" in diff
    assert "False->True" in diff["discovered.payment_checked"]
    print("[PASS] _diff_states")


def test_helpers():
    from inference import _agent_for_action, _get_anomalies, _extract_json

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


def test_confidence_default_on_none():
    from inference import StrategyTracker

    s = StrategyTracker()
    s.ingest_llm_confidence(None, source="test")
    assert s.confidence == 0.5
    assert "default" in s.last_confidence_source
    print("[PASS] confidence defaults to 0.5 when None")

    s.ingest_llm_confidence("not_a_number", source="test")
    assert s.confidence == 0.5
    print("[PASS] confidence defaults to 0.5 when unparseable")

    s.ingest_llm_confidence(0.8, source="test")
    assert s.confidence == 0.8
    assert s.last_confidence_source == "test"
    print("[PASS] confidence set from valid LLM value")


def test_parse_planning_response_valid():
    from inference import _parse_planning_response, AgentMemory, DOMAIN_TO_AGENT

    room = WarRoom(seed=42, max_steps=15)
    room.reset()

    mem = AgentMemory()
    action_domains = room.env.state_data.get("action_domains", {})
    obs_actions = set(action_domains.get("observability", []))
    available = room.env.observation.available_actions or []

    valid_action = None
    valid_agent = None
    for domain, actions in action_domains.items():
        if domain == "observability":
            continue
        for a in actions:
            if a in available:
                valid_action = a
                valid_agent = DOMAIN_TO_AGENT[domain]
                break
        if valid_action:
            break

    response = json.dumps({
        "analysis": "diagnose",
        "plan": [valid_action],
        "next_action": valid_action,
        "target_agent": valid_agent,
        "reasoning": "root cause first",
        "confidence": 0.7,
    })
    result = _parse_planning_response(response, available, action_domains, mem, obs_actions, room.env)
    assert result["action"] == valid_action
    assert result["llm_decided"] is True
    print("[PASS] parse_planning_response accepts valid LLM JSON")


def test_parse_planning_response_rejects_invalid():
    from inference import _parse_planning_response, AgentMemory

    room = WarRoom(seed=42, max_steps=15)
    room.reset()

    mem = AgentMemory()
    action_domains = room.env.state_data.get("action_domains", {})
    obs_actions = set(action_domains.get("observability", []))
    available = room.env.observation.available_actions or []

    result = _parse_planning_response("COMPLETE GARBAGE", available, action_domains, mem, obs_actions, room.env)
    assert result["llm_decided"] is False
    assert result["action"] == ""
    print("[PASS] parse_planning_response rejects garbage (no fallback action)")

    obs_action = next(iter(obs_actions), None)
    if obs_action:
        response = json.dumps({
            "analysis": "x",
            "plan": [obs_action],
            "next_action": obs_action,
            "target_agent": "ObservabilityOps",
            "reasoning": "x",
        })
        result2 = _parse_planning_response(response, available, action_domains, mem, obs_actions, room.env)
        assert result2["llm_decided"] is False
        assert result2["action"] == ""
        print("[PASS] parse_planning_response rejects observability action (no fallback)")


def test_llm_failure_case():
    def bad_llm(prompt, max_tokens=250):
        return "GARBAGE NOT JSON"

    with patch("inference.call_llm", side_effect=bad_llm):
        from inference import _run_episode_core
        room = WarRoom(seed=42, max_steps=15)
        room.reset()
        rewards_list = _run_episode_core(room)

    total = room.get_total_reward()
    progress = room.get_progress()
    executed = [h["action"] for h in room.action_history]

    print(f"\n--- LLM FAILURE EPISODE ---")
    print(f"Total reward: {total:.3f}")
    print(f"Progress: {progress:.0%}")
    print(f"Executed actions: {executed}")
    print(f"Rewards: {[f'{r:.3f}' for r in rewards_list]}")

    assert progress < 1.0, f"Expected progress < 1.0 on LLM failure, got {progress}"
    assert total <= 0, f"Expected total_reward <= 0 on LLM failure, got {total}"
    assert len(executed) == 0, f"No env steps should execute when LLM always fails, got {executed}"
    print("[PASS] LLM failure -> progress<1.0, reward<=0, no actions executed")


def test_llm_success_case():
    step_actions = [
        "investigate_payment_service",
        "investigate_cache",
        "reboot_redis",
        "investigate_database",
        "flush_db_connections",
        "restart_checkout",
    ]
    agent_map = {
        "investigate_payment_service": "AppOps",
        "investigate_cache": "InfraOps",
        "reboot_redis": "InfraOps",
        "investigate_database": "DatabaseOps",
        "flush_db_connections": "DatabaseOps",
        "restart_checkout": "AppOps",
    }

    room = WarRoom(seed=42, max_steps=15)
    room.reset()

    def good_llm(prompt, max_tokens=250):
        if "ObservabilityOps analyzing" in prompt:
            return json.dumps({
                "root_cause_analysis": "redis cache connection_refused causing payment timeout and checkout error",
                "cascade_chain": "redis failure -> payment timeout -> checkout error_500",
                "confidence": 0.4,
            })
        executed_actions = [h["action"] for h in room.action_history]
        idx = 0
        for a in step_actions:
            if a in executed_actions:
                idx += 1
            else:
                break
        idx = min(idx, len(step_actions) - 1)
        chosen = step_actions[idx]
        remaining = step_actions[idx:]
        return json.dumps({
            "analysis": f"Addressing {chosen}",
            "plan": remaining,
            "next_action": chosen,
            "target_agent": agent_map[chosen],
            "reasoning": f"Following investigation-first approach for {chosen}",
            "confidence": 0.4,
        })

    with patch("inference.call_llm", side_effect=good_llm):
        from inference import _run_episode_core
        rewards_list = _run_episode_core(room)

    total = room.get_total_reward()
    progress = room.get_progress()
    executed = [h["action"] for h in room.action_history]

    print(f"\n--- LLM SUCCESS EPISODE ---")
    print(f"Total reward: {total:.3f}")
    print(f"Progress: {progress:.0%}")
    print(f"Executed actions: {executed}")
    print(f"Rewards: {[f'{r:.3f}' for r in rewards_list]}")

    assert room.is_done(), "Expected episode completion on good LLM"
    assert progress == 1.0, f"Expected progress == 1.0, got {progress}"
    assert total > 0, f"Expected total_reward > 0, got {total}"
    assert len(set(executed)) == len(executed), f"Duplicate actions: {executed}"
    for a in executed:
        assert a not in {"analyze_metrics", "check_alerts", "trace_requests", "correlate_logs"}
    print("[PASS] LLM success -> progress==1.0, reward>0, no duplicates, no obs actions")


def test_dynamic_reward_normalization():
    from inference import _calculate_dynamic_min_reward, _calculate_dynamic_max_reward

    room = WarRoom(seed=42, max_steps=15)
    room.reset()

    min_r = _calculate_dynamic_min_reward(room.env, 15)
    max_r = _calculate_dynamic_max_reward(room.env, 15)

    assert min_r < 0
    assert max_r > 0
    assert max_r > min_r
    print(f"[PASS] Dynamic normalization: min={min_r:.3f}, max={max_r:.3f}")


if __name__ == "__main__":
    test_agent_memory()
    print()
    test_plan_tracker()
    print()
    test_diff_states()
    print()
    test_helpers()
    print()
    test_confidence_default_on_none()
    print()
    test_parse_planning_response_valid()
    print()
    test_parse_planning_response_rejects_invalid()
    print()
    test_llm_failure_case()
    print()
    test_llm_success_case()
    print()
    test_dynamic_reward_normalization()
    print()
    print("=== ALL TESTS PASSED ===")
