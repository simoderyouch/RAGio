import React from 'react';
import { FaRegLightbulb } from "react-icons/fa";

/**
 * Suggested Questions component for Chats
 */
export const SuggestedQuestions = React.memo(({ 
  questions, 
  totalCount, 
  showAll, 
  onToggle, 
  onSelect 
}) => {
  return (
    <div className="flex justify-start">
      <div className="max-w-[97%] w-full bg-[rgb(211,74,129,0.06)] border border-[rgb(211,74,129,0.15)] rounded-sm2 px-3 py-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-gray-800">
            <FaRegLightbulb className="text-primary" aria-hidden="true" />
            <span className="text-sm font-semibold">Suggested questions</span>
          </div>
          {totalCount > 6 && (
            <button
              type="button"
              onClick={onToggle}
              className="text-[12px] text-primary border border-primary rounded-sm2 px-2 py-1 hover:bg-primary/10 transition-colors"
              aria-label={showAll ? "Show fewer suggestions" : "Show all suggestions"}
            >
              {showAll ? "Show less" : `Show all (${totalCount})`}
            </button>
          )}
        </div>
        <ul className="flex flex-wrap gap-2">
          {questions.map((question, index) => (
            <li key={index}>
              <button
                type="button"
                onClick={() => onSelect(question)}
                className="px-3 py-1.5 rounded-full border border-gray-300 text-xs md:text-sm text-gray-700 bg-white hover:border-primary hover:bg-[rgb(211,74,129,0.06)] focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
                aria-label={`Ask: ${question}`}
              >
                <span className="font-bold mr-1">{index + 1}.</span>
                {question}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
});

SuggestedQuestions.displayName = "SuggestedQuestions";

