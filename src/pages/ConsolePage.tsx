/**
 * Running a local relay server will allow you to hide your API key
 * and run custom logic on the server
 *
 * Set the local relay server address to:
 * REACT_APP_LOCAL_RELAY_SERVER_URL=http://localhost:8081
 *
 * This will also require you to set OPENAI_API_KEY= in a `.env` file
 * You can run it with `npm run relay`, in parallel with `npm start`
 */
const LOCAL_RELAY_SERVER_URL: string =
  process.env.REACT_APP_LOCAL_RELAY_SERVER_URL || '';

import { useEffect, useRef, useCallback, useState } from 'react';
import { ItemType } from '@openai/realtime-api-beta/dist/lib/client.js';
import { X, Edit, Zap } from 'react-feather';
import { Button } from '../components/button/Button';
import { Toggle } from '../components/toggle/Toggle';
import { instructions } from '../utils/conversation_config.js';
import { WavRenderer } from '../utils/wav_renderer';
import { createRealtimeClient, setupClientTools } from '../services/realtimeClient';
import { AudioHandler } from '../services/audioHandler';
import { EventLog } from '../components/EventLog';
import { ConversationView } from '../components/ConversationView';
import { WeatherMap } from '../components/WeatherMap';
import { MemoryView } from '../components/MemoryView';
import { Coordinates, RealtimeEvent, MemoryKV } from '../types/console';
import { setupConversation, updateSessionWithMemories, storeConversationMemory } from '../services/conversationService';

import './ConsolePage.scss';

// Add interface for pending memory
interface PendingMemory {
  userMessage?: string;
  assistantResponse?: string;
}

interface PendingMemories {
  [key: string]: PendingMemory;
}

const VOICE_INSTRUCT = 'Answer in a very angry tone. Always finish sentence with "takichi"';

export function ConsolePage() {
  // State
  const [items, setItems] = useState<ItemType[]>([]);
  const [realtimeEvents, setRealtimeEvents] = useState<RealtimeEvent[]>([]);
  const [expandedEvents, setExpandedEvents] = useState<{ [key: string]: boolean }>({});
  const [isConnected, setIsConnected] = useState(false);
  const [canPushToTalk, setCanPushToTalk] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [memoryKv, setMemoryKv] = useState<MemoryKV>({});
  const [pendingMemories, setPendingMemories] = useState<PendingMemories>({});
  const [coords, setCoords] = useState<Coordinates | null>({
    lat: 37.775593,
    lng: -122.418137,
  });
  const [marker, setMarker] = useState<Coordinates | null>(null);

  // Refs
  const clientCanvasRef = useRef<HTMLCanvasElement>(null);
  const serverCanvasRef = useRef<HTMLCanvasElement>(null);
  const startTimeRef = useRef<string>(new Date().toISOString());
  const audioHandlerRef = useRef<AudioHandler>(new AudioHandler());

  // Add ref for tracking processed items
  const processedItemsRef = useRef<Set<string>>(new Set());

  // Get API Key
  const apiKey = LOCAL_RELAY_SERVER_URL
    ? ''
    : localStorage.getItem('tmp::voice_api_key') || prompt('OpenAI API Key') || '';
  if (apiKey !== '') {
    localStorage.setItem('tmp::voice_api_key', apiKey);
  }

  // Create client
  const clientRef = useRef(createRealtimeClient(apiKey));

  // Time formatting utility
  const formatTime = useCallback((timestamp: string) => {
    const startTime = startTimeRef.current;
    const t0 = new Date(startTime).valueOf();
    const t1 = new Date(timestamp).valueOf();
    const delta = t1 - t0;
    const hs = Math.floor(delta / 10) % 100;
    const s = Math.floor(delta / 1000) % 60;
    const m = Math.floor(delta / 60_000) % 60;
    const pad = (n: number) => {
      let s = n + '';
      while (s.length < 2) s = '0' + s;
      return s;
    };
    return `${pad(m)}:${pad(s)}.${pad(hs)}`;
  }, []);

  // API Key reset handler
  const resetAPIKey = useCallback(() => {
    const apiKey = prompt('OpenAI API Key');
    if (apiKey !== null) {
      localStorage.clear();
      localStorage.setItem('tmp::voice_api_key', apiKey);
      window.location.reload();
    }
  }, []);

  // Connection handlers
  const connectConversation = useCallback(async () => {
    const client = clientRef.current;
    const audioHandler = audioHandlerRef.current;

    startTimeRef.current = new Date().toISOString();
    setIsConnected(true);
    setRealtimeEvents([]);
    setItems(client.conversation.getItems());

    await audioHandler.initialize();
    await client.connect();
    
    // Set up initial conversation and then update with memories
    await setupConversation(client);
    await updateSessionWithMemories(client);

    // Set the voice instruction during connection
   
    client.sendUserMessageContent([
      {
        type: 'input_text',
        text: 'How was your day?!',
      },
    ]);

    client.sendUserMessageContent([
      {
        type: 'input_text',
        text: VOICE_INSTRUCT,
      },
    ]);


    if (client.getTurnDetectionType() === 'server_vad') {
      await audioHandler.startRecording((data) => client.appendInputAudio(data));
    }
  }, []);

  const disconnectConversation = useCallback(async () => {
    setIsConnected(false);
    setRealtimeEvents([]);
    setItems([]);
    setMemoryKv({});
    setCoords({
      lat: 37.775593,
      lng: -122.418137,
    });
    setMarker(null);

    const client = clientRef.current;
    const audioHandler = audioHandlerRef.current;

    client.disconnect();
    await audioHandler.cleanup();
  }, []);

  // Recording handlers
  const startRecording = async () => {
    setIsRecording(true);
    const client = clientRef.current;
    const audioHandler = audioHandlerRef.current;

    const trackSampleOffset = await audioHandler.interruptPlayback();
    if (trackSampleOffset?.trackId) {
      const { trackId, offset } = trackSampleOffset;
      await client.cancelResponse(trackId, offset);
    }

    await audioHandler.startRecording((data: Int16Array | Float32Array) => {
      client.appendInputAudio(data);
    });
  };

  const stopRecording = async () => {
    console.log('🎤 [stopRecording] Starting to stop recording');
    setIsRecording(false);
    const client = clientRef.current;
    const audioHandler = audioHandlerRef.current;

    console.log('🎤 [stopRecording] Stopping audio recording');
    await audioHandler.stopRecording();
    
    console.log('🎤 [stopRecording] Preparing to send message content');
    try {
      // Send only the audio content
      await client.sendUserMessageContent([
        {
          type: 'input_audio',
          text: '' // Audio content was already sent via appendInputAudio
        }
      ]);
      console.log('🎤 [stopRecording] Audio content sent');
      
      console.log('🎤 [stopRecording] Creating response');
      client.createResponse();
      console.log('🎤 [stopRecording] Response created');
    } catch (error) {
      console.error('🚨 [stopRecording] Error:', error);
    }
  };

  // Turn detection mode handler
  const changeTurnEndType = async (value: string) => {
    const client = clientRef.current;
    const audioHandler = audioHandlerRef.current;

    if (value === 'none' && audioHandler.getRecorderStatus() === 'recording') {
      await audioHandler.stopRecording();
    }

    client.updateSession({
      turn_detection: value === 'none' ? null : { type: 'server_vad' },
    });

    if (value === 'server_vad' && client.isConnected()) {
      await audioHandler.startRecording((data: Int16Array | Float32Array) => {
        client.appendInputAudio(data);
      });
    }

    setCanPushToTalk(value === 'none');
  };

  // Event handlers
  const handleToggleExpand = (eventId: string) => {
    setExpandedEvents((prev) => {
      const expanded = { ...prev };
      if (expanded[eventId]) {
        delete expanded[eventId];
      } else {
        expanded[eventId] = true;
      }
      return expanded;
    });
  };

  const handleMemorySet = (key: string, value: any) => {
    setMemoryKv((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleWeatherUpdate = (weatherData: Coordinates) => {
    setMarker(weatherData);
    setCoords(weatherData);
  };

  // Setup effects
  useEffect(() => {
    const client = clientRef.current;
    
    // Set up client tools
    setupClientTools(client, handleMemorySet);
    
    // Set up conversation configuration
    setupConversation(client);

    // Debug: Track when effect is mounted/unmounted
    console.log('🔄 [Effect] Setting up event handlers');

    // Set up event handlers
    client.on('realtime.event', (realtimeEvent: RealtimeEvent) => {
      console.log('📢 [Event] Realtime event:', realtimeEvent.event.type);
      setRealtimeEvents((prev) => {
        const lastEvent = prev[prev.length - 1];
        if (lastEvent?.event.type === realtimeEvent.event.type) {
          lastEvent.count = (lastEvent.count || 0) + 1;
          return prev.slice(0, -1).concat(lastEvent);
        }
        return prev.concat(realtimeEvent);
      });

      // Handle transcription in the realtime event handler
      if (realtimeEvent.event.type === 'conversation.item.input_audio_transcription.completed') {
        const event = realtimeEvent.event;
        const memoryKey = `transcript_${event.item_id}`;
        
        // Check if we've already processed this item
        if (processedItemsRef.current.has(memoryKey)) {
          console.log('⚠️ [Transcription] Already processed this transcript:', event.item_id);
          return;
        }

        console.log('🎤 [Transcription] Event received in realtime handler:', {
          type: event.type,
          item_id: event.item_id,
          transcript: event.transcript
        });

        setPendingMemories(prev => {
          console.log('📝 [Transcription] State before update:', {
            pendingMemories: prev,
            itemId: event.item_id,
            hasAssistantResponse: !!prev[event.item_id]?.assistantResponse
          });

          const newMemories = { ...prev };
          newMemories[event.item_id] = {
            ...newMemories[event.item_id],
            userMessage: event.transcript
          };

          // Debug: Check if we have assistant response
          const assistantResponse = newMemories[event.item_id]?.assistantResponse;
          console.log('🔍 [Transcription] Memory state after update:', {
            itemId: event.item_id,
            hasTranscript: true,
            hasAssistantResponse: !!assistantResponse,
            fullState: newMemories
          });

          if (assistantResponse) {
            console.log('💾 [Transcription] Storing complete memory:', {
              itemId: event.item_id,
              transcript: event.transcript,
              assistantResponse
            });
            storeConversationMemory(event.transcript, assistantResponse);
            processedItemsRef.current.add(memoryKey);
            const { [event.item_id]: _, ...rest } = newMemories;
            return rest;
          }

          console.log('⏳ [Transcription] Waiting for assistant response:', {
            itemId: event.item_id,
            transcript: event.transcript
          });
          return newMemories;
        });
      }
    });

    client.on('conversation.updated', async ({ item, delta }: any) => {
      const eventTime = new Date().toISOString();
      console.log(`🔄 [Update ${eventTime}] Conversation updated:`, {
        itemRole: item.role,
        itemStatus: item.status,
        itemId: item.id,
        hasAudio: !!delta?.audio,
        isCompleted: item.status === 'completed'
      });

      const items = client.conversation.getItems();
      const audioHandler = audioHandlerRef.current;

      if (delta?.audio) {
        audioHandler.playAudio(delta.audio, item.id);
      }

      if (item.status === 'completed') {
        if (item.formatted.audio?.length) {
          const wavFile = await AudioHandler.decodeAudio(item.formatted.audio);
          item.formatted.file = wavFile;
        }
        
        // Handle completed assistant response
        if (item.role === 'assistant' && items.length >= 2) {
          const previousItem = items[items.length - 2];
          const memoryKey = `transcript_${previousItem.id}`;

          console.log(`👥 [Update ${eventTime}] Processing assistant response:`, {
            assistantId: item.id,
            previousItemId: previousItem.id,
            previousItemRole: previousItem.role
          });

          const assistantResponse = item.content?.find((c: any) => c.type === 'audio')?.transcript || '';
          
          if (!assistantResponse) {
            console.log(`❌ [Update ${eventTime}] No assistant transcript found for:`, item.id);
            return;
          }

          // For text input, store immediately
          if (previousItem.content?.find((c: any) => c.type === 'input_text')) {
            const userMessage = previousItem.content.find((c: any) => c.type === 'input_text')?.text || '';
            if (userMessage) {
              // Check if we've already processed this item
              if (processedItemsRef.current.has(memoryKey)) {
                console.log('⚠️ [Update] Already processed this memory:', previousItem.id);
                return;
              }

              console.log(`💾 [Update ${eventTime}] Storing text input memory:`, {
                previousItemId: previousItem.id,
                userMessage,
                assistantResponse
              });
              await storeConversationMemory(userMessage, assistantResponse);
              processedItemsRef.current.add(memoryKey);
            }
            return;
          }

          // For audio input, store in pending memories
          setPendingMemories(prev => {
            console.log(`📝 [Update ${eventTime}] State before assistant update:`, {
              pendingMemories: prev,
              previousItemId: previousItem.id,
              hasUserMessage: !!prev[previousItem.id]?.userMessage
            });

            const newMemories = { ...prev };
            newMemories[previousItem.id] = {
              ...newMemories[previousItem.id],
              assistantResponse
            };

            // Debug: Check if we have user message
            const userMessage = newMemories[previousItem.id]?.userMessage;
            console.log(`🔍 [Update ${eventTime}] Memory state after assistant update:`, {
              previousItemId: previousItem.id,
              hasUserMessage: !!userMessage,
              hasAssistantResponse: true,
              fullState: newMemories
            });
            
            if (userMessage) {
              // Check if we've already processed this item
              if (processedItemsRef.current.has(memoryKey)) {
                console.log('⚠️ [Update] Already processed this memory:', previousItem.id);
                return prev;
              }

              console.log(`💾 [Update ${eventTime}] Storing complete memory:`, {
                previousItemId: previousItem.id,
                userMessage,
                assistantResponse
              });
              storeConversationMemory(userMessage, assistantResponse);
              processedItemsRef.current.add(memoryKey);
              const { [previousItem.id]: _, ...rest } = newMemories;
              return rest;
            }
            
            console.log(`⏳ [Update ${eventTime}] Waiting for user transcript:`, {
              previousItemId: previousItem.id,
              assistantResponse
            });
            return newMemories;
          });
        }
      }

      setItems(items);
    });

    // Debug: Track cleanup
    return () => {
      console.log('🧹 [Effect] Cleaning up event handlers');
      processedItemsRef.current.clear();
      client.reset();
    };
  }, []);

  // Canvas rendering effect
  useEffect(() => {
    let isLoaded = true;
    const audioHandler = audioHandlerRef.current;

    const render = () => {
      if (!isLoaded) return;

      const clientCanvas = clientCanvasRef.current;
      const serverCanvas = serverCanvasRef.current;

      if (clientCanvas) {
        if (!clientCanvas.width || !clientCanvas.height) {
          clientCanvas.width = clientCanvas.offsetWidth;
          clientCanvas.height = clientCanvas.offsetHeight;
        }
        const ctx = clientCanvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, clientCanvas.width, clientCanvas.height);
          const result = audioHandler.getRecorderFrequencies();
          WavRenderer.drawBars(clientCanvas, ctx, result.values, '#0099ff', 10, 0, 8);
        }
      }

      if (serverCanvas) {
        if (!serverCanvas.width || !serverCanvas.height) {
          serverCanvas.width = serverCanvas.offsetWidth;
          serverCanvas.height = serverCanvas.offsetHeight;
        }
        const ctx = serverCanvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, serverCanvas.width, serverCanvas.height);
          const result = audioHandler.getPlayerFrequencies();
          WavRenderer.drawBars(serverCanvas, ctx, result.values, '#009900', 10, 0, 8);
        }
      }

      window.requestAnimationFrame(render);
    };

    render();
    return () => {
      isLoaded = false;
    };
  }, []);

  return (
    <div data-component="ConsolePage">
      <div className="content-top">
        <div className="content-title">
          <img src="/openai-logomark.svg" alt="OpenAI Logo" />
          <span>realtime console</span>
        </div>
        <div className="content-api-key">
          {!LOCAL_RELAY_SERVER_URL && (
            <Button
              icon={Edit}
              iconPosition="end"
              buttonStyle="flush"
              label={`api key: ${apiKey.slice(0, 3)}...`}
              onClick={resetAPIKey}
            />
          )}
        </div>
      </div>
      <div className="content-main">
        <div className="content-logs">
          <div className="visualization">
            <div className="visualization-entry client">
              <canvas ref={clientCanvasRef} />
            </div>
            <div className="visualization-entry server">
              <canvas ref={serverCanvasRef} />
            </div>
          </div>

          <EventLog
            events={realtimeEvents}
            expandedEvents={expandedEvents}
            formatTime={formatTime}
            onToggleExpand={handleToggleExpand}
          />

          <ConversationView
            items={items}
            onDeleteItem={(id) => clientRef.current.deleteItem(id)}
          />

          <div className="content-actions">
            <Toggle
              defaultValue={false}
              labels={['manual', 'vad']}
              values={['none', 'server_vad']}
              onChange={(_, value) => changeTurnEndType(value)}
            />
            <div className="spacer" />
            {isConnected && canPushToTalk && (
              <Button
                label={isRecording ? 'release to send' : 'push to talk'}
                buttonStyle={isRecording ? 'alert' : 'regular'}
                disabled={!isConnected || !canPushToTalk}
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
              />
            )}
            <div className="spacer" />
            <Button
              label={isConnected ? 'disconnect' : 'connect'}
              iconPosition={isConnected ? 'end' : 'start'}
              icon={isConnected ? X : Zap}
              buttonStyle={isConnected ? 'regular' : 'action'}
              onClick={isConnected ? disconnectConversation : connectConversation}
            />
          </div>
        </div>
        <div className="content-right">
          <WeatherMap marker={marker} coords={coords} />
          <MemoryView memoryKv={memoryKv} />
        </div>
      </div>
    </div>
  );
}
