from datetime import datetime
import time
import random
from brain.groq_tool import GroqTool

class TestConnect:
    def test_connect(self):
        # Simulate some processing time
        time.sleep(0.1)
        
        # Get current timestamp in ISO format
        current_time = datetime.utcnow().isoformat() + "Z"
        
        # Simulate some metrics
        latency = random.randint(50, 200)
        packet_loss = random.uniform(0, 2.0)
        
        # Determine connection quality based on metrics
        if latency < 100 and packet_loss < 0.5:
            quality = "excellent"
        elif latency < 150 and packet_loss < 1.0:
            quality = "good"
        else:
            quality = "fair"
            
        return {
            "status": "success",
            "message": "MOTHER FUCKER! 🖕",
            "data": {
                "timestamp": current_time,
                "test_id": f"test_{int(time.time())}",
                "metrics": {
                    "latency": f"{latency}ms",
                    "packet_loss": f"{packet_loss:.2f}%",
                    "connection_quality": quality,
                    "sample_rate": "24000Hz",
                    "audio_buffer_size": "1024 samples"
                }
            }
        }
    
    async def analyze_emotion(self, text: str) -> dict:
        """Analyze emotion and speech style of text using Groq"""
        groq = GroqTool()
        
        prompt = f"""Analyze the following text and determine how would this persona answer:

Persona Profile: Jake is a a hustel on the street a strong man.

1. The emotional state (e.g. angry, happy, sad)
2. The speech style (e.g. whisper, shout, normal)

Text: {text}

Return a JSON object with emotion and speech style in this format:
{{"emotion": "[emotion]", "speech": "[style]"}}"""

        try:
            response = await groq.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            print('FUCK {response}')
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error analyzing emotion: {str(e)}")
            print('FUCK {response}')

            return {
                "emotion": "neutral", 
                "speech": "normal"
            }
        
if __name__ == "__main__":
    test_connect = TestConnect()
    print(test_connect.test_connect())