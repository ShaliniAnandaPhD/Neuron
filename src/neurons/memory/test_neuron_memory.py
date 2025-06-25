# test_neuron_memory.py
# This script simulates and tests the Neuron memory system.

import sys
import os
import hashlib

# In a real application, this would be a more sophisticated storage mechanism,
# like a database or a proper file-based store. For this example, we'll use
# simple text files to simulate persistence.
MEMORY_PATH = {
    "episodic": "episodic_memory.txt",
    "semantic": "semantic_memory.txt",
    "working": "working_memory.txt",
}

def calculate_hash(content):
    """Calculates the SHA256 hash of a string."""
    return hashlib.sha256(content.encode()).hexdigest()

def add_memory(memory_type, content):
    """Simulates 'neuron memory add'."""
    if memory_type not in MEMORY_PATH:
        print(f"Error: Unknown memory type '{memory_type}'")
        sys.exit(1)
    
    with open(MEMORY_PATH[memory_type], "a") as f:
        f.write(content + "\n")
    print(f"✅ Successfully added to {memory_type} memory.")

def view_memory(memory_type, expected_content):
    """Simulates 'neuron memory view' and checks for content."""
    if memory_type not in MEMORY_PATH:
        print(f"Error: Unknown memory type '{memory_type}'")
        sys.exit(1)

    if not os.path.exists(MEMORY_PATH[memory_type]):
        print(f"❌ Error: Memory file for {memory_type} not found.")
        sys.exit(1)

    with open(MEMORY_PATH[memory_type], "r") as f:
        memories = [line.strip() for line in f.readlines()]
    
    if expected_content in memories:
        print(f"✅ Successfully found '{expected_content}' in {memory_type} memory.")
    else:
        print(f"❌ Error: Did not find '{expected_content}' in {memory_type} memory.")
        sys.exit(1)

def clear_memory(memory_type):
    """Simulates 'neuron memory clear'."""
    if memory_type not in MEMORY_PATH:
        print(f"Error: Unknown memory type '{memory_type}'")
        sys.exit(1)

    if os.path.exists(MEMORY_PATH[memory_type]):
        os.remove(MEMORY_PATH[memory_type])
        print(f"✅ Successfully cleared {memory_type} memory.")
    else:
        print(f"✅ {memory_type} memory was already empty.")

def verify_clear(memory_type):
    """Verifies that a memory type is cleared."""
    if os.path.exists(MEMORY_PATH[memory_type]) and os.path.getsize(MEMORY_PATH[memory_type]) > 0:
        print(f"❌ Error: {memory_type} memory was not cleared.")
        sys.exit(1)
    else:
        print(f"✅ Verification successful: {memory_type} memory is empty.")

def integrity_check():
    """Performs a data integrity check using hashes."""
    print("🛡️ Performing data integrity check...")
    original_content = "Integrity test data"
    original_hash = calculate_hash(original_content)

    # Add to memory
    add_memory("semantic", original_content)

    # Retrieve from memory
    with open(MEMORY_PATH["semantic"], "r") as f:
        memories = [line.strip() for line in f.readlines()]
    
    retrieved_content = ""
    if original_content in memories:
        retrieved_content = original_content
    else:
        print("❌ Integrity Check Failed: Could not retrieve data.")
        sys.exit(1)

    retrieved_hash = calculate_hash(retrieved_content)

    if original_hash == retrieved_hash:
        print("✅ Data Integrity Verified: Hashes match.")
    else:
        print("❌ Integrity Check Failed: Hashes do not match.")
        sys.exit(1)
    
    clear_memory("semantic")


def main():
    """Main function to route commands."""
    if len(sys.argv) < 2:
        print("Usage: python test_neuron_memory.py [add|view|clear|verify_clear|integrity_check] [args...]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "add":
        add_memory(sys.argv[2], sys.argv[3])
    elif command == "view":
        view_memory(sys.argv[2], sys.argv[3])
    elif command == "clear":
        clear_memory(sys.argv[2])
    elif command == "verify_clear":
        verify_clear(sys.argv[2])
    elif command == "integrity_check":
        integrity_check()
    else:
        print(f"Error: Unknown command '{command}'")
        sys.exit(1)

if __name__ == "__main__":
    main()
