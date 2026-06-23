export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL !== undefined 
  ? import.meta.env.VITE_API_BASE_URL 
  : (window.location.origin === 'http://localhost:5173' ? 'http://localhost:8000' : window.location.origin);

export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL !== undefined
  ? import.meta.env.VITE_WS_BASE_URL
  : (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host;

