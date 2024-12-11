import unittest
import os
from datetime import datetime
from brain.brain import Brain
from brain.memory import Memory, MemoryType
import time

class TestBrain(unittest.TestCase):
    def setUp(self):
        # Use a test database file
        self.test_db_path = "test_memories.db"
        self.test_persona_id = "test_persona"
        
        # Ensure any existing test database is removed
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except PermissionError:
                time.sleep(0.1)  # Give OS time to release file
                try:
                    os.remove(self.test_db_path)
                except PermissionError:
                    pass  # Will try again in next test
                
        self.brain = Brain(self.test_persona_id, self.test_db_path)

    def tearDown(self):
        # Clean up the test database after each test
        if hasattr(self, 'brain'):
            self.brain.db.close()
        
        # Give OS time to release file handles
        time.sleep(0.1)
        
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except PermissionError:
            pass  # Will be handled in next setUp

    def test_create_memory(self):
        # Test creating a new memory
        content = "This is a test memory"
        memory = self.brain.create_memory(content)

        # Verify memory was created correctly
        self.assertEqual(memory.content, content)
        self.assertEqual(memory.memory_type, MemoryType.CONVERSATION)
        self.assertIsInstance(memory.timestamp, datetime)
        self.assertEqual(len(memory.vector), 5)  # Based on placeholder implementation
        
        # Verify memory was stored in brain's memory dict
        self.assertEqual(len(self.brain.memories), 1)
        
        # Verify memory was stored in database
        stored_memories = self.brain.db.get_memories(self.test_persona_id)
        self.assertEqual(len(stored_memories), 1)
        self.assertEqual(stored_memories[0].content, content)

    def test_clear_memories(self):
        # Create some test memories
        self.brain.create_memory("Memory 1")
        self.brain.create_memory("Memory 2")
        
        # Verify memories were created
        memories = self.brain.get_all_memories()
        self.assertEqual(len(memories), 2)
        
        # Clear memories
        self.brain.clear_memories()
        
        # Verify memories were cleared from both memory dict and database
        self.assertEqual(len(self.brain.get_all_memories()), 0)
        stored_memories = self.brain.db.get_memories(self.test_persona_id)
        self.assertEqual(len(stored_memories), 0)

    def test_multiple_personas(self):
        # Create a second brain instance with different persona
        second_persona_id = "test_persona_2"
        brain2 = Brain(second_persona_id, self.test_db_path)

        try:
            # Create memories for both personas
            memory1 = self.brain.create_memory("Memory for persona 1")
            memory2 = brain2.create_memory("Memory for persona 2")

            # Verify each persona has its own memories
            persona1_memories = self.brain.get_all_memories()
            persona2_memories = brain2.get_all_memories()

            self.assertEqual(len(persona1_memories), 1)
            self.assertEqual(len(persona2_memories), 1)
            self.assertEqual(persona1_memories[0].content, "Memory for persona 1")
            self.assertEqual(persona2_memories[0].content, "Memory for persona 2")
        finally:
            brain2.db.close()

    def test_mood_and_status(self):
        # Test mood functionality
        self.brain.set_mood("happy")
        self.assertEqual(self.brain.get_mood(), "happy")

        # Test status functionality
        self.brain.set_status("thinking")
        self.assertEqual(self.brain.get_status(), "thinking")

if __name__ == '__main__':
    unittest.main() 