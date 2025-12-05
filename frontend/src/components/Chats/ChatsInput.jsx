import React from 'react';
import { LuSend } from "react-icons/lu";
import AutoResizableTextarea from '../ui/AutoResizableTextarea';

/**
 * Input component for Chats
 */
export const ChatsInput = React.memo(({
  question,
  setQuestion,
  isLoading,
  isDisabled,
  onSubmit,
  onKeyDown,
}) => {
  return (
    <div className="flex flex-col left-0 bottom-0 w-full bg-white p-3">
      <div className="flex items-end p-2 border border-gray-150 rounded-sm2 w-full relative">
        <AutoResizableTextarea
          placeholder="Saisissez votre question ici..."
          value={question}
          handleInput={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={isDisabled}
          aria-label="Type your question"
        />
        <div className="right-2 flex items-center gap-2 bottom-2">
          <button
            type="submit"
            onClick={onSubmit}
            disabled={isDisabled}
            className={`bg-primary text-white rounded-sm2 w-9 h-9 flex justify-center items-center transition-colors ${
              isDisabled ? "!bg-gray-400 cursor-not-allowed" : "hover:bg-primary/90"
            }`}
            aria-label="Send message"
          >
            <LuSend className="text-xl" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
});

ChatsInput.displayName = "ChatsInput";

