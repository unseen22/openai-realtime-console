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
import { setupConversation, updateSessionWithMemories } from '../services/conversationService';

import './ConsolePage.scss';

export function ConsolePage() {
  // State
  const [items, setItems] = useState<ItemType[]>([]);
  const [realtimeEvents, setRealtimeEvents] = useState<RealtimeEvent[]>([]);
  const [expandedEvents, setExpandedEvents] = useState<{ [key: string]: boolean }>({});
  const [isConnected, setIsConnected] = useState(false);
  const [canPushToTalk, setCanPushToTalk] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [memoryKv, setMemoryKv] = useState<MemoryKV>({});
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
        text: 'How was your day?!',
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
    setIsRecording(false);
    const client = clientRef.current;
    const audioHandler = audioHandlerRef.current;

    await audioHandler.stopRecording();
    client.createResponse();
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

    // Set up event handlers
    client.on('realtime.event', (realtimeEvent: RealtimeEvent) => {
      setRealtimeEvents((prev) => {
        const lastEvent = prev[prev.length - 1];
        if (lastEvent?.event.type === realtimeEvent.event.type) {
          lastEvent.count = (lastEvent.count || 0) + 1;
          return prev.slice(0, -1).concat(lastEvent);
        }
        return prev.concat(realtimeEvent);
      });
    });

    client.on('error', (event: any) => console.error(event));
    client.on('conversation.interrupted', async () => {
      const audioHandler = audioHandlerRef.current;
      const trackSampleOffset = await audioHandler.interruptPlayback();
      if (trackSampleOffset?.trackId) {
        const { trackId, offset } = trackSampleOffset;
        await client.cancelResponse(trackId, offset);
      }
    });

    client.on('conversation.updated', async ({ item, delta }: any) => {
      const items = client.conversation.getItems();
      const audioHandler = audioHandlerRef.current;

      if (delta?.audio) {
        audioHandler.playAudio(delta.audio, item.id);
      }

      if (item.status === 'completed' && item.formatted.audio?.length) {
        const wavFile = await AudioHandler.decodeAudio(item.formatted.audio);
        item.formatted.file = wavFile;
      }

      setItems(items);
    });

    setItems(client.conversation.getItems());

    return () => {
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
