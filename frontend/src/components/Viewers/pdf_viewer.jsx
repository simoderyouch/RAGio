import React, { useState, useCallback, useEffect, useRef } from "react";
import { Viewer, Worker } from '@react-pdf-viewer/core';
import { pageNavigationPlugin } from '@react-pdf-viewer/page-navigation';
import { zoomPlugin } from '@react-pdf-viewer/zoom';

// Import styles
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/page-navigation/lib/styles/index.css';
import '@react-pdf-viewer/zoom/lib/styles/index.css';

// Icons
import { IoIosArrowDown, IoIosArrowUp } from "react-icons/io";
import { HiOutlinePlusSm, HiMinusSm, HiOutlineDocumentText } from "react-icons/hi";
import { BsFullscreen, BsFullscreenExit } from "react-icons/bs";
import { FiExternalLink } from "react-icons/fi";
import Loading from "../ui/Loading";

// PDF.js worker version
const PDFJS_VERSION = '3.11.174';


function PdfViewer({ url, className = "" }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentZoom, setCurrentZoom] = useState(100);

  const containerRef = useRef(null);

  const pageNavigationPluginInstance = pageNavigationPlugin();
  const { jumpToPage } = pageNavigationPluginInstance;

  const zoomPluginInstance = zoomPlugin();
  const { zoomTo } = zoomPluginInstance;

  const handlePageChange = useCallback((e) => {
    setCurrentPage(e.currentPage + 1);
  }, []);

  const handleDocumentLoad = useCallback((e) => {
    setTotalPages(e.doc.numPages);
    setIsLoading(false);
    setError(null);
  }, []);

  const handleLoadError = useCallback((e) => {
    setError('Failed to load PDF');
    setIsLoading(false);
  }, []);

  const goToPrevPage = useCallback(() => {
    if (currentPage > 1) {
      jumpToPage(currentPage - 2);
    }
  }, [currentPage, jumpToPage]);

  const goToNextPage = useCallback(() => {
    if (currentPage < totalPages) {
      jumpToPage(currentPage);
    }
  }, [currentPage, totalPages, jumpToPage]);

  const handlePageInput = useCallback((e) => {
    const page = parseInt(e.target.value);
    if (page >= 1 && page <= totalPages) {
      jumpToPage(page - 1);
    }
  }, [totalPages, jumpToPage]);


  const handleZoomIn = useCallback(() => {
    const newZoom = Math.min(currentZoom + 25, 300);
    zoomTo(newZoom / 100);
    setCurrentZoom(newZoom);
  }, [currentZoom, zoomTo]);

  const handleZoomOut = useCallback(() => {
    const newZoom = Math.max(currentZoom - 25, 50);
    zoomTo(newZoom / 100);
    setCurrentZoom(newZoom);
  }, [currentZoom, zoomTo]);


  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;

    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Open in new tab
  const openInNewTab = useCallback(() => {
    window.open(url, '_blank');
  }, [url]);

  // Error state
  if (error) {
    return (
      <div className={`flex items-center justify-center h-full bg-gray-50 ${className}`}>
        <div className="text-center p-8">
          <HiOutlineDocumentText className="mx-auto text-6xl text-gray-300 mb-4" />
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`flex flex-col h-full bg-gray-100 ${className}`}
    >
      {/* Custom Light Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-gray-200 shrink-0 shadow-sm">
        {/* Left spacer */}
        <div className="flex items-center gap-2" >

          <button
            onClick={toggleFullscreen}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all"
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? (
              <BsFullscreenExit className="text-lg" />
            ) : (
              <BsFullscreen className="text-lg" />
            )}
          </button>

          <button
            onClick={openInNewTab}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all"
            title="Open in new tab"
          >
            <FiExternalLink className="text-lg" />
          </button>

        </div>


        {/* Center - Page navigation */}
        <div className="flex items-center gap-3">
          <button
            onClick={goToPrevPage}
            disabled={currentPage <= 1}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-gray-500"
            title="Previous page"
          >
            <IoIosArrowUp className="text-xl" />
          </button>

          <div className="flex items-center gap-2">
            <input
              type="number"
              value={currentPage}
              min={1}
              max={totalPages}
              onChange={handlePageInput}
              className="w-14 py-1.5 px-2 text-center bg-gray-50 border border-gray-300 rounded-lg text-gray-900 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
            <span className="text-gray-400 text-sm">of {totalPages || '—'}</span>
          </div>

          <button
            onClick={goToNextPage}
            disabled={currentPage >= totalPages}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-gray-500"
            title="Next page"
          >
            <IoIosArrowDown className="text-xl" />
          </button>
        </div>

        {/* Right - Zoom and actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            disabled={currentZoom <= 50}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            title="Zoom out"
          >
            <HiMinusSm className="text-xl" />
          </button>

          <span className="text-sm text-gray-700 w-14 text-center font-medium">
            {currentZoom}%
          </span>

          <button
            onClick={handleZoomIn}
            disabled={currentZoom >= 300}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            title="Zoom in"
          >
            <HiOutlinePlusSm className="text-xl" />
          </button>


        </div>
      </div>

      {/* PDF Viewer Area */}
      <div className="flex-1 overflow-hidden relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100 z-10">
            <Loading />
          </div>
        )}

        {url && (
          <Worker workerUrl={`https://unpkg.com/pdfjs-dist@${PDFJS_VERSION}/build/pdf.worker.min.js`}>
            <div className="h-full pdf-viewer-container">
              <Viewer
                fileUrl={url}
                defaultScale={1}
                onPageChange={handlePageChange}
                onDocumentLoad={handleDocumentLoad}
                renderError={handleLoadError}
                plugins={[
                  pageNavigationPluginInstance,
                  zoomPluginInstance,
                ]}
              />
            </div>
          </Worker>
        )}
      </div>

      {/* Light mode styles */}
      <style>{`
        /* PDF Viewer Light Theme */
        .pdf-viewer-container {
          background-color: #f3f4f6 !important;
        }
        
        .rpv-core__viewer {
          background-color: #f3f4f6 !important;
        }
        
        .rpv-core__inner-pages {
          background-color: #f3f4f6 !important;
        }
        
        .rpv-core__inner-page {
          background-color: #f3f4f6 !important;
        }
        
        .rpv-core__page-layer {
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
          margin: 16px auto !important;
          border-radius: 4px;
          overflow: hidden;
        }
        
        /* Scrollbar - Main viewer */
        .rpv-core__inner-pages::-webkit-scrollbar {
          width: 10px;
          height: 10px;
        }
        
        .rpv-core__inner-pages::-webkit-scrollbar-track {
          background: #f3f4f6;
        }
        
        .rpv-core__inner-pages::-webkit-scrollbar-thumb {
          background: #d1d5db;
          border-radius: 5px;
          border: 2px solid #f3f4f6;
        }
        
        .rpv-core__inner-pages::-webkit-scrollbar-thumb:hover {
          background: #9ca3af;
        }

        /* Hide default toolbar if any */
        .rpv-toolbar {
          display: none !important;
        }

        /* Text layer for selection */
        .rpv-core__text-layer {
          opacity: 0.2;
        }
        
        .rpv-core__text-layer:hover {
          opacity: 0.4;
        }
      `}</style>
    </div>
  );
}

export default PdfViewer;
