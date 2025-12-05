import React, { createContext, useContext, useState, useCallback } from 'react';
import { HiCheckCircle, HiXCircle, HiInformationCircle, HiExclamation } from 'react-icons/hi';

const ToastContext = createContext(null);

// Toast types configuration
const TOAST_TYPES = {
  success: {
    icon: HiCheckCircle,
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    textColor: 'text-emerald-800',
    iconColor: 'text-emerald-500',
    progressColor: 'bg-emerald-500'
  },
  error: {
    icon: HiXCircle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-800',
    iconColor: 'text-red-500',
    progressColor: 'bg-red-500'
  },
  warning: {
    icon: HiExclamation,
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-800',
    iconColor: 'text-amber-500',
    progressColor: 'bg-amber-500'
  },
  info: {
    icon: HiInformationCircle,
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
    iconColor: 'text-blue-500',
    progressColor: 'bg-blue-500'
  }
};

// Individual Toast Component
const Toast = ({ id, type, message, title, onRemove, duration }) => {
  const config = TOAST_TYPES[type] || TOAST_TYPES.info;
  const Icon = config.icon;

  return (
    <div
      className={`
        relative overflow-hidden
        flex items-start gap-3 p-4 rounded-lg border shadow-lg
        ${config.bgColor} ${config.borderColor}
        animate-slide-in
        min-w-[320px] max-w-[420px]
      `}
      role="alert"
    >
      {/* Icon */}
      <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${config.iconColor}`} />
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        {title && (
          <p className={`font-semibold text-sm ${config.textColor}`}>
            {title}
          </p>
        )}
        <p className={`text-sm ${title ? 'mt-0.5' : ''} ${config.textColor} opacity-90`}>
          {message}
        </p>
      </div>

      {/* Close Button */}
      <button
        onClick={() => onRemove(id)}
        className={`
          flex-shrink-0 p-1 rounded-md transition-colors
          ${config.textColor} hover:bg-black/5
        `}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Progress Bar */}
      <div
        className={`absolute bottom-0 left-0 h-1 ${config.progressColor} animate-progress`}
        style={{ animationDuration: `${duration}ms` }}
      />
    </div>
  );
};

// Toast Container Component
const ToastContainer = ({ toasts, removeToast }) => {
  return (
    <div className="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-3">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          {...toast}
          onRemove={removeToast}
        />
      ))}
    </div>
  );
};

// Toast Provider Component
export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(({ type = 'info', message, title, duration = 3000 }) => {
    const id = Date.now() + Math.random();
    
    setToasts((prev) => [...prev, { id, type, message, title, duration }]);

    // Auto remove after duration
    setTimeout(() => {
      removeToast(id);
    }, duration);

    return id;
  }, [removeToast]);

  // Convenience methods
  const toast = {
    success: (message, title) => addToast({ type: 'success', message, title }),
    error: (message, title) => addToast({ type: 'error', message, title }),
    warning: (message, title) => addToast({ type: 'warning', message, title }),
    info: (message, title) => addToast({ type: 'info', message, title }),
    custom: addToast
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
      
      {/* Inject animations via style tag */}
      <style>{`
        @keyframes slide-in-bottom {
          from {
            transform: translateY(100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        
        @keyframes progress {
          from {
            width: 100%;
          }
          to {
            width: 0%;
          }
        }
        
        .animate-slide-in {
          animation: slide-in-bottom 0.3s ease-out forwards;
        }
        
        .animate-progress {
          animation: progress linear forwards;
        }
      `}</style>
    </ToastContext.Provider>
  );
};

// Custom hook to use toast
export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

export default ToastProvider;

