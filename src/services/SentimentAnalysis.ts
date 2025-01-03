export class SentimentAnalysisService {
  private static readonly OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions';
  private apiKey: string;

  constructor() {
    // Replace with your OpenAI API key
    this.apiKey = ''}

  private profile = `Emotional State Profile: Joi
Joi  carries an intense duality in her emotional landscape. On one hand, she's vibrant and full of energy, thriving in high-paced environments like the track or underground rave scenes. Her love for speed and rhythm reflects her hunger for adrenaline and excitement, but when life forces her to slow down, she becomes introspective. The loss of her competitive career left a scar, creating moments of self-doubt and frustration. She's quick-tempered, especially when something challenges her sense of purpose, but she's equally quick to soften, revealing a sincere, apologetic side that values her relationships deeply.

Music and movement are Joi's emotional anchors. Heavy techno reminds her of her power, while lofi offers a safe, quiet escape. Though she's rebuilding confidence, she sometimes feels stuck between past dreams and present realities, making her deeply empathetic toward others who struggle with setbacks. Her small robot companion, Bebe, symbolizes her resilience—quirky, steadfast, and a constant reminder that even in chaos, there's joy to be found. Hanna's emotional growth lies in balancing her need for intensity with her ability to find peace in smaller, softer moments.`;

  async analyzeEmotion(text: string): Promise<any> {
    try {
      const prompt = `Analyze the following text and determine how would this persona answer:

Persona Profile: ${this.profile}

1. The emotional state (e.g. angry, happy, sad, panic, discust, excited etc.)
2. The speech style (e.g. whisper, shout, mumbling, incoherent, sleepy, in a hiss, etc.)

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
        model: "gpt-3.5-turbo",
        temperature: 0.5,
        response_format: { type: "json_object" }
      };

      console.log('Sending request to OpenAI API:', {
        url: SentimentAnalysisService.OPENAI_API_URL,
        prompt,
        requestBody
      });

      const response = await fetch(SentimentAnalysisService.OPENAI_API_URL, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorBody = await response.text();
        console.error('OpenAI API error details:', {
          status: response.status,
          statusText: response.statusText,
          body: errorBody
        });
        throw new Error(`OpenAI API failed: ${response.status} ${response.statusText} - ${errorBody}`);
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
