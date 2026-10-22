#!/usr/bin/env python3
"""Tests for the Neuron industry agent.

Every test runs against every use case in use_cases/.
"""

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from add_use_case import use_case_key  # noqa: E402
from neuron_agent import (  # noqa: E402
    BEHAVIOR_PROFILES,
    INDUSTRY_COMPLIANCE,
    USE_CASES_DIR,
    NeuronSystem,
    available_use_cases,
    load_use_case,
    resolve_use_case_key,
)

USE_CASES = available_use_cases()


def run(coro):
    return asyncio.run(coro)


async def started(key, profile=None):
    system = NeuronSystem(load_use_case(key), profile=profile)
    await system.start()
    return system


# --- configuration ---------------------------------------------------------


def test_use_cases_exist():
    assert USE_CASES, f"no use case files in {USE_CASES_DIR}"


@pytest.mark.parametrize("key", USE_CASES)
def test_use_case_config_is_valid(key):
    raw = json.loads((USE_CASES_DIR / f"{key}.json").read_text())
    assert set(raw) == {
        "industry",
        "use_case",
        "description",
        "behavior_profile",
        "compliance_standards",
    }

    use_case = load_use_case(key)
    assert use_case.industry in INDUSTRY_COMPLIANCE
    assert use_case.name and use_case.description
    assert use_case.behavior_profile in BEHAVIOR_PROFILES
    assert use_case.compliance_standards
    # The file name is derived from the industry and use case,
    # so the two cannot drift apart.
    assert key == use_case_key(use_case.industry, use_case.name)


def test_use_case_names_are_unique():
    names = [load_use_case(key).name for key in USE_CASES]
    assert len(names) == len(set(names))


def test_industry_shortcut_resolves_when_unambiguous():
    for key in USE_CASES:
        industry = key.split("-", 1)[0]
        if sum(k.split("-", 1)[0] == industry for k in USE_CASES) == 1:
            assert resolve_use_case_key(industry) == key


def test_unknown_use_case_is_rejected():
    with pytest.raises(ValueError):
        load_use_case("no-such-use-case")


def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError):
        NeuronSystem(load_use_case(USE_CASES[0]), profile="team player")


# --- lifecycle and routing --------------------------------------------------


@pytest.mark.parametrize("key", USE_CASES)
def test_start_and_stop(key):
    async def scenario():
        system = NeuronSystem(load_use_case(key))
        assert not system.is_running
        assert (await system.start())["status"] == "started"
        assert system.is_running
        assert (await system.stop())["status"] == "stopped"
        assert not system.is_running

    run(scenario())


def test_requests_rejected_when_stopped():
    async def scenario():
        system = NeuronSystem(load_use_case(USE_CASES[0]))
        result = await system.process_request(
            {"type": "memory_store", "payload": {"key": "a", "data": 1}}
        )
        assert result["status"] == "error"

    run(scenario())


def test_unknown_request_type():
    async def scenario():
        system = await started(USE_CASES[0])
        for request_type in ["", "memory", "telepathy_read", "memory_delete"]:
            result = await system.process_request({"type": request_type})
            assert result["status"] == "error", request_type

    run(scenario())


# --- memory -----------------------------------------------------------------


@pytest.mark.parametrize("key", USE_CASES)
def test_memory_store_retrieve_search(key):
    async def scenario():
        system = await started(key)
        stored = await system.process_request(
            {
                "type": "memory_store",
                "payload": {
                    "key": "case_1",
                    "data": {"note": "flagged for review"},
                    "confidence": 0.8,
                },
            }
        )
        assert stored["status"] == "success"

        retrieved = await system.process_request(
            {"type": "memory_retrieve", "payload": {"key": "case_1"}}
        )
        assert retrieved["status"] == "success"
        assert retrieved["data"] == {"note": "flagged for review"}

        found = await system.process_request(
            {"type": "memory_search", "payload": {"query": "FLAGGED"}}
        )
        assert found["count"] == 1

        missing = await system.process_request(
            {"type": "memory_retrieve", "payload": {"key": "nope"}}
        )
        assert missing["status"] == "not_found"

    run(scenario())


def test_memory_accepts_falsy_data():
    async def scenario():
        system = await started(USE_CASES[0])
        result = await system.process_request(
            {"type": "memory_store", "payload": {"key": "zero", "data": 0}}
        )
        assert result["status"] == "success"

    run(scenario())


# --- reasoning --------------------------------------------------------------


@pytest.mark.parametrize("key", USE_CASES)
def test_reasoning_analyze_and_predict(key):
    async def scenario():
        system = await started(key)
        analysis = await system.process_request(
            {"type": "reasoning_analyze", "payload": {"data": list(range(10))}}
        )
        assert analysis["status"] == "success"
        assert analysis["patterns"] and analysis["insights"]

        prediction = await system.process_request(
            {
                "type": "reasoning_predict",
                "payload": {"data": [10, 15, 20, 25, 30], "horizon": 2},
            }
        )
        assert prediction["status"] == "success"
        assert prediction["prediction"] == 40

    run(scenario())


@pytest.mark.parametrize("profile", sorted(BEHAVIOR_PROFILES))
def test_every_profile_proposes_a_solution(profile):
    async def scenario():
        system = await started(USE_CASES[0], profile=profile)
        result = await system.process_request(
            {"type": "reasoning_solve", "payload": {"problem": "Reduce backlog"}}
        )
        assert result["status"] == "success"
        assert result["solution_count"] >= 1
        assert result["recommended"] in result["solutions"]

    run(scenario())


def test_predict_handles_zeros_and_single_values():
    async def scenario():
        system = await started(USE_CASES[0])
        zeros = await system.process_request(
            {"type": "reasoning_predict", "payload": {"data": [0, 0, 0]}}
        )
        assert zeros["status"] == "success" and zeros["prediction"] == 0
        single = await system.process_request(
            {"type": "reasoning_predict", "payload": {"data": [7]}}
        )
        assert single["status"] == "success" and single["prediction"] == 7

    run(scenario())


# --- reliability ------------------------------------------------------------


@pytest.mark.parametrize("key", USE_CASES)
def test_compliance_lists_the_use_case_standards(key):
    async def scenario():
        system = await started(key)
        result = await system.process_request({"type": "reliability_compliance"})
        assert result["status"] == "success"
        assert result["standards"] == load_use_case(key).compliance_standards
        assert result["verified"] is False

    run(scenario())


def test_health_reflects_real_errors():
    async def scenario():
        system = await started(USE_CASES[0])
        healthy = await system.process_request({"type": "reliability_health_check"})
        assert healthy["health_status"] == "healthy"

        for _ in range(3):
            await system.process_request(
                {"type": "memory_store", "payload": {}}
            )  # missing key and data

        after = await system.process_request({"type": "reliability_health_check"})
        assert after["metrics"]["errors"] == 3
        assert after["health_status"] == "critical"

    run(scenario())


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", os.path.abspath(__file__)]))
