"""End to end tests for circuits: deploy, route along connections, collect output."""

import asyncio
import pkgutil
import re
from pathlib import Path

import pytest

import neuron
from neuron import BaseAgent, CircuitDefinition, initialize
from neuron.circuit_designer import CircuitValidator
from neuron.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]


class Upper(BaseAgent):
    def _initialize(self):
        pass

    async def process_message(self, message):
        await self.send_message(message.sender, str(message.content).upper())


class Exclaim(BaseAgent):
    def _initialize(self):
        pass

    async def process_message(self, message):
        await self.send_message(message.sender, f"{message.content}!")


def circuit(connections, roles=None):
    roles = roles or {"a": "INPUT", "b": "OUTPUT"}
    types = {"a": "Upper", "b": "Exclaim", "c": "Exclaim"}
    return CircuitDefinition.create(
        name="test",
        description="test circuit",
        agents={
            name: {"type": types[name], "role": role} for name, role in roles.items()
        },
        connections=connections,
    )


async def run_circuit(definition, inputs, outputs_expected, timeout=3):
    core = initialize()
    core.start()
    try:
        core.agent_manager.register_agent_type(Upper)
        core.agent_manager.register_agent_type(Exclaim)
        circuit_id = await core.circuit_designer.create_and_deploy(definition)
        for item in inputs:
            await core.circuit_designer.send_input(circuit_id, item)
        outputs = [
            await core.circuit_designer.get_output(circuit_id, timeout=timeout)
            for _ in range(outputs_expected)
        ]
        await core.circuit_designer.terminate_circuit(circuit_id)
        return outputs
    finally:
        await core.shutdown_async()


def test_every_module_imports():
    for module in pkgutil.walk_packages(neuron.__path__, "neuron."):
        if module.name.startswith("neuron.model_providers.huggingface"):
            continue  # needs the optional torch/transformers extra
        if ".examples" in module.name:
            continue
        __import__(module.name)


def test_direct_connections_pass_messages_through_the_circuit():
    definition = circuit([{"source": "a", "target": "b", "connection_type": "direct"}])
    [output] = asyncio.run(run_circuit(definition, ["hello"], 1))
    assert output["agent"] == "b"
    assert output["content"] == "HELLO!"


def test_conditional_connection_only_forwards_matching_messages():
    definition = circuit(
        [
            {
                "source": "a",
                "target": "b",
                "connection_type": "conditional",
                "metadata": {"condition_code": "'URGENT' in message.content"},
            }
        ]
    )

    async def scenario():
        outputs = await run_circuit(definition, ["routine", "urgent: help"], 1)
        return outputs

    [output] = asyncio.run(scenario())
    assert output["content"] == "URGENT: HELP!"


def test_transformed_connection_rewrites_content():
    definition = circuit(
        [
            {
                "source": "a",
                "target": "b",
                "connection_type": "transformed",
                "metadata": {"transform_code": "message.content[::-1]"},
            }
        ]
    )
    [output] = asyncio.run(run_circuit(definition, ["abc"], 1))
    assert output["content"] == "CBA!"


def test_fan_out_to_two_outputs():
    definition = circuit(
        [
            {"source": "a", "target": "b", "connection_type": "direct"},
            {"source": "a", "target": "c", "connection_type": "direct"},
        ],
        roles={"a": "INPUT", "b": "OUTPUT", "c": "OUTPUT"},
    )
    outputs = asyncio.run(run_circuit(definition, ["hi"], 2))
    assert sorted(o["agent"] for o in outputs) == ["b", "c"]
    assert {o["content"] for o in outputs} == {"HI!"}


def test_get_output_times_out_when_nothing_arrives():
    definition = circuit(
        [
            {
                "source": "a",
                "target": "b",
                "connection_type": "conditional",
                "metadata": {"condition_code": "False"},
            }
        ]
    )
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(run_circuit(definition, ["dropped"], 1, timeout=0.5))


def test_connectivity_check_does_not_depend_on_agent_order():
    # A chain is connected whichever agent the check starts from.
    definition = CircuitDefinition.create(
        name="chain",
        description="",
        agents={
            "z_out": {"type": "ReflexAgent", "role": "OUTPUT"},
            "a_in": {"type": "ReflexAgent", "role": "INPUT"},
            "m": {"type": "ReflexAgent", "role": "PROCESSOR"},
        },
        connections=[
            {"source": "a_in", "target": "m", "connection_type": "direct"},
            {"source": "m", "target": "z_out", "connection_type": "direct"},
        ],
    )
    available = ["ReflexAgent"]
    for _ in range(20):
        assert CircuitValidator.validate_circuit(definition, available) == []


def test_disconnected_and_invalid_circuits_are_rejected():
    definition = CircuitDefinition.create(
        name="broken",
        description="",
        agents={
            "a": {"type": "ReflexAgent", "role": "INPUT"},
            "b": {"type": "ReflexAgent", "role": "OUTPUT"},
            "lonely": {"type": "ReflexAgent", "role": "PROCESSOR"},
        },
        connections=[
            {"source": "a", "target": "b", "connection_type": "direct"},
            {"source": "a", "target": "ghost", "connection_type": "direct"},
            {"source": "b", "target": "a"},
        ],
    )
    errors = CircuitValidator.validate_circuit(definition, ["ReflexAgent"])
    assert "Circuit has disconnected agents" in errors
    assert "Connection target does not exist: ghost" in errors
    assert "Connection missing type" in errors

    async def deploy():
        core = initialize()
        core.start()
        try:
            await core.circuit_designer.create_circuit(definition)
        finally:
            await core.shutdown_async()

    with pytest.raises(ValidationError):
        asyncio.run(deploy())


def test_readme_quick_start_matches_the_example_file():
    readme = (ROOT / "README.md").read_text()
    example = (ROOT / "examples" / "quickstart.py").read_text()
    blocks = re.findall(r"```python\n(.*?)```", readme, re.S)
    assert any(
        block.strip() in example
        for block in blocks
        if "CustomerSupportCircuit" in block
    )


def test_shutdown_async_leaves_no_pending_tasks():
    # Callers that drive the event loop themselves (instead of asyncio.run)
    # must not be left with framework tasks still pending.
    definition = circuit([{"source": "a", "target": "b", "connection_type": "direct"}])
    loop = asyncio.new_event_loop()
    try:
        [output] = loop.run_until_complete(run_circuit(definition, ["x"], 1))
        assert output["content"] == "X!"
        assert [t for t in asyncio.all_tasks(loop) if not t.done()] == []
    finally:
        loop.close()
