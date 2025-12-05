import { useMemo, useCallback } from 'react';

/**
 * Custom hook for file-related helper functions
 * @param {Object} filesData - Files data object grouped by type
 * @returns {Object} Helper functions and computed values
 */
export const useFileHelpers = (filesData) => {
  // Get all files flattened
  const getAllFiles = useCallback(() => {
    if (!filesData) return [];
    return Object.values(filesData).flat();
  }, [filesData]);

  const allFiles = useMemo(() => getAllFiles(), [getAllFiles]);
  
  const processedFiles = useMemo(
    () => allFiles.filter(f => f.processed),
    [allFiles]
  );
  
  const unprocessedFiles = useMemo(
    () => allFiles.filter(f => !f.processed),
    [allFiles]
  );

  // Get files by type
  const getFilesByType = useCallback((type) => {
    if (!filesData || !filesData[type]) return [];
    return filesData[type];
  }, [filesData]);

  // Get file by ID
  const getFileById = useCallback((fileId) => {
    return allFiles.find(f => f.id === fileId);
  }, [allFiles]);

  // Format file size
  const formatFileSize = useCallback((bytes) => {
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    return `${(bytes / 1024).toFixed(1)} KB`;
  }, []);

  // Format upload date
  const formatUploadDate = useCallback((dateString) => {
    return new Date(dateString).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }, []);

  return {
    allFiles,
    processedFiles,
    unprocessedFiles,
    getAllFiles,
    getFilesByType,
    getFileById,
    formatFileSize,
    formatUploadDate,
  };
};

