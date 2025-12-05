import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useParams } from "react-router-dom";
import useFetch from "../hooks/useFetch";
import useAxiosPrivate from "../hooks/useAxiosPrivate";
import { useTypingAnimation } from "../hooks/useTypingAnimation";
import { ChatsMessages } from "./Chats/ChatsMessages";
import { ChatsInput } from "./Chats/ChatsInput";
import { SuggestedQuestions } from "./Chats/SuggestedQuestions";

const FALLBACK_QUESTIONS = [
  "Give me a brief summary.",
  "List the key points with bullets.",
  "What are the main entities (names, dates, amounts)?",
  "What are the conclusions or recommendations?",
  "Are there any action items or deadlines?",
];

function Chats({ fileData }) {
  const { id } = useParams();
  const {
    data: messagesData,
    isLoading: messagesIsLoading,
    fetchData,
  } = useFetch(`/api/chat/messages/${id}`);
  
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [pdfSummary, setPdfSummary] = useState("");
  const [pdfQuestions, setPdfQuestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showAllSuggestions, setShowAllSuggestions] = useState(false);
  
  const axiosInstance = useAxiosPrivate();
  const chatEndRef = useRef(null);
  
  // Use typing animation hook
  const { currentIndex, showingLetters, setShowingLetters } = useTypingAnimation(
    messages.length > 0 && !messages[messages.length - 1]?.is_user_message,
    messages,
    10, // baseDelay
    5,  // delayRange
    5,  // baseIncrement
    4   // incrementRange
  );

  // Parse messages data
  useEffect(() => {
    if (messagesIsLoading || !Array.isArray(messagesData)) return;

    if (messagesData.length === 0) {
      setPdfSummary("");
      setPdfQuestions([]);
      setMessages([]);
      return;
    }

    // Summary (first item)
    setPdfSummary(messagesData[0]?.message ?? "");

    // Questions (second item)
    let parsedQuestions = [];
    const rawQuestions = messagesData[1]?.message;
    
    if (typeof rawQuestions === "string") {
      try {
        parsedQuestions = JSON.parse(rawQuestions);
      } catch {
        parsedQuestions = [];
      }
    }

    const normalizedQuestions = Array.isArray(parsedQuestions)
      ? parsedQuestions.map((q) => (typeof q === "string" ? q : JSON.stringify(q)))
      : [];

    setPdfQuestions(normalizedQuestions.length > 0 ? normalizedQuestions : FALLBACK_QUESTIONS);

    // History: from the third element onward
    setMessages(messagesData.slice(2));
  }, [messagesData, messagesIsLoading]);

  // Refetch when file gets processed
  const fileProcessed = fileData?.processed;
  useEffect(() => {
    if (fileProcessed) fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileProcessed]);


  const handleSubmit = useCallback(async (questionText = "", task = "response") => {
    const finalQuestion = typeof questionText === "string" && questionText.trim() 
      ? questionText.trim() 
      : question.trim();
    
    // Prevent empty submissions
    if (!finalQuestion) return;

    setShowingLetters(false);
    setIsLoading(true);
    
    const timestamp = new Date().toISOString();
    
    // Add user message optimistically
    setMessages((prev) => [
      ...prev,
      { message: finalQuestion, is_user_message: true, create_at: timestamp },
    ]);
    setQuestion("");

    try {
      const response = await axiosInstance.post(`/api/chat/${id}`, {
        question: finalQuestion,
        language: "Auto-detect",
        model: "Mistral",
        document: id,
        task,
      });

      // Add AI response
      const newMessage = {
        message: response.data.message,
        is_user_message: false,
        create_at: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, newMessage]);
      setShowingLetters(true); // Trigger typing animation
    } catch (error) {
      // Error submitting question
    } finally {
      setIsLoading(false);
    }
  }, [question, axiosInstance, id]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  const handleQuestionChange = useCallback((e) => {
    setQuestion(e.target.value);
  }, []);

  const toggleSuggestions = useCallback(() => {
    setShowAllSuggestions((prev) => !prev);
  }, []);

  // Memoize displayed questions
  const displayedQuestions = useMemo(() => 
    showAllSuggestions ? pdfQuestions : pdfQuestions.slice(0, 6),
    [showAllSuggestions, pdfQuestions]
  );

  const isDisabled = isLoading || (fileData && !fileData.processed);
  const showSuggestions = !showingLetters && !isLoading && pdfQuestions.length > 0;

  return (
    <div className="bg-white relative flex flex-col border pt-2 w-full h-full">
      {/* Messages Container */}
      <div 
        className="flex flex-1 overflow-y-auto w-full flex-col py-5 px-3 gap-5" 
        aria-live="polite"
        aria-label="Chat messages"
      >
        <ChatsMessages
          messages={messages}
          messagesIsLoading={messagesIsLoading}
          isLoading={isLoading}
          pdfSummary={pdfSummary}
          showingLetters={showingLetters}
          currentIndex={currentIndex}
          chatEndRef={chatEndRef}
        />

        {/* Suggested Questions */}
        {showSuggestions && (
          <SuggestedQuestions
            questions={displayedQuestions}
            totalCount={pdfQuestions.length}
            showAll={showAllSuggestions}
            onToggle={toggleSuggestions}
            onSelect={handleSubmit}
          />
        )}
      </div>

      {/* Input Area */}
      <ChatsInput
        question={question}
        setQuestion={setQuestion}
        isLoading={isLoading}
        isDisabled={isDisabled}
        onSubmit={() => handleSubmit()}
        onKeyDown={handleKeyDown}
      />
    </div>
  );
}


export default Chats;
