from typing import List
import json
from brain.llm_chooser import LLMChooser

class KeywordExtractor:
    def __init__(self, llm_tool: LLMChooser = None):
        """Initialize KeywordExtractor
        
        Args:
            llm_tool: Optional LLMChooser instance. If not provided, a new one will be created.
        """
        self.llm_tool = llm_tool or LLMChooser()

    async def extract_keywords(self, content: str) -> List[str]:
        """Extract up to 5 keywords from the content.
        
        Args:
            content: The text content to extract keywords from
            
        Returns:
            List of keyword strings
            
        Example:
            ["keyword1", "keyword2", "keyword3"]
        """
        prompt = f"""Given this memory content: "{content}"
        
Extract up to 5 relevant keywords that capture the main topics and themes.
Return only a JSON array of keyword strings.

Example: ["keyword1", "keyword2", "keyword3"]"""

        try:
            response = await self.llm_tool.generate_text(
                provider="groq",
                prompt=prompt,
                temperature=0.3,
                max_tokens=100
            )
            print(f"Keywords extracted: {response}")
            return json.loads(response)
        except Exception as e:
            print(f"Error generating keywords: {e}")
            return [] 