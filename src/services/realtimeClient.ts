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