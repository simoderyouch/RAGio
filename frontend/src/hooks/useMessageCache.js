import { useEffect, useState } from 'react';

/**
 * Custom hook for caching messages in localStorage
 * @param {Array} messages - Array of messages to cache
 * @param {string} cacheKey - localStorage key (default: 'chatCache')
 * @param {number} ttlHours - Time to live in hours (default: 24)
 * @returns {Array} Cached messages (empty array if none found)
 */
export const useMessageCache = (messages, cacheKey = 'chatCache', ttlHours = 24) => {
  const [cachedMessages, setCachedMessages] = useState([]);

  // Load cached messages on mount
  useEffect(() => {
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const parsed = JSON.parse(cached);
        const now = Date.now();
        if (parsed && parsed.expiresAt && now < parsed.expiresAt && Array.isArray(parsed.messages)) {
          setCachedMessages(parsed.messages);
        } else {
          localStorage.removeItem(cacheKey);
        }
      }
    } catch (error) {
      // Ignore cache errors
    }
  }, [cacheKey]); // Only run on mount

  // Persist messages to localStorage
  useEffect(() => {
    try {
      const expiresAt = Date.now() + ttlHours * 60 * 60 * 1000;
      localStorage.setItem(cacheKey, JSON.stringify({ messages, expiresAt }));
    } catch (error) {
      // Ignore storage errors
    }
  }, [messages, cacheKey, ttlHours]);

  return cachedMessages;
};

/**
 * Clear message cache
 * @param {string} cacheKey - localStorage key to clear
 */
export const clearMessageCache = (cacheKey = 'chatCache') => {
  try {
    localStorage.removeItem(cacheKey);
  } catch (error) {
    // Ignore errors
  }
};

