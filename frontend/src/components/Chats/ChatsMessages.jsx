import React, { useEffect } from 'react';
import { MessageBubble } from '../shared/MessageBubble';
import Loading from '../ui/Loading';

/**
 * Messages component for Chats
 */
export const ChatsMessages = React.memo(({
  messages,
  messagesIsLoading,
  isLoading,
  pdfSummary,
  showingLetters,
  currentIndex,
  chatEndRef,
}) => {
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "auto", block: "end" });
  }, [messages, currentIndex, chatEndRef]);

  if (messagesIsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loading padding={3} />
      </div>
    );
  }

  return (
    <>
      {/* Summary Block */}
      {pdfSummary && (
        <MessageBubble 
          isUser={false} 
          content={pdfSummary}
          timestamp={null}
        />
      )}

      {/* Chat Messages */}
      {messages.map((message, index) => {
        const isLastMessage = index === messages.length - 1;

        return (
          <MessageBubble
            key={`${message.id || index}-${message.create_at}`}
            isUser={message.is_user_message}
            content={message.message}
            timestamp={message.create_at}
            showTyping={showingLetters && isLastMessage}
            typingIndex={currentIndex}
            chatEndRef={isLastMessage ? chatEndRef : null}
            isLastMessage={isLastMessage}
            documentsUsed={message.documents_used}
          />
        );
      })}

      {/* Loading Indicator */}
      {isLoading && (
        <div className="flex justify-start">
          <div className="max-w-[73%] text-sm py-2 rounded-md px-3 flex gap-3 items-center">
            <Loading color="#9ca3af" />
          </div>
        </div>
      )}
      <div ref={chatEndRef} />
    </>
  );
});

ChatsMessages.displayName = "ChatsMessages";

