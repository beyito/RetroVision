import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { MessageSquare, Send, X, Sparkles, AlertCircle, RefreshCw, Cpu, Store, Video } from 'lucide-react';

export default function ChatbotAssistant({ token, onRefreshData }) {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState([
    {
      role: 'model',
      text: '¡Hola! Soy tu asistente inteligente de RetroVision 🧠✨. Puedo ayudarte a registrar y listar tiendas (sucursales), nodos edge y cámaras de seguridad usando lenguaje natural.\n\nPor ejemplo: "Registra una tienda llamada Solar" o "Crea una cámara llamada Entrada en el Nodo 1 de la sucursal Centro". ¿En qué te puedo ayudar hoy?'
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [history, isOpen, isLoading]);

  const quickReplies = [
    { label: '🏬 Registrar Tienda', text: 'Quiero registrar una tienda llamada ' },
    { label: '🖥️ Registrar Nodo Edge', text: 'Quiero crear un nodo edge para la tienda ' },
    { label: '📷 Registrar Cámara', text: 'Quiero agregar una cámara llamada ' },
    { label: '📋 Listar Tiendas', text: 'Lista todas las tiendas' },
  ];

  const handleSend = async (e, textOverride = null) => {
    if (e) e.preventDefault();
    const textToSend = textOverride || message;
    if (!textToSend.trim() || isLoading) return;

    // Agregar mensaje del usuario a la historia
    const updatedHistory = [...history, { role: 'user', text: textToSend }];
    setHistory(updatedHistory);
    if (!textOverride) {
      setMessage('');
    }
    setIsLoading(true);
    setErrorMessage('');
    setSuccessMessage('');

    try {
      // Filtrar la bienvenida
      const apiHistory = updatedHistory.slice(1).map(h => ({
        role: h.role,
        text: h.text
      }));
      // Enviar a la API
      const previousHistory = apiHistory.slice(0, -1);

      const response = await axios.post(
        `${API_BASE_URL}/api/chatbot/chat/`,
        {
          message: textToSend,
          history: previousHistory
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );

      const data = response.data;
      if (data.status === 'success') {
        // Añadir la respuesta de la IA
        setHistory([...updatedHistory, { role: 'model', text: data.text }]);
        
        // Si se realizaron acciones, refrescar los datos en el frontend
        if (data.actions && data.actions.length > 0) {
          const actionDetails = data.actions.map(act => {
            if (act.type === 'store_created') return `Tienda "${act.name}"`;
            if (act.type === 'edgenode_created') return `Nodo "${act.display_name}"`;
            if (act.type === 'camera_created') return `Cámara "${act.display_name}"`;
            return 'recurso';
          }).join(', ');
          
          setSuccessMessage(`Se ha registrado: ${actionDetails} con éxito.`);
          if (onRefreshData) {
            onRefreshData();
          }
        }
      } else {
        setErrorMessage(data.error || 'Ocurrió un error inesperado.');
      }
    } catch (err) {
      console.error('Error in chatbot communication:', err);
      const apiErr = err.response?.data?.error || 'No se pudo conectar con el servidor de IA.';
      setErrorMessage(apiErr);
      setHistory([...updatedHistory, { role: 'model', text: `⚠️ Error: ${apiErr}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans">
      {/* Burbujita Flotante */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="group relative flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-500 via-blue-500 to-indigo-600 text-white shadow-xl shadow-cyan-500/20 hover:shadow-cyan-500/40 transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer border border-cyan-400/30 animate-bounce"
          title="Asistente IA de Configuración"
        >
          <Sparkles className="h-6 w-6 text-cyan-100 group-hover:rotate-12 transition-transform duration-300" />
          <span className="absolute -top-1 -right-1 flex h-4.5 w-4.5 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-black text-slate-950 uppercase border border-slate-950">
            AI
          </span>
        </button>
      )}

      {/* Ventana de Chat */}
      {isOpen && (
        <div className="flex h-[560px] w-[380px] flex-col rounded-3xl border border-white/10 bg-slate-950/90 backdrop-blur-xl shadow-2xl shadow-cyan-500/10 overflow-hidden transition-all duration-300 animate-in slide-in-from-bottom-5">
          {/* Cabecera */}
          <div className="flex items-center justify-between bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-indigo-500/10 px-4 py-3.5 border-b border-white/10">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-500 text-white shadow-md shadow-cyan-500/10">
                <Sparkles className="h-4.5 w-4.5" />
              </div>
              <div>
                <h3 className="text-sm font-black uppercase tracking-wider text-white">RetroVision AI</h3>
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                  <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Online</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-lg p-1 text-gray-400 hover:bg-white/5 hover:text-white transition cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Historial de Mensajes */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
            {history.map((msg, index) => {
              const isAI = msg.role === 'model';
              return (
                <div
                  key={index}
                  className={`flex ${isAI ? 'justify-start' : 'justify-end'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed whitespace-pre-line border ${
                      isAI
                        ? 'bg-slate-900/60 border-white/5 text-slate-100'
                        : 'bg-cyan-500/10 border-cyan-500/25 text-cyan-100 shadow-sm shadow-cyan-500/5'
                    }`}
                  >
                    {msg.text}
                  </div>
                </div>
              );
            })}

            {/* Indicador de Carga */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-2xl bg-slate-900/60 border border-white/5 px-4 py-3 text-xs text-slate-400 animate-pulse">
                  <RefreshCw className="h-3 w-3 animate-spin text-cyan-400" />
                  <span>Procesando solicitud...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Mensajes de Estado Flotantes/Inferiores */}
          {successMessage && (
            <div className="mx-4 mb-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-[11px] text-emerald-300 flex items-center gap-1.5 animate-in fade-in">
              <span className="text-emerald-400 font-bold">✔</span>
              <span>{successMessage}</span>
            </div>
          )}

          {errorMessage && (
            <div className="mx-4 mb-2 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-[11px] text-red-300 flex items-center gap-1.5 animate-in fade-in">
              <AlertCircle className="h-3.5 w-3.5 text-red-400" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Sugerencias Rápidas / Chips */}
          <div className="px-4 py-2 border-t border-white/5 bg-slate-950/40">
            <p className="text-[10px] uppercase font-bold text-slate-500 mb-1.5">Sugerencias rápidas</p>
            <div className="flex flex-wrap gap-1.5">
              {quickReplies.map((reply, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setMessage(reply.text);
                  }}
                  className="rounded-lg bg-white/5 border border-white/5 hover:border-cyan-500/30 hover:bg-cyan-500/5 px-2.5 py-1 text-[10px] text-slate-300 hover:text-cyan-300 transition cursor-pointer"
                >
                  {reply.label}
                </button>
              ))}
            </div>
          </div>

          {/* Input de Envío */}
          <form
            onSubmit={handleSend}
            className="flex items-center gap-2 border-t border-white/10 bg-slate-950 p-3"
          >
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Escribe un comando en lenguaje natural..."
              disabled={isLoading}
              className="flex-1 rounded-xl bg-white/5 border border-white/5 px-3 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 transition disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={!message.trim() || isLoading}
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 hover:bg-cyan-400 disabled:opacity-50 transition cursor-pointer"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
