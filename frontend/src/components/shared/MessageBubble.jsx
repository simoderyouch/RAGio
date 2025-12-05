import React from 'react';
import parse from 'html-react-parser';
import sanitizeHtml from '../../utils/sanitizeHtml';
import { time } from '../../utils/time';

/**
 * Shared MessageBubble component for consistent message rendering
 * @param {Object} props
 * @param {boolean} props.isUser - Whether the message is from the user
 * @param {string} props.content - Message content
 * @param {string} props.timestamp - Message timestamp
 * @param {boolean} props.showTyping - Whether to show typing animation
 * @param {number} props.typingIndex - Current typing index
 * @param {Array} props.documentsUsed - Array of documents used (optional)
 * @param {React.Ref} props.chatEndRef - Ref to scroll to bottom
 * @param {boolean} props.isLastMessage - Whether this is the last message
 */
export const MessageBubble = React.memo(({
  isUser,
  content,
  timestamp,
  showTyping = false,
  typingIndex = 0,
  documentsUsed = null,
  chatEndRef = null,
  isLastMessage = false,
}) => {
  const displayContent = showTyping && isLastMessage
    ? content.slice(0, typingIndex + 1)
    : content;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        ref={isLastMessage ? chatEndRef : null}
        className={`max-w-[80%] rounded-2xl px-5 py-3 ${
          isUser
            ? "bg-primary text-white rounded-br-md"
            : "bg-gray-100 text-gray-800 rounded-bl-md"
        }`}
        role="article"
        aria-label={isUser ? "Your message" : "Assistant message"}
      >
        <div className="text-sm">
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{displayContent}</p>
          ) : (
            <div>
              {documentsUsed && documentsUsed.length > 0 && (
                <div className="mb-3 p-2.5 rounded-lg text-xs flex flex-wrap items-center gap-2 bg-primary/10">
                  <span className="text-primary font-medium flex items-center gap-1">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                      <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
                    </svg>
                    Sources:
                  </span>
                  {documentsUsed.slice(0, 5).map((doc, i) => (
                    <span 
                      key={doc.id || i} 
                      className="px-2 py-0.5 bg-primary/20 text-primary rounded text-[11px]"
                    >
                      {doc.name?.split('.')[0].slice(0, 15) || doc}
                    </span>
                  ))}
                  {documentsUsed.length > 5 && (
                    <span className="text-gray-500">+{documentsUsed.length - 5} others</span>
                  )}
                </div>
              )}
              <div className="prose prose-sm max-w-none response_style">
                {parse(sanitizeHtml(displayContent))}
              </div>
            </div>
          )}
        </div>
        {timestamp && (
          <div className={`text-xs mt-2 ${isUser ? "text-white/70" : "text-gray-400"}`}>
            {time(timestamp)}
          </div>
        )}
      </div>
    </div>
  );
});

MessageBubble.displayName = "MessageBubble";

