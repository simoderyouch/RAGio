import React from 'react';
import NavBar from './shared/navBar';
import GeneralChat from './GeneralChat/GeneralChat';

function GeneralChatPage() {
  return (
    <div className="flex flex-col bg-gradient-to-br from-slate-50 to-gray-100 min-h-screen">
      <NavBar />
      
      <div className="flex-1 p-4 md:p-6">
        <div className="max-w-9xl mx-auto h-[calc(100vh-140px)]">
          <GeneralChat />
        </div>
      </div>
    </div>
  );
}

export default GeneralChatPage;

