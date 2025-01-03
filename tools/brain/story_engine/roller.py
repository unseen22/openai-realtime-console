import random
from enum import Enum
from typing import Dict, Optional
import json
from brain.brain import Brain
from brain.llm_chooser import LLMChooser

class TaskDifficulty(Enum):
    MUNDANE = 0
    EASY = 6
    HARD = 10
    CHALLENGING = 14



class StoryRoller:
    def __init__(self, persona):
        """Initialize with brain instance"""
        self.persona = persona
        self.llm_chooser = LLMChooser()
        
    

    async def _determine_difficulty(self, task: str) -> TaskDifficulty:
        """Analyze task to determine its difficulty level"""
        # Create prompt for difficulty analysis
        print(f"🎯 DETERMINING DIFFICULTY FOR TASK: {task}")
        prompt = f"""
        Given this persona's profile:
        {self.persona['profile']}
        
        Analyze this task and determine its difficulty level for this persona:
        {task}
        
        Return only a JSON object with:
        - difficulty: One of ["mundane", "easy", "hard", "challenging"]
        """
        
        try:
            # Get difficulty assessment from LLM
            llm_response = await self.llm_chooser.generate_text(
                provider="groq",
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=128,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(llm_response)
            difficulty = result["difficulty"].upper()
            return TaskDifficulty[difficulty]
            
        except Exception as e:
            print(f"Error determining difficulty: {str(e)}")
            return TaskDifficulty.EASY

    async def _roll_d20(self) -> int:
        """Roll a d20 die"""
        roll = random.randint(1, 20)
        print(f"🎲 D20 Roll: {roll}")
        return roll

    async def _get_characteristic_bonus(self, task: str) -> int:
        """Determine which characteristic applies to this task and get its bonus value"""
        prompt = f"""
        Given this task: {task}

        Determine which characteristic is most relevant:

        - Mind: Mental abilities, knowledge, intelligence, problem-solving
        - Body: Physical abilities, health, fitness, coordination
        - Heart: Emotional intelligence, empathy, social skills
        - Soul: Spiritual awareness, intuition, creativity
        - Will: Determination, focus, mental fortitude

        Return only a JSON object with:
        - characteristic: One of ["mind", "body", "heart", "soul", "will"]
        """

        try:
            # Get characteristic assessment from LLM
            llm_response = await self.llm_chooser.generate_text(
                provider="groq",
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=128,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(llm_response)
            characteristic = result["characteristic"].lower()
            characteristics_dict = json.loads(self.persona['characteristics'])
            bonus = characteristics_dict[characteristic]
            print(f"💫 {characteristic.title()} bonus: +{bonus}")
            return bonus
            
        except Exception as e:
            print(f"Error determining characteristic bonus: {str(e)}")
            return 0

    async def roll_for_outcome(self, task: str) -> str:
        """
        Roll for task outcome, considering difficulty and characteristics.
        Returns one of: "super_success", "success", "failure", "super_failure"
        """
        difficulty = await self._determine_difficulty(task)
        print(f"📊 Task difficulty: {difficulty.name} (DC {difficulty.value})")
        
        # Mundane tasks automatically succeed
        if difficulty == TaskDifficulty.MUNDANE:
            print("✨ Mundane task - automatic success!")
            return "success"
            
        d20_roll = await self._roll_d20()
        characteristic_bonus = await self._get_characteristic_bonus(task)
        total_roll = d20_roll + characteristic_bonus
        print(f"🎯 Total roll: {total_roll} (Roll: {d20_roll} + Bonus: {characteristic_bonus})")
        
        # Calculate difference from difficulty threshold
        difference = total_roll - difficulty.value
        
        # Determine degree of success/failure
        if difference >= 6:
            print("✨ Super Success!")
            return "super_success"
        elif difference >= 0:
            print("✅ Success!")
            return "success"
        elif difference >= -6:
            print("❌ Failure!")
            return "failure"
        else:
            print("💥 Super Failure!")
            return "super_failure"
