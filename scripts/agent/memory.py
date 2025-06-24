# scripts/agent/memory.py

from collections import deque

class SimpleMemory:
    """
    A basic, short-term memory system for the agent.
    It uses a deque to store a fixed number of recent interactions.
    """
    def __init__(self, max_history=10):
        print(f"🧠 Initializing SimpleMemory with a history size of {max_history}.")
        self.history = deque(maxlen=max_history)

    def store_interaction(self, user_input, agent_response):
        """Stores a user input and the agent's response."""
        interaction = {"user": user_input, "agent": agent_response}
        self.history.append(interaction)
        print(f"🧠 Memory: Stored interaction -> {interaction}")

    def recall_recent(self, num_interactions=3):
        """Recalls the last few interactions."""
        return list(self.history)[-num_interactions:]

    def get_full_history(self):
        """Returns the entire interaction history."""
        return list(self.history)
