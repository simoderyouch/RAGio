import React from 'react';
import { LuChevronLeft, LuChevronRight } from "react-icons/lu";
import { GoStack, GoCheck } from "react-icons/go";
import { MdOutlineSelectAll, MdClear, MdOutlinePlayCircle } from "react-icons/md";
import { FaFileAlt } from "react-icons/fa";

/**
 * Sidebar component for GeneralChat showing document list
 */
export const GeneralChatSidebar = React.memo(({
  sidebarCollapsed,
  setSidebarCollapsed,
  includedFiles,
  processedFiles,
  unprocessedFiles,
  excludedFiles,
  fileStatuses,
  onFileToggle,
  onIncludeAll,
  onExcludeAll,
  onProcessFile,
}) => {
  return (
    <div className={`${sidebarCollapsed ? 'w-16' : 'w-80'} border-r border-gray-100 flex flex-col bg-gray-50/50 transition-all duration-300`}>
      {!sidebarCollapsed ? (
        <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
              <GoStack className="text-primary text-lg" aria-hidden="true" />
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-800">Documents</span>
              <p className="text-xs text-gray-500">
                {includedFiles.length} / {processedFiles.length} actifs
              </p>
            </div>
          </div>
          <button
            onClick={() => setSidebarCollapsed(true)}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            title="Réduire"
            aria-label="Collapse sidebar"
          >
            <LuChevronLeft className="text-lg" aria-hidden="true" />
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 p-3 border-b border-gray-100 bg-white">
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            title="Développer"
            aria-label="Expand sidebar"
          >
            <LuChevronRight className="text-lg" aria-hidden="true" />
          </button>
          <div className="relative" title={`${includedFiles.length} documents actifs`} aria-label={`${includedFiles.length} documents actifs`}>
            <GoStack className="text-primary text-xl" aria-hidden="true" />
            <span className="absolute -top-1 -right-2 bg-primary text-white text-[10px] leading-none px-1.5 py-0.5 rounded-full min-w-[16px] text-center">
              {includedFiles.length}
            </span>
          </div>
        </div>
      )}

      {!sidebarCollapsed && (
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Quick actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={onIncludeAll}
              className="flex-1 text-xs text-primary px-3 py-2 border border-primary/20 bg-primary/5 rounded-lg flex items-center justify-center gap-1.5 hover:bg-primary/10 transition-colors"
              title="Inclure tous les documents"
              aria-label="Include all documents"
            >
              <MdOutlineSelectAll className="text-sm" aria-hidden="true" />
              Tout inclure
            </button>
            <button
              onClick={onExcludeAll}
              className="flex-1 text-xs text-gray-600 px-3 py-2 border border-gray-200 rounded-lg flex items-center justify-center gap-1.5 hover:bg-gray-50 transition-colors"
              title="Exclure tous les documents"
              aria-label="Exclude all documents"
            >
              <MdClear className="text-sm" aria-hidden="true" />
              Tout exclure
            </button>
          </div>

          {/* Info banner */}
          <div className="p-3 bg-gradient-to-r from-primary/5 to-primary/10 rounded-lg border border-primary/10">
            <p className="text-xs text-gray-600 leading-relaxed">
              <span className="font-medium text-primary">Chat Général</span> — Tous vos documents sont inclus par défaut. 
              Décochez ceux que vous souhaitez exclure.
            </p>
          </div>

          {/* Unprocessed files warning */}
          {unprocessedFiles.length > 0 && (
            <div className="space-y-2">
              <p className="text-[11px] uppercase text-amber-600 font-medium flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-400" aria-hidden="true"></span>
                Non traités ({unprocessedFiles.length})
              </p>
              {unprocessedFiles.map((file) => {
                const displayStatus = fileStatuses[file.id];
                const status = displayStatus?.status || (file.processed ? 'completed' : 'pending');
                const isProcessing = status === 'processing';
                const isFailed = status === 'failed';
                
                return (
                  <div
                    key={file.id}
                    className="flex items-center gap-2 p-3 rounded-lg border border-amber-200 bg-amber-50/50"
                  >
                    <FaFileAlt className="text-amber-500 flex-shrink-0" aria-hidden="true" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{file.file_name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-amber-600 uppercase">{file.extention}</span>
                        {isProcessing && (
                          <span className="text-[10px] text-amber-700 flex items-center gap-1" aria-live="polite">
                            <svg className="animate-spin h-2.5 w-2.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Processing...
                          </span>
                        )}
                        {isFailed && (
                          <span className="text-[10px] text-red-600" title={displayStatus?.error}>
                            Failed
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => onProcessFile(file.id)}
                      disabled={isProcessing}
                      className={`text-xs px-2.5 py-1.5 rounded-lg flex items-center gap-1 transition-colors disabled:opacity-50 ${
                        isFailed
                          ? 'bg-red-100 text-red-700 hover:bg-red-200'
                          : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                      }`}
                      aria-label={isProcessing ? 'Processing document' : isFailed ? 'Retry processing document' : 'Process document'}
                    >
                      <MdOutlinePlayCircle className="text-sm" aria-hidden="true" />
                      {isProcessing ? '...' : isFailed ? 'Retry' : 'Traiter'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Processed files list */}
          {processedFiles.length > 0 ? (
            <div className="space-y-2">
              <p className="text-[11px] uppercase text-gray-400 font-medium">
                Documents disponibles
              </p>
              {processedFiles.map((file) => {
                const isIncluded = !excludedFiles.includes(file.id);
                return (
                  <div
                    key={file.id}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                      isIncluded
                        ? 'border-primary/30 bg-primary/5 hover:bg-primary/10'
                        : 'border-gray-200 bg-white hover:bg-gray-50 opacity-60'
                    }`}
                    onClick={() => onFileToggle(file.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onFileToggle(file.id);
                      }
                    }}
                    aria-label={`${isIncluded ? 'Included' : 'Excluded'} document: ${file.file_name}`}
                  >
                    <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 transition-colors ${
                      isIncluded 
                        ? 'bg-primary text-white' 
                        : 'border-2 border-gray-300'
                    }`} aria-hidden="true">
                      {isIncluded && <GoCheck className="text-sm" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium truncate ${isIncluded ? 'text-gray-800' : 'text-gray-500'}`}>
                        {file.file_name}
                      </p>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] uppercase ${isIncluded ? 'text-primary' : 'text-gray-400'}`}>
                          {file.extention}
                        </span>
                        {isIncluded && (
                          <span className="text-[10px] text-green-600 flex items-center gap-0.5">
                            <GoCheck className="text-[8px]" aria-hidden="true" /> Inclus
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <FaFileAlt className="mx-auto text-3xl mb-3 text-gray-300" aria-hidden="true" />
              <p className="text-gray-500 text-sm">Aucun document traité</p>
              <p className="text-xs text-gray-400 mt-1">Téléchargez et traitez des documents d'abord</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

GeneralChatSidebar.displayName = "GeneralChatSidebar";

