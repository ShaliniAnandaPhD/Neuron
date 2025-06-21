#!/usr/bin/env python3
import asyncio
import sys
import os
import pytest
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import AdvancedNeuronSystem, AgentMessage

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_system_initialization():
    system = AdvancedNeuronSystem()
    assert system.industry is not None
    assert system.use_case is not None
    assert system.complexity is not None
    assert system.is_running == False
    print(f"✅ System initialized for {system.industry}")

@pytest.mark.asyncio
async def test_system_start_stop():
    system = AdvancedNeuronSystem()
    
    start_result = await system.start()
    assert start_result["status"] == "started"
    assert system.is_running == True
    print("✅ System start test passed")

    stop_result = await system.stop()
    assert stop_result["status"] == "stopped"
    assert system.is_running == False
    print("✅ System stop test passed")

@pytest.mark.asyncio
async def test_memory_operations():
    system = AdvancedNeuronSystem()
    await system.start()

    # Test store
    store_request = {
        "type": "memory_store", 
        "payload": {"key": "test_key", "data": {"value": "test_data"}, "confidence": 0.8}
    }
    store_result = await system.process_request(store_request)
    assert store_result["status"] == "success"
    print("✅ Memory store test passed")

    # Test retrieve
    retrieve_request = {
        "type": "memory_retrieve",
        "payload": {"key": "test_key"}
    }
    retrieve_result = await system.process_request(retrieve_request)
    assert retrieve_result["status"] == "success"
    assert retrieve_result["data"]["value"] == "test_data"
    print("✅ Memory retrieve test passed")

    # Test search
    search_request = {
        "type": "memory_search",
        "payload": {"query": "test", "limit": 5}
    }
    search_result = await system.process_request(search_request)
    assert search_result["status"] == "success"
    print("✅ Memory search test passed")

    await system.stop()

@pytest.mark.asyncio
async def test_reasoning_operations():
    system = AdvancedNeuronSystem()
    await system.start()

    # Test analyze
    analyze_request = {
        "type": "reasoning_analyze",
        "payload": {"data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
    }
    analyze_result = await system.process_request(analyze_request)
    assert analyze_result["status"] == "success"
    assert "patterns" in analyze_result
    assert "insights" in analyze_result
    print("✅ Reasoning analyze test passed")

    # Test solve
    solve_request = {
        "type": "reasoning_solve",
        "payload": {"problem": "How to optimize system performance", "constraints": ["limited resources"]}
    }
    solve_result = await system.process_request(solve_request)
    assert solve_result["status"] == "success"
    assert "solutions" in solve_result
    print("✅ Reasoning solve test passed")

    # Test predict
    predict_request = {
        "type": "reasoning_predict",
        "payload": {"data": [10, 15, 20, 25, 30], "horizon": 2}
    }
    predict_result = await system.process_request(predict_request)
    assert predict_result["status"] == "success"
    assert "prediction" in predict_result
    print("✅ Reasoning predict test passed")

    await system.stop()

@pytest.mark.asyncio
async def test_reliability_operations():
    system = AdvancedNeuronSystem()
    await system.start()

    # Test health check
    health_request = {
        "type": "reliability_health_check",
        "payload": {}
    }
    health_result = await system.process_request(health_request)
    assert health_result["status"] == "success"
    assert "health_status" in health_result
    assert "health_score" in health_result
    print("✅ Reliability health check test passed")

    # Test compliance audit
    compliance_request = {
        "type": "reliability_compliance_audit",
        "payload": {}
    }
    compliance_result = await system.process_request(compliance_request)
    assert compliance_result["status"] == "success"
    assert "overall_compliance" in compliance_result
    print("✅ Reliability compliance test passed")

    # Test metrics
    metrics_request = {
        "type": "reliability_metrics",
        "payload": {}
    }
    metrics_result = await system.process_request(metrics_request)
    assert metrics_result["status"] == "success"
    assert "health_metrics" in metrics_result
    print("✅ Reliability metrics test passed")

    await system.stop()

@pytest.mark.asyncio
async def test_behavior_profile():
    system = AdvancedNeuronSystem()
    
    # Check behavior profile is properly configured
    profile = system.behavior_profile
    assert profile.traits is not None
    assert len(profile.traits) > 0
    print(f"✅ Behavior profile test passed: {profile.mode.name}")

@pytest.mark.asyncio
async def test_end_to_end_workflow():
    system = AdvancedNeuronSystem()
    await system.start()

    # Store some data
    await system.process_request({
        "type": "memory_store",
        "payload": {"key": "workflow_data", "data": {"workflow": "test"}}
    })

    # Analyze the data
    analyze_result = await system.process_request({
        "type": "reasoning_analyze",
        "payload": {"data": [1, 2, 3, 4, 5]}
    })

    # Check health
    health_result = await system.process_request({
        "type": "reliability_health_check",
        "payload": {}
    })

    # Verify all operations succeeded
    assert analyze_result["status"] == "success"
    assert health_result["status"] == "success"
    print("✅ End-to-end workflow test passed")

    await system.stop()

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", os.path.abspath(__file__)]))
