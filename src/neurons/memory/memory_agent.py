# filename: memory_agent.py

import json

class MemoryAgent:
    """
    A simple Memory Agent that stores and retrieves key-value pairs.
    It simulates a basic memory component in a larger agent system.
    """
    def __init__(self):
        # Internal storage for memory, mimicking a simple database or cache.
        self._memory_store = {}

    def store_data(self, key: str, value: any) -> dict:
        """
        Stores a key-value pair in the agent's memory.
        :param key: The identifier for the data.
        :param value: The data to be stored.
        :return: A dictionary indicating success and the stored data.
        """
        if not isinstance(key, str) or not key:
            # Basic validation for the key
            return {"status": "error", "message": "Key must be a non-empty string."}
        try:
            # Attempt to serialize complex objects to JSON for storage,
            # simulating data transformation for persistence.
            stored_value = json.dumps(value) if isinstance(value, (dict, list)) else value
            self._memory_store[key] = stored_value
            print(f"MemoryAgent: Stored '{key}': {stored_value}")
            return {"status": "success", "key": key, "value": value}
        except TypeError:
            return {"status": "error", "message": "Value is not JSON serializable."}
        except Exception as e:
            return {"status": "error", "message": f"An unexpected error occurred: {e}"}


    def retrieve_data(self, key: str) -> dict:
        """
        Retrieves data associated with a given key from the agent's memory.
        :param key: The identifier of the data to retrieve.
        :return: A dictionary indicating success and the retrieved data, or an error.
        """
        if not isinstance(key, str) or not key:
            return {"status": "error", "message": "Key must be a non-empty string."}

        if key in self._memory_store:
            stored_value = self._memory_store[key]
            try:
                # Attempt to deserialize if the stored value was JSON,
                # simulating data transformation on retrieval.
                retrieved_value = json.loads(stored_value) if isinstance(stored_value, str) and (stored_value.startswith('{') or stored_value.startswith('[')) else stored_value
                print(f"MemoryAgent: Retrieved '{key}': {retrieved_value}")
                return {"status": "success", "key": key, "value": retrieved_value}
            except json.JSONDecodeError:
                # If it looks like JSON but isn't valid, return it as a string
                return {"status": "success", "key": key, "value": stored_value, "message": "Stored value was a string but not valid JSON."}
            except Exception as e:
                return {"status": "error", "message": f"An unexpected error occurred during retrieval: {e}"}
        else:
            print(f"MemoryAgent: Key '{key}' not found.")
            return {"status": "not_found", "message": f"Key '{key}' not found."}

    def delete_data(self, key: str) -> dict:
        """
        Deletes data associated with a given key from the agent's memory.
        :param key: The identifier of the data to delete.
        :return: A dictionary indicating success or an error.
        """
        if not isinstance(key, str) or not key:
            return {"status": "error", "message": "Key must be a non-empty string."}

        if key in self._memory_store:
            del self._memory_store[key]
            print(f"MemoryAgent: Deleted '{key}'.")
            return {"status": "success", "message": f"Key '{key}' deleted successfully."}
        else:
            print(f"MemoryAgent: Key '{key}' not found for deletion.")
            return {"status": "not_found", "message": f"Key '{key}' not found for deletion."}


# Example usage (can be removed if only using for testing, or put in a main guard)
if __name__ == "__main__":
    agent = MemoryAgent()

    # Store some data
    print("\n--- Storing Data ---")
    agent.store_data("user_name", "Alice")
    agent.store_data("user_age", 30)
    agent.store_data("user_profile", {"city": "New York", "interests": ["reading", "hiking"]})
    agent.store_data("invalid_value", object()) # This should fail

    # Retrieve data
    print("\n--- Retrieving Data ---")
    print(agent.retrieve_data("user_name"))
    print(agent.retrieve_data("user_profile"))
    print(agent.retrieve_data("non_existent_key"))

    # Delete data
    print("\n--- Deleting Data ---")
    agent.delete_data("user_age")
    print(agent.retrieve_data("user_age")) # Should be not found
    agent.delete_data("non_existent_key_for_delete") # Should report not found


