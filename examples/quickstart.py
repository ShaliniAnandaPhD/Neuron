"""
Neuron quick start: a three-agent circuit for customer support.

intake → checker → responder. The intake agent tags a message with simple
sentiment signals, the checker flags mixed signals ("I love it but it's
broken"), and the responder turns that into a clarifying reply.

    pip install -e .
    python examples/quickstart.py
"""

import asyncio

from neuron import BaseAgent, CircuitDefinition, initialize


class Intake(BaseAgent):
    """Tags a support message with positive and negative signals."""

    def _initialize(self):
        pass

    async def process_message(self, message):
        text = message.content["message"].lower()
        signals = {
            "positive": any(word in text for word in ("love", "great", "thanks")),
            "negative": any(word in text for word in ("broken", "refund", "angry")),
        }
        await self.send_message(message.sender, {**message.content, "signals": signals})


class ContradictionCheck(BaseAgent):
    """Flags messages that are positive and negative at the same time."""

    def _initialize(self):
        pass

    async def process_message(self, message):
        signals = message.content["signals"]
        mixed = signals["positive"] and signals["negative"]
        await self.send_message(
            message.sender, {**message.content, "contradiction": mixed}
        )


class Responder(BaseAgent):
    """Writes the reply."""

    def _initialize(self):
        pass

    async def process_message(self, message):
        if message.content["contradiction"]:
            reply = "Sounds like you like it but it isn't working. Repair or refund?"
        else:
            reply = "Thanks, we're on it."
        await self.send_message(message.sender, {"reply": reply})


async def main():
    core = initialize()
    core.start()  # components run as tasks on this event loop
    for agent_type in (Intake, ContradictionCheck, Responder):
        core.agent_manager.register_agent_type(agent_type)

    circuit = CircuitDefinition.create(
        name="CustomerSupportCircuit",
        description="Detects mixed signals and asks a clarifying question",
        agents={
            "intake": {"type": "Intake", "role": "INPUT"},
            "checker": {"type": "ContradictionCheck", "role": "PROCESSOR"},
            "responder": {"type": "Responder", "role": "OUTPUT"},
        },
        connections=[
            {"source": "intake", "target": "checker", "connection_type": "direct"},
            {"source": "checker", "target": "responder", "connection_type": "direct"},
        ],
    )
    circuit_id = await core.circuit_designer.create_and_deploy(circuit)

    message = "I love this product but it's completely broken and I want a refund"
    await core.circuit_designer.send_input(circuit_id, {"message": message})
    output = await core.circuit_designer.get_output(circuit_id, timeout=5)
    print(f"{output['agent']}: {output['content']['reply']}")

    await core.circuit_designer.terminate_circuit(circuit_id)
    core.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
