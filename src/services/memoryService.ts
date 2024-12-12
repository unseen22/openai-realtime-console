const LOCAL_RELAY_SERVER_URL: string = process.env.REACT_APP_LOCAL_RELAY_SERVER_URL || 'http://localhost:8081';

interface ConversationItem {
  speaker: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export const saveConversationToMemory = async (conversation: ConversationItem): Promise<void> => {
  if (!LOCAL_RELAY_SERVER_URL) {
    console.log('LOCAL_RELAY_SERVER_URL not set');
    return;
  }

  try {
    const response = await fetch(`${LOCAL_RELAY_SERVER_URL}/conversation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(conversation),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log('Conversation saved to memory:', result);
  } catch (error) {
    console.error('Error saving conversation to memory:', error);
  }
}; 