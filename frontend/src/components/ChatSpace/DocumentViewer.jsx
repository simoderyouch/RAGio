import React, { Suspense, useMemo } from 'react';
import PdfViewer from '../Viewers/pdf_viewer';
import CSVViewer from '../Viewers/csv_viewer';
import TxtViewer from '../Viewers/txt_viewer';
import MdViewer from '../Viewers/md_viewer';
import Loading from '../ui/Loading';

/**
 * Document Viewer component that renders the appropriate viewer based on file type
 */
export const DocumentViewer = React.memo(({ 
  fileData, 
  fileViewUrl, 
  needsProcessing, 
  isProcessing, 
  onProcess 
}) => {
  const fileType = useMemo(() => fileData?.file_type, [fileData?.file_type]);
  
  const renderViewer = () => {
    switch (fileType) {
      case 'PDF':
        return (
          <Suspense fallback={
            <div className="flex items-center justify-center h-full">
              <Loading padding={3} />
            </div>
          }>
            <PdfViewer url={fileViewUrl} />
          </Suspense>
        );
      case 'CSV':
        return <CSVViewer url={fileViewUrl} />;
      case 'TXT':
        return <TxtViewer url={fileViewUrl} />;
      case 'MD':
        return <MdViewer url={fileViewUrl} />;
      default:
        return null;
    }
  };

  if (!fileData) return null;

  return (
    <div className="relative h-full w-full">
      {renderViewer()}
      
      {/* Processing Overlay */}
      {needsProcessing && (
        <div 
          className="absolute inset-0 flex justify-center items-center z-50 bg-black/65"
          role="dialog"
          aria-label="Document processing overlay"
        >
          {isProcessing ? (
            <Loading color="#ffffff" />
          ) : (
            <button
              onClick={onProcess}
              className="border-dashed border-2 border-white py-3 px-8 rounded-lg text-white hover:bg-white/10 transition-colors"
              aria-label="Process document"
            >
              Analyse Document
            </button>
          )}
        </div>
      )}
    </div>
  );
});

DocumentViewer.displayName = "DocumentViewer";

