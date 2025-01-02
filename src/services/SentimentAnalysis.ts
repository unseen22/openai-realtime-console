export class SentimentAnalysisService {
  private static readonly GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';
  private apiKey: string;

  constructor() {
    // Replace with your Groq API key
    this.apiKey = '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';
  }

  async analyzeEmotion(text: string): Promise<any> {
    try {
      const prompt = `Analyze the following text and determine how would this persona answer:

Persona Profile: Jake is a hustler on the street a strong man.

1. The emotional state (e.g. angry, happy, sad)
2. The speech style (e.g. whisper, shout, normal)

Text: ${text}

Return a JSON object with emotion and speech style in this format:
{"emotion": "[emotion]", "speech": "[style]"}`;

      const requestBody = {
        messages: [
          {
            role: "user",
            content: prompt
          }
        ],
        model: "llama-3.3-70b-versatile",
        temperature: 1.1,
        response_format: { type: "json_object" }
      };

      console.log('Sending request to Groq API:', {
        url: SentimentAnalysisService.GROQ_API_URL,
        prompt,
        requestBody
      });

      const response = await fetch(SentimentAnalysisService.GROQ_API_URL, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorBody = await response.text();
        console.error('Groq API error details:', {
          status: response.status,
          statusText: response.statusText,
          body: errorBody
        });
        throw new Error(`Groq API failed: ${response.status} ${response.statusText} - ${errorBody}`);
      }

      const result = await response.json();
      console.log('Raw API Response:', result);
      
      // Parse the content as JSON since it's returned as a string
      const content = JSON.parse(result.choices[0].message.content);
      console.log('Parsed emotion analysis result:', content);
      
      return content;
    } catch (error) {
      console.error('Emotion analysis error:', error);
      return {
        emotion: "neutral",
        speech: "normal"
      };
    }
  }
}
