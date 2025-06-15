#!/usr/bin/env python3
import asyncio
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import AdvancedNeuronAgent, AgentMessage, BehaviorTrait, BehaviorMode

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_agent_initialization():
    agent = AdvancedNeuronAgent()
    assert agent.agent_id is not None
    assert agent.version == "2.0"
    assert agent.is_running == False
    print(f"✅ Agent initialized with ID: {agent.agent_id}")

@pytest.mark.asyncio
async def test_agent_start_stop():
    agent = AdvancedNeuronAgent()
    start_result = await agent.start()
    assert start_result["status"] == "started"
    assert agent.is_running == True
    print("✅ Agent start/stop test passed")

    stop_result = await agent.stop()
    assert stop_result["status"] == "stopped"
    assert agent.is_running == False

@pytest.mark.asyncio
async def test_memory_operations():
    agent = AdvancedNeuronAgent()
    await agent.start()

    store_msg = AgentMessage(
        sender="test",
        recipient=agent.agent_id,
        msg_type="memory_store",
        payload={"key": "test_data", "data": {"value": "test"}, "confidence": 0.8}
    )
    store_result = await agent.process_message(store_msg)
    assert store_result["status"] == "success"
    print("✅ Memory operations test passed")

    await agent.stop()

@pytest.mark.asyncio
async def test_reasoning_operations():
    agent = AdvancedNeuronAgent()
    await agent.start()

    analyze_msg = AgentMessage(
        sender="test",
        recipient=agent.agent_id,
        msg_type="reasoning_analyze",
        payload={"data": [1, 2, 3, 4, 5]}
    )
    analyze_result = await agent.process_message(analyze_msg)
    assert analyze_result["status"] == "success"
    print("✅ Reasoning operations test passed")

    await agent.stop()

@pytest.mark.asyncio
async def test_reliability_operations():
    agent = AdvancedNeuronAgent()
    await agent.start()

    health_msg = AgentMessage(
        sender="test",
        recipient=agent.agent_id,
        msg_type="reliability_health_check",
        payload={}
    )
    health_result = await agent.process_message(health_msg)
    assert health_result["status"] == "success"
    print("✅ Reliability operations test passed")

    await agent.stop()

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", os.path.abspath(__file__)]))
