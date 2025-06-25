# filename: test_memory_agent.py

import pytest
from memory_agent import MemoryAgent # Import the agent class

# --- Setup fixture for tests ---
# A pytest fixture to provide a fresh MemoryAgent instance for each test.
# This ensures tests are isolated and don't interfere with each other's state.
@pytest.fixture
def memory_agent_instance():
    """Provides a fresh MemoryAgent instance for each test."""
    return MemoryAgent()

# --- Unit Tests: Verify individual agent logic ---

def test_store_and_retrieve_simple_data(memory_agent_instance):
    """
    Unit test: Verifies that a simple string value can be stored and retrieved correctly.
    This checks the core functionality of data persistence within the agent.
    """
    key = "test_key_str"
    value = "test_value"
    # Store operation
    store_result = memory_agent_instance.store_data(key, value)
    assert store_result["status"] == "success"
    assert store_result["key"] == key
    assert store_result["value"] == value

    # Retrieve operation
    retrieve_result = memory_agent_instance.retrieve_data(key)
    assert retrieve_result["status"] == "success"
    assert retrieve_result["key"] == key
    assert retrieve_result["value"] == value

def test_store_and_retrieve_complex_data(memory_agent_instance):
    """
    Unit test: Verifies that a dictionary (complex data) can be stored and retrieved.
    This tests the agent's ability to handle more structured inputs and outputs,
    including potential serialization/deserialization.
    """
    key = "test_key_dict"
    value = {"data1": 123, "data2": [4, 5, 6], "nested": {"a": "b"}}
    store_result = memory_agent_instance.store_data(key, value)
    assert store_result["status"] == "success"
    assert store_result["value"] == value # Check that the original value is reflected

    retrieve_result = memory_agent_instance.retrieve_data(key)
    assert retrieve_result["status"] == "success"
    assert retrieve_result["value"] == value # Ensure retrieved value matches original

def test_retrieve_non_existent_key(memory_agent_instance):
    """
    Unit test: Checks behavior when trying to retrieve data for a key that does not exist.
    Expected: "not_found" status.
    """
    result = memory_agent_instance.retrieve_data("non_existent")
    assert result["status"] == "not_found"
    assert "not found" in result["message"]

def test_delete_existing_key(memory_agent_instance):
    """
    Unit test: Ensures that an existing key can be successfully deleted.
    It verifies both the deletion operation and that the key is no longer retrievable.
    """
    key = "key_to_delete"
    memory_agent_instance.store_data(key, "some_data")
    delete_result = memory_agent_instance.delete_data(key)
    assert delete_result["status"] == "success"
    assert f"Key '{key}' deleted successfully." in delete_result["message"]

    # Verify it's actually deleted
    retrieve_result_after_delete = memory_agent_instance.retrieve_data(key)
    assert retrieve_result_after_delete["status"] == "not_found"

def test_delete_non_existent_key(memory_agent_instance):
    """
    Unit test: Checks behavior when attempting to delete a non-existent key.
    Expected: "not_found" status.
    """
    result = memory_agent_instance.delete_data("non_existent_for_delete")
    assert result["status"] == "not_found"
    assert "not found for deletion" in result["message"]

def test_store_invalid_key(memory_agent_instance):
    """
    Unit test: Tests input validation for the 'key' argument in store_data.
    Keys should be non-empty strings.
    """
    result_empty = memory_agent_instance.store_data("", "value")
    assert result_empty["status"] == "error"
    assert "Key must be a non-empty string." in result_empty["message"]

    result_non_str = memory_agent_instance.store_data(123, "value")
    assert result_non_str["status"] == "error"
    assert "Key must be a non-empty string." in result_non_str["message"]

def test_retrieve_invalid_key(memory_agent_instance):
    """
    Unit test: Tests input validation for the 'key' argument in retrieve_data.
    Keys should be non-empty strings.
    """
    result_empty = memory_agent_instance.retrieve_data("")
    assert result_empty["status"] == "error"
    assert "Key must be a non-empty string." in result_empty["message"]

    result_non_str = memory_agent_instance.retrieve_data(None)
    assert result_non_str["status"] == "error"
    assert "Key must be a non-empty string." in result_non_str["message"]

def test_store_non_serializable_value(memory_agent_instance):
    """
    Unit test: Verifies error handling when trying to store a value that cannot be JSON serialized.
    """
    class NonSerializable:
        pass
    obj = NonSerializable()
    result = memory_agent_instance.store_data("non_serializable_key", obj)
    assert result["status"] == "error"
    assert "Value is not JSON serializable." in result["message"]

# --- Integration Tests: Simulate data flow between agent operations ---

def test_full_memory_lifecycle_integration(memory_agent_instance):
    """
    Integration test: Simulates a full lifecycle of data (store -> retrieve -> delete -> retrieve).
    This checks the seamless flow of data between different operations of the agent,
    ensuring that the inputs and outputs work together as expected.
    """
    key = "user_settings"
    initial_settings = {"theme": "dark", "notifications": True}

    # 1. Store data (Input to store_data, Output from store_data)
    store_result = memory_agent_instance.store_data(key, initial_settings)
    assert store_result["status"] == "success"
    assert store_result["value"] == initial_settings

    # 2. Retrieve data (Input to retrieve_data, Output from retrieve_data)
    retrieve_result_1 = memory_agent_instance.retrieve_data(key)
    assert retrieve_result_1["status"] == "success"
    assert retrieve_result_1["value"] == initial_settings

    # 3. Update data (Store again to simulate an update)
    updated_settings = {"theme": "light", "notifications": False, "language": "en"}
    update_result = memory_agent_instance.store_data(key, updated_settings)
    assert update_result["status"] == "success"
    assert update_result["value"] == updated_settings

    # 4. Retrieve updated data
    retrieve_result_2 = memory_agent_instance.retrieve_data(key)
    assert retrieve_result_2["status"] == "success"
    assert retrieve_result_2["value"] == updated_settings

    # 5. Delete data (Input to delete_data, Output from delete_data)
    delete_result = memory_agent_instance.delete_data(key)
    assert delete_result["status"] == "success"

    # 6. Attempt to retrieve deleted data (should fail - ensures data flow integrity)
    retrieve_result_3 = memory_agent_instance.retrieve_data(key)
    assert retrieve_result_3["status"] == "not_found"

