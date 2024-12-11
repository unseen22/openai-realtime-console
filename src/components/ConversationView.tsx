import React from 'react';
import { X } from 'react-feather';
import { ItemType } from '@openai/realtime-api-beta/dist/lib/client.js';

interface ConversationViewProps {
  items: ItemType[];
  onDeleteItem: (id: string) => void;
}

export const ConversationView: React.FC<ConversationViewProps> = ({
  items,
  onDeleteItem,
}) => {
  return (
    <div className="content-block conversation">
      <div className="content-block-title">conversation</div>
      <div className="content-block-body" data-conversation-content>
        {!items.length && `awaiting connection...`}
        {items.map((conversationItem) => {
          return (
            <div className="conversation-item" key={conversationItem.id}>
              <div className={`speaker ${conversationItem.role || ''}`}>
                <div>
                  {(conversationItem.role || conversationItem.type).replaceAll(
                    '_',
                    ' '
                  )}
                </div>
                <div
                  className="close"
                  onClick={() => onDeleteItem(conversationItem.id)}
                >
                  <X />
                </div>
              </div>
              <div className={`speaker-content`}>
                {/* tool response */}
                {conversationItem.type === 'function_call_output' && (
                  <div>{conversationItem.formatted.output}</div>
                )}
                {/* tool call */}
                {!!conversationItem.formatted.tool && (
                  <div>
                    {conversationItem.formatted.tool.name}(
                    {conversationItem.formatted.tool.arguments})
                  </div>
                )}
                {!conversationItem.formatted.tool &&
                  conversationItem.role === 'user' && (
                    <div>
                      {conversationItem.formatted.transcript ||
                        (conversationItem.formatted.audio?.length
                          ? '(awaiting transcript)'
                          : conversationItem.formatted.text || '(item sent)')}
                    </div>
                  )}
                {!conversationItem.formatted.tool &&
                  conversationItem.role === 'assistant' && (
                    <div>
                      {conversationItem.formatted.transcript ||
                        conversationItem.formatted.text ||
                        '(truncated)'}
                    </div>
                  )}
                {conversationItem.formatted.file && (
                  <audio src={conversationItem.formatted.file.url} controls />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}; 