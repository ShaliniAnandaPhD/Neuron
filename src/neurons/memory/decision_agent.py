# filename: decision_agent.py

import random

class DecisionAgent:
    """
    A simple Decision Agent that makes a choice from a list of options
    based on a given context or criteria.
    """
    def __init__(self):
        """Initializes the DecisionAgent."""
        # This could be expanded to include rules, models, or memory access.
        pass

    def make_decision(self, context: str, options: list) -> dict:
        """
        Makes a decision based on the provided context and options.

        :param context: A string describing the situation for the decision.
        :param options: A list of possible choices.
        :return: A dictionary indicating the chosen option or an error.
        """
        print(f"DecisionAgent: Context is '{context}'")
        if not isinstance(options, list) or not options:
            return {"status": "error", "message": "Options must be a non-empty list."}

        # A simple, placeholder logic: randomly choose an option.
        # This would be replaced with more complex logic (e.g., a model call, rule engine).
        chosen_option = random.choice(options)
        print(f"DecisionAgent: Chose '{chosen_option}' from {options}")

        return {
            "status": "success",
            "decision": chosen_option,
            "context": context,
            "options_considered": options
        }

# Example usage
if __name__ == "__main__":
    agent = DecisionAgent()

    print("\n--- Making a Decision ---")
    decision_context = "User wants to know the weather forecast."
    possible_actions = ["call_weather_api", "ask_for_location", "admit_i_cannot_help"]
    
    result = agent.make_decision(decision_context, possible_actions)
    print(f"Final Result: {result}")

    print("\n--- Handling Invalid Input ---")
    error_result = agent.make_decision("No options provided", [])
    print(f"Error Result: {error_result}")
