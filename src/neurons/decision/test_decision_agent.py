# filename: test_decision_agent.py

import pytest
from decision_agent import DecisionAgent

@pytest.fixture
def agent() -> DecisionAgent:
    """Provides a clean DecisionAgent instance for each test."""
    return DecisionAgent()

class TestDecisionAgent:
    """
    Unit tests for the DecisionAgent to ensure its core logic is sound.
    """

    def test_make_decision_with_valid_options(self, agent):
        """
        Tests that the agent can make a decision from a valid list of options
        and that the output format is correct.
        """
        context = "test_context"
        options = ["option_a", "option_b", "option_c"]
        
        result = agent.make_decision(context, options)
        
        assert result["status"] == "success"
        assert result["context"] == context
        assert result["decision"] in options
        assert result["options_considered"] == options

    def test_make_decision_with_no_options(self, agent):
        """
        Tests that the agent returns an error when provided with an empty
        list of options, ensuring input validation works.
        """
        result = agent.make_decision("any_context", [])
        
        assert result["status"] == "error"
        assert "Options must be a non-empty list" in result["message"]

    def test_make_decision_with_invalid_options_type(self, agent):
        """
        Tests that the agent returns an error if the options parameter is
        not a list.
        """
        result = agent.make_decision("any_context", "not_a_list")
        
        assert result["status"] == "error"
        assert "Options must be a non-empty list" in result["message"]

    def test_make_decision_with_single_option(self, agent):
        """
        Tests the edge case where only one option is available. The agent
        must choose that single option.
        """
        context = "single_choice_scenario"
        options = ["the_only_choice"]
        
        result = agent.make_decision(context, options)
        
        assert result["status"] == "success"
        assert result["decision"] == "the_only_choice"

