# filename: test_memory_agent.py

import pytest
from memory_agent import MemoryAgent

# A pytest fixture to provide a fresh instance of MemoryAgent for each test function.
# This ensures tests are isolated and don't interfere with each other.
@pytest.fixture
def agent() -> MemoryAgent:
    """Provides a clean MemoryAgent instance for each test."""
    return MemoryAgent()

class TestMemoryAgent:
    """
    Groups all tests for the MemoryAgent to ensure comprehensive coverage
    of its functionality, from basic operations to edge cases.
    """

    # --- 1. Tests for store_data() ---

    def test_store_and_retrieve_simple_value(self, agent):
        """
        Tests the foundational ability to store and retrieve a simple string value.
        This validates the core success path.
        """
        store_response = agent.store_data("user_name", "Alice")
        assert store_response["status"] == "success"
        assert store_response["key"] == "user_name"
        assert store_response["value"] == "Alice"

        retrieve_response = agent.retrieve_data("user_name")
        assert retrieve_response["status"] == "success"
        assert retrieve_response["value"] == "Alice"

    def test_store_and_retrieve_complex_dict(self, agent):
        """
        Tests the agent's ability to handle complex data types (dict) and
        validates the internal JSON serialization/deserialization.
        """
        profile = {"city": "New York", "interests": ["reading", "hiking"]}
        agent.store_data("user_profile", profile)
        
        # Verify internal storage is a JSON string
        assert isinstance(agent._memory_store["user_profile"], str)

        retrieve_response = agent.retrieve_data("user_profile")
        assert retrieve_response["status"] == "success"
        assert retrieve_response["value"] == profile  # Should be deserialized back to a dict

    def test_store_and_retrieve_complex_list(self, agent):
        """
        Tests the agent's ability to handle another complex data type (list)
        and validates the JSON transformation.
        """
        tasks = ["buy milk", "walk the dog", {"priority": "high", "task": "finish report"}]
        agent.store_data("todo_list", tasks)
        
        retrieve_response = agent.retrieve_data("todo_list")
        assert retrieve_response["status"] == "success"
        assert retrieve_response["value"] == tasks

    def test_store_overwrite_existing_key(self, agent):
        """
        Ensures that storing data with an existing key correctly overwrites the old value.
        """
        agent.store_data("status", "online")
        agent.store_data("status", "offline")
        retrieve_response = agent.retrieve_data("status")
        assert retrieve_response["status"] == "success"
        assert retrieve_response["value"] == "offline"
        
    @pytest.mark.parametrize("key", [None, 123, ""])
    def test_store_data_with_invalid_key(self, agent, key):
        """
        Tests that the agent rejects invalid keys (non-string or empty string),
        ensuring input validation is working as expected.
        """
        response = agent.store_data(key, "some_value")
        assert response["status"] == "error"
        assert "Key must be a non-empty string" in response["message"]

    def test_store_data_with_non_serializable_value(self, agent):
        """
        Tests the agent's error handling when trying to store a value
        that cannot be converted to JSON.
        """
        # A raw object is not JSON serializable
        response = agent.store_data("invalid_value", object())
        assert response["status"] == "error"
        assert "Value is not JSON serializable" in response["message"]

    # --- 2. Tests for retrieve_data() ---

    def test_retrieve_non_existent_key(self, agent):
        """
        Tests that the agent correctly reports when a key is not found.
        """
        response = agent.retrieve_data("non_existent_key")
        assert response["status"] == "not_found"
        assert "not found" in response["message"]

    @pytest.mark.parametrize("key", [None, 456, ""])
    def test_retrieve_data_with_invalid_key(self, agent, key):
        """
        Ensures input validation for the retrieval method is working correctly.
        """
        response = agent.retrieve_data(key)
        assert response["status"] == "error"
        assert "Key must be a non-empty string" in response["message"]

    def test_retrieve_data_stored_as_malformed_json_string(self, agent):
        """
        Edge case: Tests retrieval of a string that looks like JSON but is invalid.
        The agent should return the raw string without crashing.
        """
        malformed_json = '{"key": "value",}' # Extra comma makes it invalid
        agent._memory_store["bad_json"] = malformed_json
        
        response = agent.retrieve_data("bad_json")
        assert response["status"] == "success"
        assert response["value"] == malformed_json
        assert "Stored value was a string but not valid JSON" in response["message"]


    # --- 3. Tests for delete_data() ---

    def test_delete_existing_key(self, agent):
        """
        Tests the full lifecycle of storing then deleting a key, ensuring it's truly gone.
        """
        agent.store_data("to_be_deleted", "temporary_data")
        
        # Verify it's there
        assert agent.retrieve_data("to_be_deleted")["status"] == "success"
        
        # Delete it
        delete_response = agent.delete_data("to_be_deleted")
        assert delete_response["status"] == "success"
        
        # Verify it's gone
        retrieve_after_delete = agent.retrieve_data("to_be_deleted")
        assert retrieve_after_delete["status"] == "not_found"


    def test_delete_non_existent_key(self, agent):
        """
        Tests that attempting to delete a key that doesn't exist returns the correct
        'not_found' status without errors.
        """
        response = agent.delete_data("non_existent_key_for_delete")
        assert response["status"] == "not_found"
        assert "not found for deletion" in response["message"]

    @pytest.mark.parametrize("key", [None, 789, ""])
    def test_delete_data_with_invalid_key(self, agent, key):
        """
        Ensures input validation for the delete method is working correctly.
        """
        response = agent.delete_data(key)
        assert response["status"] == "error"
        assert "Key must be a non-empty string" in response["message"]


    # --- 4. Integration & Lifecycle Simulation ---
    
    def test_full_agent_lifecycle(self, agent):
        """
        A basic integration test simulating a typical operational sequence:
        1. Store initial data.
        2. Retrieve and verify.
        3. Store new data (overwrite).
        4. Retrieve and verify updated data.
        5. Delete the data.
        6. Verify the data is gone.
        This ensures methods work together seamlessly.
        """
        # 1. Store
        agent.store_data("session_id", "xyz-123")
        
        # 2. Retrieve
        assert agent.retrieve_data("session_id")["value"] == "xyz-123"
        
        # 3. Overwrite
        agent.store_data("session_id", "abc-456")
        
        # 4. Retrieve again
        assert agent.retrieve_data("session_id")["value"] == "abc-456"
        
        # 5. Delete
        assert agent.delete_data("session_id")["status"] == "success"
        
        # 6. Verify deletion
        assert agent.retrieve_data("session_id")["status"] == "not_found"


