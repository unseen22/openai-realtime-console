import React, { useRef } from 'react';
import { ArrowUp, ArrowDown } from 'react-feather';
import { RealtimeEvent } from '../types/console';

interface EventLogProps {
  events: RealtimeEvent[];
  expandedEvents: { [key: string]: boolean };
  formatTime: (timestamp: string) => string;
  onToggleExpand: (eventId: string) => void;
}

export const EventLog: React.FC<EventLogProps> = ({
  events,
  expandedEvents,
  formatTime,
  onToggleExpand,
}) => {
  const eventsScrollRef = useRef<HTMLDivElement>(null);

  return (
    <div className="content-block events">
      <div className="content-block-title">events</div>
      <div className="content-block-body" ref={eventsScrollRef}>
        {!events.length && `awaiting connection...`}
        {events.map((realtimeEvent) => {
          const count = realtimeEvent.count;
          const event = { ...realtimeEvent.event };
          if (event.type === 'input_audio_buffer.append') {
            event.audio = `[trimmed: ${event.audio.length} bytes]`;
          } else if (event.type === 'response.audio.delta') {
            event.delta = `[trimmed: ${event.delta.length} bytes]`;
          }
          return (
            <div className="event" key={event.event_id}>
              <div className="event-timestamp">
                {formatTime(realtimeEvent.time)}
              </div>
              <div className="event-details">
                <div
                  className="event-summary"
                  onClick={() => onToggleExpand(event.event_id)}
                >
                  <div
                    className={`event-source ${
                      event.type === 'error' ? 'error' : realtimeEvent.source
                    }`}
                  >
                    {realtimeEvent.source === 'client' ? (
                      <ArrowUp />
                    ) : (
                      <ArrowDown />
                    )}
                    <span>
                      {event.type === 'error' ? 'error!' : realtimeEvent.source}
                    </span>
                  </div>
                  <div className="event-type">
                    {event.type}
                    {count && ` (${count})`}
                  </div>
                </div>
                {!!expandedEvents[event.event_id] && (
                  <div className="event-payload">
                    {JSON.stringify(event, null, 2)}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}; 