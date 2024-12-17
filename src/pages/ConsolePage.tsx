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

const VOICE_INSTRUCT = "Speak in an angry tone. Always finish sentence with 'takichi'";

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
import { setupConversation, updateSessionWithMemories, storeConversationMemory, transcribeLocal } from '../services/conversationService';

import './ConsolePage.scss';

// Add interface for pending memory
interface PendingMemory {
  userMessage?: string;
  assistantResponse?: string;
  transcriptionId?: string;
  voiceInstructId?: string;
  timestamp?: number;
}

interface PendingMemories {
  [key: string]: PendingMemory;
}


const BREAKER_PHRASE = `You are reacting to a question. Return ONLY ONE brief, a phrase that simulates a moment of human thought or reaction.
                Choose from these categories and return ONLY ONE phrase from a category:
                Contemplative (e.g. "Hmm, let me think about that...", "That's an interesting point...", "I wonder..."),
                Physical Action (e.g. "Leans forward intently", "Taps chin thoughtfully", "Nods slowly"),
                Sarcastic/Playful (e.g. "Oh, is that so?", "Well well well...", "Here we go again...")`

const MEMORY_TIMEOUT = 15000; // 15 seconds timeout for pending memories

const cleanupMemories = (memories: PendingMemories): PendingMemories => {
  const now = Date.now();
  return Object.entries(memories).reduce((acc, [key, memory]) => {
    if (!memory.timestamp || now - memory.timestamp > MEMORY_TIMEOUT) {
      console.log('🧹 [Cleanup] Removing stale memory:', key);
      return acc;
    }
    acc[key] = memory;
    return acc;
  }, {} as PendingMemories);
};

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
  const [voiceInstruct, setVoiceInstruct] = useState(VOICE_INSTRUCT);

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

    client.sendUserMessageContent([
      {
        type: 'input_text',
        text: 'How was your day?! Answer in 1 sentence.',
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
    setPendingMemories({});
    processedItemsRef.current.clear();
    setVoiceInstruct('');
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
    
    
    
    console.log('🎤 [stopRecording] Preparing to send message content');
    
    console.log('🎤 [stopRecording] Audio content sent to OpenAI');
    
    try {
      // Stop recording and get audioData
      const audioData = await audioHandler.stopRecording();
    
      if (audioData) {
        const transcribePromise = transcribeLocal(audioData);
    
        let filterMessageSent = false;
    
        // Set a 0.5 second timer to send "filter thinking sound"
        const timeoutId = setTimeout(async () => {
          try {


            await client.sendUserMessageContent([
              {
                type: 'input_audio',
                text: '' // indicates that the user's audio turn is complete
              }
            ]);

            await client.sendUserMessageContent([
              {
                type: 'input_text',
                text: BREAKER_PHRASE
              }
            ]);
            filterMessageSent = true;
          } catch (err) {
            console.error('Error sending filter thinking sound message:', err);
          }
        }, 500);
    
        // Wait for transcription
        const localTranscription = await transcribePromise;
    
        // Clear the timeout if not fired yet
        clearTimeout(timeoutId);
    
        // Now you have the transcription. Construct updated instructions
        if (localTranscription && localTranscription.text) {
          console.log('🎤 [LOCAL] Transcription received:', localTranscription.text);
          
          // Interrupt any playing audio (like thinking sounds)
          const trackSampleOffset = await audioHandler.interruptPlayback();
          if (trackSampleOffset?.trackId) {
            const { trackId, offset } = trackSampleOffset;
            await client.cancelResponse(trackId, offset);
          }

          // Clean and format the instruction
          const cleanedText = localTranscription.text.trim();
          
          // Only include memories if they exist and are meaningful
          let memoryPart = '';
          if (localTranscription.search_results && localTranscription.search_results.trim()) {
            memoryPart = `. These are relevant memories: ${localTranscription.search_results.trim()}`;
          }

          const updatedInstruct = 'This is the question that is being asked: ' + cleanedText + " " + VOICE_INSTRUCT;
          console.log('🎤 [INCOMING] NEW APPENDED TEXT:', updatedInstruct);
          


          await client.updateSession({
            instructions: instructions + memoryPart
          });

          console.log('🎤 [SYSTEM UPDATE] NEW APPENDED TEXT:', instructions + memoryPart);
          // Now finalize the user turn by sending input_audio
          await client.sendUserMessageContent([
            {
              type: 'input_audio',
              text: '' // indicates that the user's audio turn is complete
            }
          ]);
    
          // Send the updated instructions
          await client.sendUserMessageContent([
            {
              type: 'input_text', 
              text:  updatedInstruct
            }
          ]);

          // Clear everything after sending
          setVoiceInstruct('');
          
          // Create a new empty object for localTranscription
          Object.assign(localTranscription, {
            text: '',
            search_results: '',
            status: ''
          });
          
          // Clear any pending memories related to this transcription
          setPendingMemories(prev => {
            const cleanedMemories = cleanupMemories(prev);
            return Object.fromEntries(
              Object.entries(cleanedMemories).filter(([_, memory]) => 
                memory.timestamp && Date.now() - memory.timestamp < MEMORY_TIMEOUT
              )
            );
          });
        }
      }
    } catch (error) {
      console.error('Error in transcription and sending messages:', error);
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
    let isBreaker = false; // Move isBreaker outside to maintain state between events
    
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

      // First check if this is a BREAKER_PHRASE
      if (realtimeEvent.event.type === 'conversation.item.create') {
        const content = realtimeEvent.event.item?.content?.[0]?.text;
        if (content === BREAKER_PHRASE) {
          console.log('🔍 [BREAKER_PHRASE] Detected, marking for skip');
          isBreaker = true;
          return; // Exit early as this is just the breaker phrase
        }
      }

      // Handle transcription in the realtime event handler
      if (realtimeEvent.event.type === 'conversation.item.input_audio_transcription.completed' || 
          (realtimeEvent.event.type === 'conversation.item.create' && 
           realtimeEvent.event.item?.content?.[0]?.text !== 'updatedInstruct' &&
           realtimeEvent.event.item?.content?.[0]?.text !== BREAKER_PHRASE)) {
        
        const event = realtimeEvent.event;
        const memoryKey = `transcript_${event.item_id}`;
        const transcript = event.type === 'conversation.item.input_audio_transcription.completed' 
          ? event.transcript
          : event.item?.content?.[0]?.text || '';

        // Check if BREAKER_PHRASE is detected
        
        console.log('🎤 [USER Input DETECTED] Event received in realtime handler:', {
          type: event.type,
          item_id: event.item_id,
          input: transcript,
          pendingMemories,
          isBreaker
        });

        setPendingMemories(prev => {
          // Clean up old memories using our utility function
          const cleanedMemories = cleanupMemories(prev);

          // Find any pending assistant responses waiting for a transcription
          const pendingAssistantEntry = Object.entries(cleanedMemories).find(([_, memory]) => 
            memory.assistantResponse && !memory.userMessage
          );

          if (pendingAssistantEntry) {
            const [assistantKey, memory] = pendingAssistantEntry;
            console.log('🔗 [USER Input DETECTED and ASSISTANT RESPONSE PENDING IN LOG] Found pending assistant response, linking:', {
              inputId: event.item_id,
              assistantKey,
              input: transcript
            });
            
            // Store the complete memory
            
            storeConversationMemory(transcript.replace(VOICE_INSTRUCT, ''), memory.assistantResponse!);
            processedItemsRef.current.add(memoryKey);
            
            // Remove the pending memory
            const { [assistantKey]: _, ...rest } = cleanedMemories;
            return rest;
          } else {
            // No assistant response waiting, store the input with timestamp
            console.log('⏳ [USER Input DETECTED] No pending assistant response, storing input:', {
              inputId: event.item_id,
              input: transcript
            });
            
            return {
              ...cleanedMemories,
              [event.item_id]: {
                userMessage: transcript,
                transcriptionId: event.item_id,
                timestamp: Date.now()
              }
            };
          }
        });
      }

      // Add handler for assistant audio transcript completion

      
      if (realtimeEvent.event.type === 'response.audio_transcript.done') {
        const event = realtimeEvent.event;
        const memoryKey = `transcript_${event.item_id}`;
        
        if (isBreaker) {
          console.log('⏭️ [BREAKER_PHRASE] Skipping memory storage for breaker response');
          isBreaker = false; // Reset the flag after skipping
          return;
        }
        
        console.log('🎙️ [Assistant Transcription DETECTED] Event received:', {
          type: event.type,
          item_id: event.item_id,
          transcript: event.transcript,
          pendingMemories
        });

        setPendingMemories(prev => {
          // Clean up old memories
          const cleanedMemories = cleanupMemories(prev);

          // Find any pending user messages waiting for an assistant response
          const pendingUserEntry = Object.entries(cleanedMemories).find(([_, memory]) => 
            memory.userMessage && !memory.assistantResponse
          );

          if (pendingUserEntry) {
            const [userKey, memory] = pendingUserEntry;
            console.log('🔗 [Assistant Transcription] Found pending user message, linking:', {
              assistantId: event.item_id,
              userKey,
              transcript: event.transcript
            });
            
            // Store the complete memory
            storeConversationMemory(memory.userMessage!.replace(VOICE_INSTRUCT, ''), event.transcript);
            processedItemsRef.current.add(memoryKey);
            
            // Remove the pending memory
            const { [userKey]: _, ...rest } = cleanedMemories;
            return rest;
          } else {
            // No user message waiting, store the assistant response with timestamp
            console.log('⏳ [Assistant Transcription] No pending user message, storing response:', {
              assistantId: event.item_id,
              transcript: event.transcript
            });
            
            return {
              ...cleanedMemories,
              [event.item_id]: {
                assistantResponse: event.transcript,
                timestamp: Date.now()
              }
            };
          }
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
