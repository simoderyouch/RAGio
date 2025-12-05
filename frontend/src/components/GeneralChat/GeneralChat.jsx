import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import useFetch from "../../hooks/useFetch";
import Loading from "../ui/Loading";
import useAxiosPrivate from "../../hooks/useAxiosPrivate";
import { RiDeleteBin6Line } from "react-icons/ri";
import { HiOutlineSparkles } from "react-icons/hi";
import { useToast } from "../Toast/ToastContext";
import { useTypingAnimation } from "../../hooks/useTypingAnimation";
import { useMessageCache, clearMessageCache } from "../../hooks/useMessageCache";
import { useFileHelpers } from "../../hooks/useFileHelpers";
import { GeneralChatSidebar } from "./GeneralChatSidebar";
import { GeneralChatMessages } from "./GeneralChatMessages";
import { GeneralChatInput } from "./GeneralChatInput";

// Constants
const POLL_INTERVAL = 3000; // 3 seconds
const POLL_TIMEOUT = 120000; // 2 minutes

function GeneralChat() {
  const {
    data: filesData,
    error: filesError,
    isLoading: filesIsLoading,
    fetchData: fetchFiles,
  } = useFetch('/api/document/files');

  const [excludedFiles, setExcludedFiles] = useState([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [language, setLanguage] = useState("Auto-detect");
  const [model, setModel] = useState("Mistral");
  const [messages, setMessages] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [processing, setProcessing] = useState({});
  const chatEndRef = useRef(null);
  const axiosInstance = useAxiosPrivate();
  const toast = useToast();
  
  // Use custom hooks
  useMessageCache(messages, 'generalChatCache', 24);
  const { allFiles, processedFiles, unprocessedFiles } = useFileHelpers(filesData);
  const { currentIndex, showingLetters, setShowingLetters } = useTypingAnimation(
    messages.length > 0 && !messages[messages.length - 1]?.is_user_message, // isActive
    messages,
    10, // baseDelay
    5,  // delayRange
    5,  // baseIncrement
    4   // incrementRange
  );
  
  // Track file processing statuses: { fileId: { status, message, error, startTime } }
  const [fileStatuses, setFileStatuses] = useState({});
  // Store interval IDs for cleanup
  const pollIntervalsRef = useRef({});

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollIntervalsRef.current).forEach(intervalId => {
        clearInterval(intervalId);
      });
    };
  }, []);

  // Check initial statuses when files load (for files that might be processing)
  useEffect(() => {
    if (!filesData || filesIsLoading) return;

    const checkInitialStatuses = async () => {
      const allFileIds = [];
      Object.values(filesData).forEach(fileList => {
        fileList.forEach(file => {
          // Only check files that aren't already marked as processed
          if (!file.processed) {
            allFileIds.push(file.id);
          }
        });
      });

      // Check status for unprocessed files
      for (const fileId of allFileIds) {
        try {
          const response = await axiosInstance.get(`/api/document/process/status/${fileId}`);
          const statusData = response.data;
          
          // If file is currently processing, start polling
          if (statusData.status === 'processing') {
            setFileStatuses(prev => ({
              ...prev,
              [fileId]: { ...statusData, startTime: Date.now() }
            }));
            startPolling(fileId);
          }
        } catch (error) {
          // Ignore errors for initial check
        }
      }
    };

    checkInitialStatuses();
  }, [filesData, filesIsLoading, axiosInstance]);

  // Load files and restore cached messages
  useEffect(() => {
    fetchFiles();
    // Load cached messages on mount
    try {
      const cached = localStorage.getItem('generalChatCache');
      if (cached) {
        const parsed = JSON.parse(cached);
        const now = Date.now();
        if (parsed && parsed.expiresAt && now < parsed.expiresAt && Array.isArray(parsed.messages)) {
          setMessages(parsed.messages);
        } else {
          localStorage.removeItem('generalChatCache');
        }
      }
    } catch (_) {
      // ignore cache errors
    }
  }, [fetchFiles]);

  // Files that are currently included (not excluded)
  const includedFiles = useMemo(() => 
    processedFiles.filter(f => !excludedFiles.includes(f.id)),
    [processedFiles, excludedFiles]
  );

  // Toggle file inclusion/exclusion
  const handleFileToggle = useCallback((fileId) => {
    setExcludedFiles(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId)  // Remove from excluded (include it)
        : [...prev, fileId]                  // Add to excluded (exclude it)
    );
  }, []);

  // Include all files (clear exclusions)
  const handleIncludeAll = useCallback(() => {
    setExcludedFiles([]);
  }, []);

  // Exclude all files
  const handleExcludeAll = useCallback(() => {
    setExcludedFiles(processedFiles.map(f => f.id));
  }, [processedFiles]);

  const handleSubmit = async (question_p = "") => {
    const activeFilesCount = includedFiles.length;
    
    if (activeFilesCount === 0) {
      alert("Veuillez inclure au moins un document pour discuter.");
      return;
    }

    const finalQuestion = question_p.trim() || question.trim();
    if (!finalQuestion) {
      alert("Veuillez saisir une question.");
      return;
    }

    setShowingLetters(false);
    setIsLoading(true);
    const currentTime = new Date();
    const formattedTime = currentTime.toISOString();
    
    setMessages([
      ...messages,
      { message: finalQuestion, is_user_message: true, create_at: formattedTime },
    ]);
    
    setQuestion("");

    try {
      const requestData = {
        question: finalQuestion,
        excluded_file_ids: excludedFiles,
        language: language,
        model: model,
      };
      
      const response = await axiosInstance.post('/api/chat/general', requestData);
      
      const responseTime = new Date();
      const responseFormattedTime = responseTime.toISOString();
      
      const newMessage = {
        message: response.data.message,
        is_user_message: false,
        create_at: responseFormattedTime,
        documents_used: response.data.documents_used,
        total_documents: response.data.total_documents,
      };
      
      setMessages((prevMessages) => [...prevMessages, newMessage]);
      setShowingLetters(true); // Trigger typing animation
    } catch (error) {
      const errorMessage = error.response?.data?.detail || "Une erreur s'est produite. Veuillez réessayer.";
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          message: errorMessage,
          is_user_message: false,
          create_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Poll status for a specific file
  const pollStatus = async (fileId) => {
    try {
      const response = await axiosInstance.get(`/api/document/process/status/${fileId}`);
      const statusData = response.data;

      setFileStatuses(prev => {
        const currentStatus = prev[fileId] || {};
        const startTime = currentStatus.startTime || Date.now();
        const wasProcessing = currentStatus.status === 'processing';
        
        // Check for timeout
        if (Date.now() - startTime > POLL_TIMEOUT) {
          stopPolling(fileId);
          toast.error('Processing timed out. Please try again.', 'Timeout');
          return {
            ...prev,
            [fileId]: {
              ...statusData,
              status: 'failed',
              error: 'Processing timed out. Please try again.',
              startTime
            }
          };
        }

        // Stop polling if completed or failed
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          stopPolling(fileId);
          // Refresh file list to get updated processed status
          if (statusData.status === 'completed') {
            fetchFiles();
            // Only show toast if it was previously processing (not on initial load)
            if (wasProcessing) {
              toast.success('Document processed successfully! Ready to chat.', 'Complete');
            }
          } else if (statusData.status === 'failed' && wasProcessing) {
            toast.error(statusData.error || 'Processing failed. Please try again.', 'Failed');
          }
        }

        return {
          ...prev,
          [fileId]: { ...statusData, startTime }
        };
      });

      return statusData;
    } catch (error) {
      return null;
    }
  };

  // Stop polling for a file
  const stopPolling = (fileId) => {
    if (pollIntervalsRef.current[fileId]) {
      clearInterval(pollIntervalsRef.current[fileId]);
      delete pollIntervalsRef.current[fileId];
    }
  };

  // Start polling for a file
  const startPolling = (fileId) => {
    // Clear any existing polling for this file
    stopPolling(fileId);

    // Start new polling interval
    pollIntervalsRef.current[fileId] = setInterval(() => {
      pollStatus(fileId);
    }, POLL_INTERVAL);
  };

  // Handle file processing
  const handleProcessFile = async (fileId) => {
    try {
      // Set initial processing state
      setFileStatuses(prev => ({
        ...prev,
        [fileId]: { 
          status: 'processing', 
          message: 'Starting processing...',
          startTime: Date.now()
        }
      }));

      setProcessing(prev => ({ ...prev, [fileId]: true }));
      toast.info('Processing started. This may take a few moments...', 'Processing');

      // Call the process endpoint
      const response = await axiosInstance.get(`/api/document/process/${fileId}`);
      const result = response.data;

      if (result.status === 'completed') {
        // Already completed
        setFileStatuses(prev => ({
          ...prev,
          [fileId]: { ...result, startTime: prev[fileId]?.startTime }
        }));
        await fetchFiles();
        toast.success('Document processed successfully!', 'Complete');
      } else if (result.status === 'processing' || result.status === 'started' || result.status === 'pending') {
        // Start polling
        setFileStatuses(prev => ({
          ...prev,
          [fileId]: { 
            ...result, 
            status: 'processing',
            message: result.message || 'Processing document...',
            startTime: prev[fileId]?.startTime 
          }
        }));
        startPolling(fileId);
        // Do an immediate status check
        await pollStatus(fileId);
      }
    } catch (error) {
      setFileStatuses(prev => ({
        ...prev,
        [fileId]: { 
          status: 'failed', 
          error: error.response?.data?.detail || 'Failed to start processing'
        }
      }));
      toast.error(
        error.response?.data?.detail || 'Failed to start processing. Please try again.',
        'Processing Failed'
      );
    } finally {
      setProcessing(prev => ({ ...prev, [fileId]: false }));
    }
  };

  const clearChat = useCallback(() => {
    setMessages([]);
    clearMessageCache('generalChatCache');
  }, []);

  if (filesIsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loading padding={3} />
      </div>
    );
  }

  return (
    <div className="flex h-full bg-white rounded-xl shadow-sm overflow-hidden">
      {/* Sidebar: Documents */}
      <GeneralChatSidebar
        sidebarCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed}
        includedFiles={includedFiles}
        processedFiles={processedFiles}
        unprocessedFiles={unprocessedFiles}
        excludedFiles={excludedFiles}
        fileStatuses={fileStatuses}
        onFileToggle={handleFileToggle}
        onIncludeAll={handleIncludeAll}
        onExcludeAll={handleExcludeAll}
        onProcessFile={handleProcessFile}
      />

      {/* Chat panel */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-md shadow-primary/20">
              <HiOutlineSparkles className="text-white text-xl" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">Chat Général</h2>
              <p className="text-xs text-gray-500">
                {includedFiles.length === processedFiles.length 
                  ? `Tous les documents (${processedFiles.length})`
                  : `${includedFiles.length} document${includedFiles.length > 1 ? 's' : ''} actif${includedFiles.length > 1 ? 's' : ''}`
                }
              </p>
            </div>
          </div>
          <button
            onClick={clearChat}
            className="text-sm px-3 py-2 text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg flex items-center gap-2 transition-colors"
            title="Effacer l'historique"
            aria-label="Clear chat history"
          >
            <RiDeleteBin6Line className="text-base" aria-hidden="true" />
            Effacer
          </button>
        </div>

        {/* Messages */}
        <GeneralChatMessages
          messages={messages}
          isLoading={isLoading}
          showingLetters={showingLetters}
          currentIndex={currentIndex}
          chatEndRef={chatEndRef}
          onSuggestionClick={handleSubmit}
        />

        {/* Input */}
        <GeneralChatInput
          question={question}
          setQuestion={setQuestion}
          isLoading={isLoading}
          includedFilesCount={includedFiles.length}
          onSubmit={() => handleSubmit()}
          onKeyPress={handleKeyPress}
        />
      </div>
    </div>
  );
}

export default GeneralChat;

