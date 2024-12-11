import { RealtimeClient } from '@openai/realtime-api-beta';
import { instructions } from '../utils/conversation_config.js';

const LOCAL_RELAY_SERVER_URL: string = process.env.REACT_APP_LOCAL_RELAY_SERVER_URL || 'http://localhost:8081';

interface Memory {
  id: number;
  string: string;
  timestamp: string;
  importance: number;
  type: string;
}

export const setupConversation = async (client: RealtimeClient) => {
  // Set up conversation configuration with default values first
  await client.updateSession({
    instructions: instructions,
    voice: 'alloy',
    input_audio_transcription: { model: 'whisper-1' }
  });
}; 

export const updateSessionWithMemories = async (client: RealtimeClient) => {
  // Fetch memories if using local relay server
  let memoriesText = '';
  if (LOCAL_RELAY_SERVER_URL) {
    try {
      const response = await fetch(`${LOCAL_RELAY_SERVER_URL}/fake-memories`);
      const data = await response.json();
      if (data.memories && Array.isArray(data.memories) && data.memories.length > 0) {
        // Format memories into readable strings
        memoriesText = data.memories
          .map((memory: Memory) => memory.string)
          .join('\n');
        
        // Update session with formatted memories
        await client.updateSession({
          instructions: `${instructions}\n\nThese are your recent memories:\n${memoriesText}`,
        });
      } else {
        console.log('No memories found in response');
      }
    } catch (error) {
      console.error('Error fetching memories:', error);
    }
  } else {
    console.log('LOCAL_RELAY_SERVER_URL not set');
  }
}; 