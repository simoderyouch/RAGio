import React from 'react';
import { IoChevronBack, IoChevronForward } from "react-icons/io5";

/**
 * Custom resize handle with toggle button for ChatSpace panels
 */
export const CustomPanelResizeHandle = React.memo(({ 
  isViewerCollapsed, 
  onToggle 
}) => {
  return (
    <div className="group relative flex items-center justify-center w-2 mx-1 transition-colors hover:bg-blue-100 rounded data-[resize-handle-active]:bg-blue-200">
      <div className="w-1 h-12 rounded-full bg-gray-300 group-hover:bg-blue-400 group-hover:h-16 transition-all group-data-[resize-handle-active]:bg-blue-500 group-data-[resize-handle-active]:h-20" />
      
      <button
        onClick={onToggle}
        className="absolute top-1/2 -translate-y-1/2 left-1/2 -translate-x-1/2 z-10 flex items-center justify-center w-5 h-10 rounded-full bg-white border border-gray-300 hover:bg-blue-50 hover:border-blue-300 shadow-md transition-all"
        title={isViewerCollapsed ? 'Show document' : 'Hide document'}
        aria-label={isViewerCollapsed ? 'Show document' : 'Hide document'}
      >
        {isViewerCollapsed ? (
          <IoChevronForward className="text-gray-600 text-xs" aria-hidden="true" />
        ) : (
          <IoChevronBack className="text-gray-600 text-xs" aria-hidden="true" />
        )}
      </button>
    </div>
  );
});

CustomPanelResizeHandle.displayName = "CustomPanelResizeHandle";

