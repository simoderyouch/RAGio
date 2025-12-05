import { useState, useEffect } from 'react';

/**
 * Custom hook for typing animation effect
 * @param {boolean} isActive - Whether typing animation should be active
 * @param {Array} messages - Array of messages
 * @param {number} baseDelay - Base delay in milliseconds (default: 10)
 * @param {number} delayRange - Random delay range (default: 5)
 * @param {number} baseIncrement - Base increment for characters (default: 5)
 * @param {number} incrementRange - Random increment range (default: 4)
 * @returns {Object} { currentIndex, showingLetters, setShowingLetters }
 */
export const useTypingAnimation = (
  isActive,
  messages,
  baseDelay = 10,
  delayRange = 5,
  baseIncrement = 5,
  incrementRange = 4
) => {
  const [showingLetters, setShowingLetters] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!isActive) {
      setShowingLetters(false);
      setCurrentIndex(0);
      return;
    }

    let timeout;
    const lastMessage = messages[messages.length - 1];
    
    if (
      showingLetters &&
      lastMessage &&
      !lastMessage.is_user_message &&
      currentIndex < (lastMessage.message?.length || 0)
    ) {
      const randomDelay = Math.floor(Math.random() * delayRange + 1) + baseDelay;
      const randomUpdate = Math.floor(Math.random() * incrementRange + 1) + baseIncrement;
      
      timeout = setTimeout(() => {
        setCurrentIndex((prev) => prev + randomUpdate);
      }, randomDelay);
    } else {
      setShowingLetters(false);
    }
    
    return () => clearTimeout(timeout);
  }, [showingLetters, currentIndex, messages, isActive, baseDelay, delayRange, baseIncrement, incrementRange]);

  // Reset index when showingLetters changes
  useEffect(() => {
    if (showingLetters) {
      setCurrentIndex(0);
    }
  }, [showingLetters]);

  return { currentIndex, showingLetters, setShowingLetters };
};

