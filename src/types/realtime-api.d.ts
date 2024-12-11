declare module '@openai/realtime-api-beta' {
  export interface RealtimeClientOptions {
    url?: string;
    apiKey?: string;
    dangerouslyAllowAPIKeyInBrowser?: boolean;
  }

  export interface Tool {
    name: string;
    description: string;
    parameters: {
      type: string;
      properties: Record<string, any>;
      required: string[];
    };
  }

  export interface Conversation {
    getItems(): ItemType[];
  }

  export class RealtimeClient {
    conversation: Conversation;

    constructor(options: RealtimeClientOptions);

    connect(): Promise<void>;
    disconnect(): void;
    reset(): void;
    isConnected(): boolean;
    getTurnDetectionType(): string;
    deleteItem(id: string): void;
    appendInputAudio(data: Float32Array | Int16Array): void;
    createResponse(): void;
    cancelResponse(trackId: string, offset: number): Promise<void>;
    sendUserMessageContent(content: Array<{ type: string; text: string }>): void;
    updateSession(options: { 
      turn_detection?: { type: string } | null;
      instructions?: string;
      voice?: string;
      input_audio_transcription?: { model: string };
    }): void;
    addTool(tool: Tool, handler: (args: any) => Promise<any>): void;
    on(event: string, handler: (data: any) => void): void;
  }
} 