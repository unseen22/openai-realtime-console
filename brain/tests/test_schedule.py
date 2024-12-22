import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import unittest
from datetime import datetime
import json
from brain.daily_activity import DailyScheduler

class TestDailyScheduler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n🌟 Starting Persona Schedule Test 🌟")
        print("=" * 50)

    def setUp(self):
        self.scheduler = DailyScheduler()
        
        # Single persona profile string that encapsulates the character
        self.persona = {
            "profile": "Hanna is a 23-year-old enthusiastic anime fan with a romantic personality. She loves Naruto, romance manga, and Japanese culture. She's highly empathetic and passionate about cosplay. Her favorite series include Naruto, Your Name, and Fruits Basket. She has high energy levels and learns best through visual-emotional experiences. She's currently working on a Hinata cosplay and following the Naruto Shippuden series."
        }

    def test_full_schedule_flow(self):
        """Test complete flow from schedule generation to activity execution"""
        print("\n📋 Testing Complete Schedule Flow")
        print("-" * 50)

        try:
            # 1. Generate Schedule
            print("\n🎯 Generating Daily Schedule...")
            schedule = self.scheduler.create_daily_schedule(self.persona, {})
            schedule_dict = json.loads(schedule)
            
            print("\n📅 Generated Schedule:")
            for time, activity in schedule_dict.items():
                print(f"⏰ {time}: {activity['activity']} ({activity['priority']} priority)")

            # 2. Execute Each Activity
            print("\n🎬 Executing Activities:")
            for time_slot, activity in schedule_dict.items():
                print(f"\n▶️ Executing activity at {time_slot}:")
                print(f"   {activity['activity']}")
                
                result = self.scheduler.execute_current_activity(
                    json.dumps({time_slot: activity}),
                    self.persona,
                    datetime.strptime(time_slot, "%H:%M")
                )
                
                # Display execution results
                if result["status"] == "success":
                    print("✅ Execution successful")
                    if "execution_result" in result:
                        execution = result["execution_result"]
                        if "content_info" in execution:
                            print("\n📚 Content Information:")
                            print(f"   {execution['content_info'][:200]}...")
                        if "experience_details" in execution:
                            exp = execution["experience_details"]
                            print("\n💭 Experience Details:")
                            if "engagement_level" in exp:
                                print(f"   Engagement: {exp['engagement_level']}/10")
                            if "key_reactions" in exp:
                                print("   Key Reactions:")
                                for reaction in exp['key_reactions'][:3]:
                                    print(f"   • {reaction}")
                else:
                    print(f"❌ Execution failed: {result.get('message', 'Unknown error')}")

                print("-" * 30)

            # Verify schedule structure
            self.assertIsInstance(schedule_dict, dict)
            for time_slot, activity in schedule_dict.items():
                self.assertIn("activity", activity)
                self.assertIn("duration", activity)
                self.assertIn("priority", activity)

        except Exception as e:
            print(f"\n⚠️ Test failed: {str(e)}")
            print(f"🔍 Error type: {type(e).__name__}")
            raise

    def test_tool_detection(self):
        """Test if tool detection works with the persona's activities"""
        print("\n🔍 Testing Activity Tool Detection")
        print("-" * 50)
        
        test_activities = [
            "Watch Naruto Shippuden episode 136",
            "Work on Hinata cosplay costume",
            "Read new chapter of Fruits Basket",
            "Practice Japanese phrases",
            "Browse anime recommendations"
        ]
        
        for activity in test_activities:
            result = self.scheduler._check_tools_needed(activity)
            tool_type = result.get('tool_type', 'unknown')
            print(f"Activity: {activity}")
            print(f"Tool Type: {tool_type}")
            print(f"{'🌐' if tool_type == 'web_browsing' else '🏠'} " + "-" * 30)

    @classmethod
    def tearDownClass(cls):
        print("\n" + "=" * 50)
        print("🎉 Test Suite Completed! 🎉")

if __name__ == '__main__':
    unittest.main(verbosity=2)
