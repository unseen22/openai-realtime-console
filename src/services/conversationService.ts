import { RealtimeClient } from '@openai/realtime-api-beta';
import { instructions } from '../utils/conversation_config.js';

const LOCAL_RELAY_SERVER_URL: string = process.env.REACT_APP_LOCAL_RELAY_SERVER_URL || 'http://localhost:8081';

interface Memory {
  content: string;
  importance: number;
  memory_type: string;
  timestamp: string;
  vector: number[];
}

interface MemoryResponse {
  status: string;
  persona_id: string;
  memories: Memory[];
}

export const setupConversation = async (client: RealtimeClient) => {
  // Set up conversation configuration with default values first
  await client.updateSession({
    instructions: instructions,
    voice: 'alloy',
    input_audio_transcription: { model: 'whisper-1' }
  });
}; 

export const updateSessionWithMemories = async (client: RealtimeClient, personaId: string = 'pink_man') => {
  if (LOCAL_RELAY_SERVER_URL) {
    try {
      // Initialize all personas
      const response = await fetch(`${LOCAL_RELAY_SERVER_URL}/init-all-personas`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.status === 'success') {
        // Update session with initialized personas
        await client.updateSession({
          instructions: `${instructions}\n\nPersonas initialized successfully`,
        });
        console.log('Session updated with initialized personas:', data.initialized_personas);
      } else {
        console.log('Failed to initialize personas');
      }
    } catch (error) {
      console.error('Error initializing personas:', error);
    }
  } else {
    console.log('LOCAL_RELAY_SERVER_URL not set');
  }
};


export const storeConversationMemory = async (
  userMessage: string,
  assistantResponse: string,
  personaId: string = 'pink_man'
) => {
  if (LOCAL_RELAY_SERVER_URL) {
    try {
      const combinedContent = `User: ${userMessage}\nAssistant: ${assistantResponse}`;
      
      const response = await fetch(`${LOCAL_RELAY_SERVER_URL}/memory/${personaId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: combinedContent,
          memory_type: 'conversation'
        })
      });

      const data = await response.json();
      if (data.status === 'success') {
        console.log('Conversation memory stored successfully');
      } else if (data.status === 'duplicate') {
        console.log('Conversation memory already exists, skipping storage');
      } else {
        console.log('Failed to store conversation memory:', data);
      }
    } catch (error) {
      console.error('Error storing conversation memory:', error);
    }
  } else {
    console.log('LOCAL_RELAY_SERVER_URL not set');
  }
};
