import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './components/landing';
import './index.css';
import Loading from './components/ui/Loading';
import RegisterComponents from './components/register';
import Login from './components/login';
import useAuthStore from './stores/authStore';
import ErrorBoundary from './components/ErrorBoundary';

// Lazy load heavy components
const ChatSpace = lazy(() => import('./components/chatSpace'));
const ChatDashboard = lazy(() => import('./components/chatDashboard'));
const GeneralChatPage = lazy(() => import('./components/GeneralChatPage'));

function PrivateRoute({ element, ...rest }) {
  const token = useAuthStore((state) => state.token);

  return token ? (
    element
  ) : (
    <Navigate to="/user/login" replace />
  );
}

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <ErrorBoundary>
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loading padding={8} /></div>}>
            <Routes>
              <Route exact path="/" element={<ErrorBoundary><Landing /></ErrorBoundary>} />
              <Route exact path="/user/register" element={<ErrorBoundary><RegisterComponents /></ErrorBoundary>} />
              <Route exact path="/user/login" element={<ErrorBoundary><Login /></ErrorBoundary>} />
              
              <Route path="/chatroom" element={<ErrorBoundary><PrivateRoute element={<ChatDashboard />} /></ErrorBoundary>} />
              <Route path="/chatroom/:id" element={<ErrorBoundary><PrivateRoute element={<ChatSpace />} /></ErrorBoundary>} />
              <Route path="/general-chat" element={<ErrorBoundary><PrivateRoute element={<GeneralChatPage />} /></ErrorBoundary>} />
              
              {/* Backward compatibility: redirect old multi-chat route to general-chat */}
              <Route path="/multi-chat" element={<Navigate to="/general-chat" replace />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
