import React, { useState, useRef, useEffect } from "react";

function AutoResizableTextarea({handleInput, value, placeholder, onKeyDown, disabled = false}) {
  
  const textareaRef = useRef(null);

  // Automatically resize the textarea to fit its content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textareaRef && textarea) {
      textarea.style.height = "auto"; // Reset height to auto to recalculate scroll height
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`; // Set height to the scroll height with max height
    }
  }, [value]);

  return (
    <textarea
      ref={textareaRef}
      className={`w-full border-0 bg-transparent text-sm focus:ring-0 focus:border-0 outline-none resize-none transition-all duration-200 ${
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-text'
      }`}
      placeholder={placeholder}
      value={value}
      onChange={handleInput}
      onKeyDown={onKeyDown}
      disabled={disabled}
      style={{
        minHeight: '20px',
        maxHeight: '120px',
        lineHeight: '1.5'
      }}
    />
  );
}

export default AutoResizableTextarea;
