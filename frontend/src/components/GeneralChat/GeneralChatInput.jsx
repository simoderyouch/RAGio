import React from 'react';
import { LuSend } from "react-icons/lu";
import AutoResizableTextarea from '../ui/AutoResizableTextarea';

/**
 * Input component for GeneralChat
 */
export const GeneralChatInput = React.memo(({
  question,
  setQuestion,
  isLoading,
  includedFilesCount,
  onSubmit,
  onKeyPress,
}) => {
  return (
    <div className="p-4 border-t border-gray-100 bg-gray-50/50">
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <div className={`bg-white rounded-xl border border-gray-200 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all ${isLoading ? 'opacity-50' : ''}`}>
            <AutoResizableTextarea
              value={question}
              handleInput={(e) => setQuestion(e.target.value)}
              onKeyDown={onKeyPress}
              placeholder={
                includedFilesCount === 0
                  ? "Incluez au moins un document pour poser une question..."
                  : `Posez une question sur vos ${includedFilesCount} document${includedFilesCount > 1 ? 's' : ''}...`
              }
              className="w-full p-4 text-sm resize-none bg-transparent focus:outline-none"
              disabled={isLoading}
              aria-label="Type your question"
            />
          </div>
        </div>
        <button
          onClick={onSubmit}
          disabled={isLoading || !question.trim() || includedFilesCount === 0}
          className={`w-12 h-12 rounded-xl flex justify-center items-center transition-all duration-200 ${
            isLoading || includedFilesCount === 0 || !question.trim()
              ? "bg-gray-200 text-gray-400 cursor-not-allowed"
              : "bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/30 hover:shadow-xl hover:shadow-primary/40"
          }`}
          aria-label="Send message"
        >
          <LuSend className="text-xl" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
});

GeneralChatInput.displayName = "GeneralChatInput";

