import unittest
from datetime import datetime
import json
from brain.daily_activity import DailyScheduler

class TestDailyScheduler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n🌟 Starting Tests for Hanna's Daily Schedule 🌟")
        print("=" * 50)

    def setUp(self):
        self.scheduler = DailyScheduler()
        
        # Hanna's persona profile
        self.mock_profile = {
            "name": "Hanna",
            "age": 23,
            "personality_traits": [
                "enthusiastic",
                "romantic",
                "empathetic",
                "passionate about anime",
                "dreamy"
            ],
            "interests": [
                "anime",
                "Naruto series",
                "romance manga",
                "Japanese culture",
                "cosplay",
                "romantic movies",
                "slice of life anime"
            ],
            "favorite_anime": {
                "series": ["Naruto", "Your Name", "Kimi ni Todoke", "Fruits Basket"],
                "genres": ["romance", "action", "slice of life"],
                "characters": ["Naruto Uzumaki", "Hinata Hyuga", "Sakura Haruno"]
            },
            "energy_level": "high",
            "learning_style": "visual-emotional",
            "emotional_traits": {
                "enthusiasm": 9,
                "sensitivity": 8,
                "empathy": 9,
                "romanticism": 9
            }
        }
        
        # Mock schedule with Hanna's typical activities
        self.mock_schedule = {
            "08:00": {
                "activity": "Watch latest episode of Naruto Shippuden",
                "duration": "1 hour",
                "priority": "high"
            },
            "10:00": {
                "activity": "Read new chapter of romance manga 'Kimi ni Todoke'",
                "duration": "1 hour",
                "priority": "normal"
            },
            "14:00": {
                "activity": "Work on Hinata cosplay costume",
                "duration": "2 hours",
                "priority": "normal"
            },
            "16:00": {
                "activity": "Watch romantic slice of life anime",
                "duration": "1 hour",
                "priority": "normal"
            }
        }
        print("\n🔄 Setting up new test...")

    def test_schedule_generation(self):
        """Test schedule generation with Hanna's profile"""
        print("\n📅 Testing Schedule Generation")
        print("-" * 40)
        
        recent_history = {
            "last_watched_episode": "Naruto Shippuden 134",
            "current_manga": "Kimi ni Todoke Chapter 45",
            "mood": "romantic",
            "recent_activities": [
                "Finished watching a romantic anime movie",
                "Started working on Hinata cosplay",
                "Discussed latest Naruto episodes with friends"
            ]
        }
        
        print("📝 Recent History:")
        print(f"  • Last Episode: {recent_history['last_watched_episode']}")
        print(f"  • Current Manga: {recent_history['current_manga']}")
        print(f"  • Mood: {recent_history['mood']}")
        
        schedule = self.scheduler.create_daily_schedule(self.mock_profile, recent_history)
        schedule_dict = json.loads(schedule)
        
        print("\n📊 Generated Schedule:")
        for time, activity in schedule_dict.items():
            print(f"  ⏰ {time}: {activity['activity']} ({activity['priority']} priority)")
        
        # Verify schedule structure
        self.assertIsInstance(schedule_dict, dict)
        for time_slot, activity in schedule_dict.items():
            self.assertIn("activity", activity)
            self.assertIn("duration", activity)
            self.assertIn("priority", activity)

    def test_naruto_activity_execution(self):
        """Test execution of Naruto watching activity"""
        print("\n🍜 Testing Naruto Activity Execution")
        print("-" * 40)
        
        naruto_activity = {
            "activity": "Watch Naruto Shippuden episode 135 - The Promise That Was Kept",
            "duration": "1 hour",
            "priority": "high"
        }
        
        print(f"🎬 Activity: {naruto_activity['activity']}")
        
        result = self.scheduler.execute_current_activity(
            json.dumps({
                "08:00": naruto_activity
            }),
            self.mock_profile,
            datetime.strptime("08:00", "%H:%M")
        )
        
        print("\n📺 Execution Result:")
        execution_result = result["execution_result"]
        
        if execution_result.get("content_info"):
            print("  ℹ️ Content Information Retrieved")
            experience_details = execution_result["experience_details"]
            print(f"  ⭐ Engagement Level: {experience_details.get('engagement_level', 'N/A')}/10")
            print("\n  🗨️ Key Reactions:")
            for reaction in experience_details.get('key_reactions', []):
                print(f"    • {reaction}")
            print("\n  ✨ Memorable Moments:")
            for moment in experience_details.get('memorable_moments', []):
                print(f"    • {moment}")
        
        self.assertEqual(result["status"], "success")

    def test_romance_manga_activity(self):
        """Test execution of romance manga reading activity"""
        print("\n📖 Testing Romance Manga Activity")
        print("-" * 40)
        
        manga_activity = {
            "activity": "Read new chapter of Kimi ni Todoke",
            "duration": "1 hour",
            "priority": "normal"
        }
        
        print(f"📚 Activity: {manga_activity['activity']}")
        
        result = self.scheduler.execute_current_activity(
            json.dumps({
                "10:00": manga_activity
            }),
            self.mock_profile,
            datetime.strptime("10:00", "%H:%M")
        )
        
        print("\n📑 Execution Result:")
        execution_result = result["execution_result"]
        
        if execution_result.get("content_info"):
            print("  ℹ️ Content Information Retrieved")
            experience_details = execution_result["experience_details"]
            print(f"  ⭐ Engagement Level: {experience_details.get('engagement_level', 'N/A')}/10")
            print("\n  💭 Reactions:")
            for reaction in experience_details.get('key_reactions', []):
                print(f"    • {reaction}")

    def test_cosplay_activity(self):
        """Test execution of cosplay creation activity"""
        print("\n🎭 Testing Cosplay Activity")
        print("-" * 40)
        
        cosplay_activity = {
            "activity": "Work on Hinata cosplay costume",
            "duration": "2 hours",
            "priority": "normal"
        }
        
        print(f"👘 Activity: {cosplay_activity['activity']}")
        
        result = self.scheduler.execute_current_activity(
            json.dumps({
                "14:00": cosplay_activity
            }),
            self.mock_profile,
            datetime.strptime("14:00", "%H:%M")
        )
        
        print("\n🪡 Execution Result:")
        execution_result = result["execution_result"]
        
        if "details" in execution_result:
            print(f"  📝 Details: {execution_result['details']}")
        print(f"  ✅ Success: {execution_result.get('success', False)}")

    def test_tool_detection(self):
        """Test if tool detection correctly identifies web browsing activities"""
        print("\n🔍 Testing Activity Type Detection")
        print("-" * 40)
        
        web_activities = [
            "Watch Naruto Shippuden episode",
            "Read new chapter of Kimi ni Todoke online",
            "Research cosplay tutorials",
            "Browse anime recommendations"
        ]
        
        offline_activities = [
            "Work on cosplay costume",
            "Practice Naruto hand signs",
            "Organize anime collection",
            "Draw manga characters"
        ]
        
        print("🌐 Testing Web Activities:")
        for activity in web_activities:
            result = self.scheduler._check_tools_needed(activity)
            print(f"  • {activity}: {'✅' if result['tool_type'] == 'web_browsing' else '❌'}")
            
        print("\n🏠 Testing Offline Activities:")
        for activity in offline_activities:
            result = self.scheduler._check_tools_needed(activity)
            print(f"  • {activity}: {'✅' if result['tool_type'] == 'simulation' else '❌'}")

    @classmethod
    def tearDownClass(cls):
        print("\n" + "=" * 50)
        print("🎉 All Tests Completed! 🎉")

if __name__ == '__main__':
    unittest.main(verbosity=2)
