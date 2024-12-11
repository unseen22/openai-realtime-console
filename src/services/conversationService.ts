import { RealtimeClient } from '@openai/realtime-api-beta';
import { instructions } from '../utils/conversation_config.js';

const LOCAL_RELAY_SERVER_URL: string = process.env.REACT_APP_LOCAL_RELAY_SERVER_URL || '';

export const setupConversation = async (client: RealtimeClient) => {
  // Fetch memories if using local relay server
  let memoriesText = '';
  if (LOCAL_RELAY_SERVER_URL) {
    try {
      const response = await fetch(`${LOCAL_RELAY_SERVER_URL}/fake-memories`);
      const data = await response.json();
      if (data.memories?.length > 0) {
        memoriesText = `\n\nThese are memories you recall:\n${data.memories.map((m: any) => `- ${m.content}`).join('\n')}`;
      }
    } catch (error) {
      console.error('Error fetching memories:', error);
    }
  }

  // Set up conversation configuration
  client.updateSession({
    // Add memories to instructions if available
    instructions: instructions + memoriesText,
    // Set voice model
    voice: 'alloy',
    // Enable transcription
    input_audio_transcription: { model: 'whisper-1' }
  });
}; 