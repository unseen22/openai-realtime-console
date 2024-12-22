import { RealtimeClient } from '@openai/realtime-api-beta';

const LOCAL_RELAY_SERVER_URL: string = process.env.REACT_APP_LOCAL_RELAY_SERVER_URL || '';

export const createRealtimeClient = (apiKey: string = '') => {
  return new RealtimeClient(
    LOCAL_RELAY_SERVER_URL
      ? { url: LOCAL_RELAY_SERVER_URL }
      : {
          apiKey: apiKey,
          dangerouslyAllowAPIKeyInBrowser: true,
        }
  );
};

export const sendOutOfBandResponse = async (client: RealtimeClient, prompt: string, metadata: any = {}) => {
  console.log('🚀 [OUTBAND] Starting to send out-of-band response:', {
    prompt,
    metadata
  });

  // Create the event with the proper structure for out-of-band responses
  const event = {
    type: "response.create",
    response: {
      // Setting to "none" indicates the response is out of band
      // and will not be added to the default conversation
      conversation: "none",

      // Set metadata to help identify responses sent back from the model
      metadata,
      
      // Set any other available response fields
      modalities: ["text"],
      instructions: prompt,

      // Create a custom input array for this request
      input: [
        {
          type: "message",
          role: "user",
          content: [
            {
              type: "input_text",  // Changed to match docs
              text: prompt,
            },
          ],
        },
      ],
    }
  };

  // Send the raw event through the client
  // @ts-ignore - We know this exists even though it's not in the type definitions
  if (client.realtime?.send) {
    try {
      // @ts-ignore - We know this exists even though it's not in the type definitions
      client.realtime.send(event.type, event);
      console.log('✅ [OUTBAND] Event sent successfully:', JSON.stringify(event, null, 2));
    } catch (error) {
      console.error('❌ [OUTBAND] Error sending event:', error);
      throw error;
    }
  } else {
    const error = 'Unable to send out-of-band response: realtime API not available';
    console.error('❌ [OUTBAND]', error);
    throw new Error(error);
  }

  // Log the client state
  console.log('🔍 [OUTBAND] Client state:', {
    isConnected: client.isConnected()
  });
};

export const setupClientTools = (client: RealtimeClient, onMemorySet: (key: string, value: any) => void) => {
  // Add memory tool
  client.addTool(
    {
      name: 'set_memory',
      description: 'Saves important data about the user into memory.',
      parameters: {
        type: 'object',
        properties: {
          key: {
            type: 'string',
            description: 'The key of the memory value. Always use lowercase and underscores, no other characters.',
          },
          value: {
            type: 'string',
            description: 'Value can be anything represented as a string',
          },
        },
        required: ['key', 'value'],
      },
    },
    async ({ key, value }: { [key: string]: any }) => {
      onMemorySet(key, value);
      return { ok: true };
    }
  );

  // Add weather tool
  client.addTool(
    {
      name: 'get_weather',
      description: 'Retrieves the weather for a given lat, lng coordinate pair. Specify a label for the location.',
      parameters: {
        type: 'object',
        properties: {
          lat: {
            type: 'number',
            description: 'Latitude',
          },
          lng: {
            type: 'number',
            description: 'Longitude',
          },
          location: {
            type: 'string',
            description: 'Name of the location',
          },
        },
        required: ['lat', 'lng', 'location'],
      },
    },
    async ({ lat, lng, location }: { [key: string]: any }) => {
      const result = await fetch(
        `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m,wind_speed_10m`
      );
      const json = await result.json();
      return json;
    }
  );
}; 