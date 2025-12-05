import { useParams } from 'react-router-dom';
import { useState, useRef, useCallback, Suspense, useMemo } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import NavBar from './shared/navBar';
import useFetch from '../hooks/useFetch';
import useAxiosPrivate from '../hooks/useAxiosPrivate';
import Chats from './chats';
import Loading from './ui/Loading';
import { HiOutlineDocumentText } from "react-icons/hi";
import { BASE_URL } from '../utils/axios';
import { DocumentViewer } from './ChatSpace/DocumentViewer';
import { CustomPanelResizeHandle } from './ChatSpace/PanelResizeHandle';

function ChatSpace() {
  const { id } = useParams();
  const { data: fileData, isLoading: fileIsLoading, fetchData } = useFetch(`/api/document/file/${id}`);
  const axiosInstance = useAxiosPrivate();
  
  const [isViewerCollapsed, setIsViewerCollapsed] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const viewerPanelRef = useRef(null);

  const toggleViewer = useCallback(() => {
    const panel = viewerPanelRef.current;
    if (panel) {
      if (panel.isCollapsed()) {
        panel.expand();
      } else {
        panel.collapse();
      }
    }
  }, []);

  const handleCollapse = useCallback(() => setIsViewerCollapsed(true), []);
  const handleExpand = useCallback(() => setIsViewerCollapsed(false), []);

  // Handle document processing
  const handleProcess = useCallback(async () => {
    if (!fileData?.id) return;
    
    setIsProcessing(true);
    try {
      await axiosInstance.get(`/api/document/process/${fileData.id}`);
      fetchData();
    } catch (error) {
      // Processing error
    } finally {
      setIsProcessing(false);
    }
  }, [fileData?.id, axiosInstance, fetchData]);

  // Memoize computed values
  const needsProcessing = useMemo(() => fileData && !fileData.processed, [fileData]);
  const fileViewUrl = useMemo(() => 
    `${BASE_URL}/api/document/file/${id}/view`,
    [id]
  );

  return (
    <div className="flex flex-col relative bg-gray-100 h-[100vh]">
      <NavBar />

      <div className="flex flex-col flex-1 md:flex-row relative w-full p-3 overflow-hidden">
        {fileIsLoading ? (
          <div className="flex items-center justify-center w-full h-[87vh]">
            <Loading padding={3} />
          </div>
        ) : (
          <>
            {/* Desktop Layout with Resizable Panels */}
            <div className="hidden md:flex w-full h-full">
              <PanelGroup 
                direction="horizontal" 
                autoSaveId="chatspace-panels"
              >
                {/* Viewer Panel */}
                <Panel
                  ref={viewerPanelRef}
                  defaultSize={50}
                  minSize={20}
                  maxSize={80}
                  collapsible={true}
                  collapsedSize={0}
                  onCollapse={handleCollapse}
                  onExpand={handleExpand}
                  className="h-full"
                >
                  <div className="h-full w-full overflow-hidden">
                    <DocumentViewer
                      fileData={fileData}
                      fileViewUrl={fileViewUrl}
                      needsProcessing={needsProcessing}
                      isProcessing={isProcessing}
                      onProcess={handleProcess}
                    />
                  </div>
                </Panel>

                {/* Resize Handle */}
                <PanelResizeHandle>
                  <CustomPanelResizeHandle
                    isViewerCollapsed={isViewerCollapsed}
                    onToggle={toggleViewer}
                  />
                </PanelResizeHandle>

                {/* Chats Panel */}
                <Panel defaultSize={50} minSize={25} className="h-full">
                  <div className="h-full w-full overflow-hidden">
                    <Chats fileData={fileData} />
                  </div>
                </Panel>
              </PanelGroup>
            </div>

            {/* Mobile Layout */}
            <div className="md:hidden flex flex-col w-full h-full gap-2">
              <button
                onClick={() => setIsViewerCollapsed(prev => !prev)}
                className="flex items-center justify-center gap-2 py-2 px-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-blue-50 transition-colors"
              >
                <HiOutlineDocumentText className="text-gray-600" />
                <span className="text-sm text-gray-600">
                  {isViewerCollapsed ? 'Show Document' : 'Hide Document'}
                </span>
              </button>

              {!isViewerCollapsed && (
                <div className="w-full h-[40vh]">
                  <DocumentViewer
                    fileData={fileData}
                    fileViewUrl={fileViewUrl}
                    needsProcessing={needsProcessing}
                    isProcessing={isProcessing}
                    onProcess={handleProcess}
                  />
                </div>
              )}

              <div className="flex-1 overflow-hidden">
                <Suspense fallback={<div className="flex items-center justify-center h-full"><Loading padding={3} /></div>}>
                  <Chats fileData={fileData} />
                </Suspense>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default ChatSpace;
