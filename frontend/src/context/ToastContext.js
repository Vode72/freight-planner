// src/context/ToastContext.js
import React, { createContext, useContext, useState, useCallback } from 'react';
 
const ToastContext = createContext(null);
 
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
 
  const addToast = useCallback(({ message, type = 'info', duration }) => {
    const id = Date.now() + Math.random();
    const timeout = duration ?? (type === 'error' ? 5000 : 3500);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, timeout);
  }, []);
 
  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);
 
  return (
    <ToastContext.Provider value={{ addToast, removeToast, toasts }}>
      {children}
    </ToastContext.Provider>
  );
}
 
export function useToastContext() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToastContext must be used within ToastProvider');
  return ctx;
}
 