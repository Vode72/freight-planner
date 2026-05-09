// src/components/ToastContainer.js
import React, { useState, useEffect } from 'react';
import { useToastContext } from '../context/ToastContext';

// ─── Värit per tyyppi ────────────────────────────────────────────────────────
const STYLES = {
  success: {
    bg:     '#0d2818',
    border: '#16a34a',
    accent: '#22c55e',
    text:   '#dcfce7',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
        <path d="M4 7.5L6.5 10L11 5" stroke="currentColor" strokeWidth="1.5"
              strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  error: {
    bg:     '#2a0a0a',
    border: '#dc2626',
    accent: '#ef4444',
    text:   '#fee2e2',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
        <path d="M5 5L10 10M10 5L5 10" stroke="currentColor" strokeWidth="1.5"
              strokeLinecap="round"/>
      </svg>
    ),
  },
  warning: {
    bg:     '#271400',
    border: '#d97706',
    accent: '#f97316',
    text:   '#ffedd5',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <path d="M7.5 1.5L13.5 12.5H1.5L7.5 1.5Z" stroke="currentColor"
              strokeWidth="1.4" strokeLinejoin="round"/>
        <path d="M7.5 5.5V8.5" stroke="currentColor" strokeWidth="1.5"
              strokeLinecap="round"/>
        <circle cx="7.5" cy="10.5" r="0.7" fill="currentColor"/>
      </svg>
    ),
  },
  info: {
    bg:     '#070f1f',
    border: '#2563eb',
    accent: '#3b82f6',
    text:   '#dbeafe',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
        <path d="M7.5 6.5V10.5" stroke="currentColor" strokeWidth="1.5"
              strokeLinecap="round"/>
        <circle cx="7.5" cy="4.5" r="0.7" fill="currentColor"/>
      </svg>
    ),
  },
};

// ─── Yksittäinen toast ───────────────────────────────────────────────────────
function Toast({ id, message, type, onRemove }) {
  const [phase, setPhase] = useState('enter'); // enter | idle | leave
  const s = STYLES[type] || STYLES.info;

  // Sisään-animaatio
  useEffect(() => {
    const t = setTimeout(() => setPhase('idle'), 20);
    return () => clearTimeout(t);
  }, []);

  const handleClose = () => {
    setPhase('leave');
    setTimeout(() => onRemove(id), 300);
  };

  const transform = phase === 'idle'
    ? 'translateX(0) scale(1)'
    : phase === 'leave'
    ? 'translateX(110%) scale(0.95)'
    : 'translateX(24px) scale(0.97)';

  return (
    <div
      style={{
        display:        'flex',
        alignItems:     'flex-start',
        gap:            '10px',
        padding:        '11px 13px',
        background:     s.bg,
        border:         `1px solid ${s.border}33`,
        borderLeft:     `3px solid ${s.accent}`,
        borderRadius:   '7px',
        boxShadow:      `0 8px 24px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.04)`,
        color:          s.text,
        fontSize:       '13px',
        fontWeight:     '500',
        lineHeight:     '1.45',
        width:          '340px',
        opacity:        phase === 'idle' ? 1 : 0,
        transform,
        transition:     'opacity 0.3s cubic-bezier(0.16,1,0.3,1), transform 0.3s cubic-bezier(0.16,1,0.3,1)',
        willChange:     'transform, opacity',
        pointerEvents:  'all',
        userSelect:     'none',
      }}
    >
      {/* Ikoni */}
      <span style={{ color: s.accent, flexShrink: 0, marginTop: '1px', lineHeight: 0 }}>
        {s.icon}
      </span>

      {/* Viesti */}
      <span style={{ flex: 1 }}>{message}</span>

      {/* Sulje */}
      <button
        onClick={handleClose}
        style={{
          background:  'none',
          border:      'none',
          color:       s.text,
          opacity:     0.45,
          cursor:      'pointer',
          padding:     '0',
          fontSize:    '17px',
          lineHeight:  1,
          flexShrink:  0,
          marginTop:   '-2px',
          transition:  'opacity 0.15s',
        }}
        onMouseEnter={e => (e.currentTarget.style.opacity = 1)}
        onMouseLeave={e => (e.currentTarget.style.opacity = 0.45)}
        aria-label="Sulje ilmoitus"
      >
        ×
      </button>
    </div>
  );
}

// ─── Kontti (fixed oikeaan alakulmaan) ──────────────────────────────────────
export default function ToastContainer() {
  const { toasts, removeToast } = useToastContext();
  if (!toasts.length) return null;

  return (
    <div
      style={{
        position:      'fixed',
        bottom:        '24px',
        right:         '24px',
        display:       'flex',
        flexDirection: 'column',
        gap:           '8px',
        zIndex:        9999,
        pointerEvents: 'none',
      }}
    >
      {toasts.map(t => (
        <Toast key={t.id} {...t} onRemove={removeToast} />
      ))}
    </div>
  );
}