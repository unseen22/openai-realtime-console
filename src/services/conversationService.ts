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

interface TranscriptionResponse {
  text: string;
  search_results?: string;
  status?: string;
}

export const transcribeLocal = async (audioData: Int16Array): Promise<TranscriptionResponse | null> => {
  if (!LOCAL_RELAY_SERVER_URL) {
    console.log('LOCAL_RELAY_SERVER_URL not set');
    return null;
  }

  try {
    // Log audio data details
    console.log('🎤 [LOCAL] Audio data stats:', {
      samples: audioData.length,
      sampleRate: '24kHz',
      duration: `${(audioData.length / 24000).toFixed(2)}s`
    });

    // Create WAV blob from the buffer directly
    const audioBuffer = audioData.buffer;
    const blob = new Blob([audioBuffer], { type: 'audio/wav' });
    
    console.log('🎤 [LOCAL] Created WAV blob:', {
      size: `${(blob.size / 1024).toFixed(2)}KB`,
      type: blob.type
    });

    // Send to server
    const formData = new FormData();
    formData.append('audio_file', blob, 'recording.wav');
    console.log('🎤 [LOCAL] Sending audio to transcribe endpoint');
    
    const response = await fetch(`${LOCAL_RELAY_SERVER_URL}/transcribe/local`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      let errorDetail;
      try {
        const errorJson = JSON.parse(errorText);
        errorDetail = errorJson.detail;
      } catch {
        errorDetail = errorText;
      }
      console.error('[LOCAL] Transcription failed:', {
        status: response.status,
        statusText: response.statusText,
        error: errorDetail
      });
      return null;
    }
    
    const data = await response.json();
    console.log('🎤 [LOCAL] X Transcription successful:', data);
    
    if (data && data.text) {
      let cleanedSearchResults = '';
      
      if (data.search_results) {
        // Split by common delimiters and take only relevant parts
        const parts = data.search_results
          .split(/(?:This is the question being asked:|These are relevant memories:|Speak in an angry tone)/)
          .filter(Boolean)  // Remove empty strings
          .map((part: string) => part.trim())
          .filter((part: string) => part && !part.includes('takichi')); // Remove parts with 'takichi'

        // Take only the most recent meaningful memory
        cleanedSearchResults = parts[0] || '';
      }
      console.log('🎤 [QUESTION RETURNED] Cleaned search results:', data.text);
      return {
        text: data.text,
        search_results: cleanedSearchResults,
        status: data.status || 'success'
      };
    }
    return null;
  } catch (error) {
    console.error('[LOCAL] Error in transcribeLocal:', error);
    return null;
  }
};

export const setupConversation = async (client: RealtimeClient) => {
  // Set up conversation configuration with default values first
  await client.updateSession({
    instructions: instructions,
    voice: 'ash',
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
