import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  ShieldAlert, Video, Activity, RefreshCw, Search, Filter,
  Clock, Camera, AlertTriangle, Eye, ShieldCheck, Volume2, VolumeX,
  Play, Calendar, Info, BarChart2
} from 'lucide-react';
import AnalyticsPanel from './AnalyticsPanel';

export default function Dashboard() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsStatus, setWsStatus] = useState('DISCONNECTED');
  const [lastChecked, setLastChecked] = useState(new Date());
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState('ALL'); // ALL, CRITICAL, WARNING, LOW
  const [selectedCameraFilter, setSelectedCameraFilter] = useState('ALL');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [flashScreen, setFlashScreen] = useState(false);
  const [token, setToken] = useState(null);
  const [activeTab, setActiveTab] = useState('security'); // 'security' | 'analytics'

  const prevAlertsCountRef = useRef(0);
  const audioContextRef = useRef(null);

  // --- ARREGLO CRÍTICO 1: Referencia para el estado del sonido ---
  const soundEnabledRef = useRef(soundEnabled);
  useEffect(() => {
    soundEnabledRef.current = soundEnabled;
  }, [soundEnabled]);

  // Auto-login and initial history fetch
  const loginAndFetch = async () => {
    setLoading(true);
    try {
      // 1. Authenticate to get JWT token
      const authRes = await axios.post('http://localhost:8000/api/token/', {
        username: 'admin',
        password: 'admin123'
      });
      const accessToken = authRes.data.access;
      setToken(accessToken);

      // 2. Fetch history
      const response = await axios.get('http://localhost:8000/api/alerts/', {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      setAlerts(response.data);
      setError(null);
    } catch (err) {
      console.error("Auth / Fetch failed:", err);
      setError("Fallo al conectar con el API central (Verifica credenciales o servidor).");
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  };

  // Sound generator using Web Audio API
  const playAlertSound = () => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(660, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
      osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.3);

      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.4);
    } catch (e) {
      console.warn("Audio Context could not start:", e);
    }
  };
  // WebSockets Native Connection
  const wsRef = useRef(null); // <- Referencia estática e inmortal
  const isConnectingRef = useRef(false); // <- Bloqueador de choques

  useEffect(() => {
    let reconnectTimeout = null;

    const connectWS = () => {
      // Si ya hay una conexión viva, o estamos en proceso de conectar, abortar
      if (wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) {
        return;
      }

      isConnectingRef.current = true;
      setWsStatus('CONNECTING');

      const ws = new WebSocket('ws://127.0.0.1:8000/ws/alerts/');

      ws.onopen = () => {
        console.log("WebSocket conectado exitosamente!");
        setWsStatus('CONNECTED');
        isConnectingRef.current = false;
        wsRef.current = ws; // Guardamos el socket en el cofre
      };

      ws.onmessage = (event) => {
        try {
          const eventData = JSON.parse(event.data);
          if (eventData.type === 'new_alert') {
            const newAlert = eventData.alert;

            setAlerts(prevAlerts => {
              if (prevAlerts.some(a => a.id === newAlert.id)) return prevAlerts;

              const updated = [newAlert, ...prevAlerts];
              if (newAlert.risk_score > 0.7) {
                setFlashScreen(true);
                setTimeout(() => setFlashScreen(false), 1000);

                if (soundEnabledRef.current) {
                  playAlertSound();
                }
              }
              return updated;
            });
          }
        } catch (e) {
          console.error("Error al procesar alerta:", e);
        }
      };

      ws.onclose = () => {
        console.log("WebSocket cerrado. Reintentando...");
        setWsStatus('DISCONNECTED');
        wsRef.current = null;
        isConnectingRef.current = false;
        // Solo reintenta si el componente sigue vivo
        reconnectTimeout = setTimeout(connectWS, 3000);
      };

      ws.onerror = () => {
        // No cerramos manualmente, dejamos que onclose lo maneje
        isConnectingRef.current = false;
      };
    };

    connectWS();

    return () => {
      // Al salir del Dashboard, limpiamos TODO
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        // Le quitamos el onclose para que no intente reconectar como zombie
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  // Format date utility
  const formatTimestamp = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('es-BO', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    } catch (e) {
      return isoString;
    }
  };

  // Derived metrics
  const totalAlerts = alerts.length;
  const criticalAlerts = alerts.filter(a => a.risk_score > 0.7);
  const warningAlerts = alerts.filter(a => a.risk_score > 0.4 && a.risk_score <= 0.7);
  const uniqueCameras = ['ALL', ...new Set(alerts.map(a => a.camera_id))];

  // Filtering alerts
  const filteredAlerts = alerts.filter(alert => {
    const matchesSearch =
      alert.camera_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      alert.rules_triggered.some(r => r.toLowerCase().includes(searchTerm.toLowerCase()));

    let matchesRisk = true;
    if (selectedRiskFilter === 'CRITICAL') {
      matchesRisk = alert.risk_score > 0.7;
    } else if (selectedRiskFilter === 'WARNING') {
      matchesRisk = alert.risk_score > 0.4 && alert.risk_score <= 0.7;
    } else if (selectedRiskFilter === 'LOW') {
      matchesRisk = alert.risk_score <= 0.4;
    }

    const matchesCamera = selectedCameraFilter === 'ALL' || alert.camera_id === selectedCameraFilter;
    return matchesSearch && matchesRisk && matchesCamera;
  });

  return (
    <div className={`transition-colors duration-300 rounded-2xl ${flashScreen ? 'bg-red-950/40 p-4 border border-red-500' : ''}`}>

      {/* Top Banner Flash Alert */}
      {flashScreen && (
        <div className="bg-red-600 text-white text-center py-2 font-bold animate-pulse uppercase tracking-widest flex items-center justify-center gap-2 text-sm z-50 fixed top-0 left-0 w-full shadow-lg">
          <ShieldAlert className="w-5 h-5 animate-bounce" />
          ¡ALERTA CRÍTICA DETECTADA EN TIEMPO REAL!
          <ShieldAlert className="w-5 h-5 animate-bounce" />
        </div>
      )}

      {/* Header and Controls Row */}
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-6 bg-[#0f1524]/60 border border-gray-800 p-4 rounded-xl">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setActiveTab('security')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs uppercase tracking-wider font-bold transition-all cursor-pointer ${
              activeTab === 'security'
                ? 'bg-cyan-950/40 border-cyan-500 text-cyan-400'
                : 'bg-transparent border-transparent text-gray-400 hover:text-white'
            }`}
          >
            <Activity className="w-4 h-4" />
            Seguridad (Alertas WS)
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs uppercase tracking-wider font-bold transition-all cursor-pointer ${
              activeTab === 'analytics'
                ? 'bg-indigo-950/40 border-indigo-500 text-indigo-400'
                : 'bg-transparent border-transparent text-gray-400 hover:text-white'
            }`}
          >
            <BarChart2 className="w-4 h-4" />
            Analítica Comercial
          </button>
        </div>
        <div className="flex items-center gap-3">
          {/* WS Connection Indicator */}
          <div className="flex items-center gap-2 bg-gray-800/80 px-3 py-1.5 rounded-lg border border-gray-700/50">
            <span className={`h-2.5 w-2.5 rounded-full ${wsStatus === 'CONNECTED' ? 'bg-green-500 animate-pulse' : wsStatus === 'CONNECTING' ? 'bg-yellow-500 animate-bounce' : 'bg-red-500'
              }`} />
            <span className="text-[10px] font-mono font-bold text-gray-300">
              WS: {wsStatus}
            </span>
          </div>
          {/* Sound Mute */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`p-2 rounded-lg border transition-all duration-200 ${soundEnabled ? 'bg-red-950/40 border-red-500/50 text-red-400' : 'bg-gray-800/80 border-gray-700 text-gray-400 hover:text-white'}`}
            title={soundEnabled ? "Desactivar alarma acústica" : "Activar alarma acústica"}
          >
            {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
          {/* Manual Sync */}
          <button
            onClick={loginAndFetch}
            className="flex items-center gap-1.5 px-3 py-2 bg-gray-800/80 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Sincronizar
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-950/30 border border-red-900/50 rounded-xl flex items-start gap-3 text-red-300">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-semibold">Error de Conexión</p>
            <p className="text-red-400 mt-1">{error}</p>
          </div>
        </div>
      )}

      {activeTab === 'security' ? (
        <>
          {/* Dashboard KPI Grid inside Component */}
          <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden">
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Alarmas Activas</p>
          <h3 className="text-2xl font-black text-white mt-1 font-mono">{totalAlerts}</h3>
          <span className="text-[9px] text-gray-500">Historial total en DB</span>
        </div>

        <div className={`border rounded-xl p-4 relative overflow-hidden transition-all ${criticalAlerts.length > 0 ? 'bg-red-950/20 border-red-900/40' : 'bg-[#0f1524]/60 border-gray-800'}`}>
          <p className="text-[10px] font-bold text-red-400 uppercase tracking-wider flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-ping" />
            Casos Críticos (&gt;70%)
          </p>
          <h3 className="text-2xl font-black text-red-500 mt-1 font-mono">{criticalAlerts.length}</h3>
          <span className="text-[9px] text-red-400/80">Acciones de riesgo detectadas</span>
        </div>

        <div className={`border rounded-xl p-4 relative overflow-hidden transition-all ${warningAlerts.length > 0 ? 'bg-amber-950/10 border-amber-900/30' : 'bg-[#0f1524]/60 border-gray-800'}`}>
          <p className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Sospechosos (40-70%)</p>
          <h3 className="text-2xl font-black text-amber-400 mt-1 font-mono">{warningAlerts.length}</h3>
          <span className="text-[9px] text-amber-400/80">Comportamientos atípicos</span>
        </div>
      </section>

      {/* Filters and Controls */}
      <section className="bg-[#0f1524]/40 border border-gray-800/80 rounded-xl p-4 mb-6 flex flex-col lg:flex-row gap-4 items-center justify-between">
        <div className="relative w-full lg:w-80">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por regla o cámara..."
            className="w-full bg-[#0a0f1d] border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto text-xs">
          <div className="flex items-center gap-1 bg-gray-900/60 p-1 rounded-lg border border-gray-800">
            <span className="text-gray-500 px-1 font-medium text-[10px]">Riesgo:</span>
            <button
              onClick={() => setSelectedRiskFilter('ALL')}
              className={`px-2 py-0.5 rounded text-[10px] ${selectedRiskFilter === 'ALL' ? 'bg-cyan-500 text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Todos
            </button>
            <button
              onClick={() => setSelectedRiskFilter('CRITICAL')}
              className={`px-2 py-0.5 rounded text-[10px] ${selectedRiskFilter === 'CRITICAL' ? 'bg-red-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              Crítico
            </button>
          </div>

          <div className="flex items-center gap-1 bg-gray-900/60 p-1 rounded-lg border border-gray-800">
            <span className="text-gray-500 px-1 font-medium text-[10px]">Cámara:</span>
            <select
              value={selectedCameraFilter}
              onChange={(e) => setSelectedCameraFilter(e.target.value)}
              className="bg-transparent text-[10px] text-gray-300 font-medium focus:outline-none pr-1 border-none cursor-pointer"
            >
              {uniqueCameras.map(cam => (
                <option key={cam} value={cam} className="bg-gray-900 text-gray-300">
                  {cam === 'ALL' ? 'Todas' : cam}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Main Grid: Alert list and inspector */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* List (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="flex justify-between items-center px-1">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 m-0 uppercase tracking-wide">
              Alertas Recientes ({filteredAlerts.length})
            </h3>
            {loading && <span className="text-[10px] text-gray-400 animate-pulse">Sincronizando...</span>}
          </div>

          {filteredAlerts.length === 0 ? (
            <div className="bg-[#0f1524]/30 border border-gray-800 rounded-xl p-12 text-center flex flex-col items-center justify-center">
              <ShieldCheck className="w-10 h-10 text-gray-600 mb-2" />
              <p className="text-xs font-semibold text-gray-400">Sin Alertas Detectadas</p>
            </div>
          ) : (
            <div className="flex flex-col gap-3 max-h-[500px] overflow-y-auto pr-1">
              {filteredAlerts.map((alert) => {
                const isCritical = alert.risk_score > 0.7;
                const isWarning = alert.risk_score > 0.4 && alert.risk_score <= 0.7;

                return (
                  <div
                    key={alert.id}
                    onClick={() => setSelectedAlert(alert)}
                    className={`cursor-pointer rounded-xl border p-4 shadow-sm transition-all duration-200 relative group overflow-hidden ${selectedAlert?.id === alert.id
                      ? isCritical
                        ? 'bg-red-950/35 border-red-500'
                        : isWarning
                          ? 'bg-amber-950/30 border-amber-500'
                          : 'bg-slate-900 border-cyan-500'
                      : isCritical
                        ? 'bg-red-950/10 border-red-900/60 hover:bg-red-950/20 hover:border-red-500'
                        : isWarning
                          ? 'bg-[#0f1524]/60 border-amber-900/30 hover:bg-amber-950/10 hover:border-amber-500'
                          : 'bg-[#0f1524]/60 border-gray-800 hover:bg-[#121b2f] hover:border-gray-700'
                      }`}
                  >
                    {isCritical && (
                      <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-red-500 to-orange-600 animate-pulse" />
                    )}
                    {isWarning && (
                      <div className="absolute top-0 left-0 w-1.5 h-full bg-amber-500" />
                    )}

                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center gap-2 text-[10px]">
                          <span className="flex items-center gap-1 text-gray-300 bg-gray-800 px-2 py-0.5 rounded font-mono font-semibold">
                            <Camera className="w-3 h-3 text-indigo-400" />
                            {alert.camera_id}
                          </span>
                          <span className="flex items-center gap-1 text-gray-400 font-mono">
                            <Clock className="w-3 h-3" />
                            {formatTimestamp(alert.timestamp)}
                          </span>
                        </div>

                        <div className="mt-2.5">
                          <span className="text-[10px] text-gray-500 font-semibold">Reglas:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {alert.rules_triggered && alert.rules_triggered.length > 0 ? (
                              alert.rules_triggered.map((rule, idx) => (
                                <span
                                  key={idx}
                                  className={`text-[9px] px-2 py-0.5 rounded-full font-medium ${isCritical
                                    ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                                    : isWarning
                                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                      : 'bg-gray-800 text-gray-300 border border-gray-700'
                                    }`}
                                >
                                  {rule}
                                </span>
                              ))
                            ) : (
                              <span className="text-[9px] text-gray-500 italic">Ninguna rule</span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-col items-end shrink-0 gap-1">
                        <span className="text-[9px] text-gray-500 font-bold uppercase">Score</span>
                        <div className="flex items-center gap-1">
                          {isCritical && <AlertTriangle className="w-3.5 h-3.5 text-red-500 animate-pulse" />}
                          <span className={`text-lg font-black font-mono leading-none ${isCritical ? 'text-red-500' : isWarning ? 'text-amber-500' : 'text-green-500'
                            }`}>
                            {Math.round(alert.risk_score * 100)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Detail Panel (5 cols) */}
        <div className="lg:col-span-5">
          <div className="sticky top-4">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2 px-1 uppercase tracking-wide">
              <Video className="w-4 h-4 text-cyan-400" />
              Inspector Inteligente
            </h3>

            {!selectedAlert ? (
              <div className="bg-[#0f1524]/40 border border-gray-800 rounded-2xl p-8 text-center flex flex-col items-center justify-center min-h-[350px]">
                <Video className="w-12 h-12 text-gray-700 mb-2 animate-pulse" />
                <p className="text-xs font-semibold text-gray-400">Selecciona una alerta</p>
                <p className="text-[10px] text-gray-500 mt-1 max-w-[180px]">Haz clic en una alerta para ver la reconstrucción del esqueleto y datos del clip.</p>
              </div>
            ) : (
              <div className="bg-[#0f1524]/85 border border-gray-800 rounded-2xl p-4 flex flex-col gap-4 shadow-lg">
                <div className="flex justify-between items-center pb-2 border-b border-gray-800/80">
                  <div>
                    <h4 className="font-extrabold text-white text-xs font-mono">
                      CÁMARA: {selectedAlert.camera_id}
                    </h4>
                    <p className="text-[9px] text-gray-400 mt-0.5 font-mono">
                      Alert ID: #{selectedAlert.id}
                    </p>
                  </div>
                  <div className={`px-2 py-0.5 rounded text-[10px] font-black font-mono ${selectedAlert.risk_score > 0.7
                    ? 'bg-red-950/60 border border-red-500/30 text-red-500'
                    : 'bg-green-950/40 border border-green-500/30 text-green-500'
                    }`}>
                    {Math.round(selectedAlert.risk_score * 100)}% RIESGO
                  </div>
                </div>

                {/* Simulated Skeleton visualizer */}
                <div className="relative aspect-video bg-black rounded-lg border border-gray-800 overflow-hidden flex items-center justify-center">
                  <div className="absolute inset-0 z-10 flex flex-col justify-between p-2 pointer-events-none">
                    <span className="bg-red-600/90 text-white font-mono text-[8px] px-1.5 py-0.5 rounded font-bold uppercase animate-pulse self-start">
                      REPLAY
                    </span>
                    <span className="bg-black/75 text-[8px] font-mono text-cyan-400 px-1.5 py-0.5 rounded border border-gray-800/60 self-center">
                      Visualizador Esqueleto MediaPipe
                    </span>
                  </div>

                  <div className="absolute inset-0 bg-gradient-to-tr from-gray-950 via-[#101524] to-gray-900 opacity-90" />

                  <div className="absolute inset-0 border border-cyan-500/10 m-4 rounded pointer-events-none flex items-center justify-center">
                    <svg className="w-full h-full text-cyan-400/80" viewBox="0 0 100 100">
                      <circle cx="50" cy="25" r="3.5" className={selectedAlert.risk_score > 0.7 ? 'text-red-500 fill-current animate-ping' : 'text-cyan-400 fill-current'} />
                      <line x1="50" y1="28" x2="50" y2="50" stroke="currentColor" strokeWidth="1.2" />
                      <line x1="42" y1="32" x2="58" y2="32" stroke="currentColor" strokeWidth="1.2" />
                      {/* Left arm bent (hidden in pocket logic) */}
                      <line x1="42" y1="32" x2="38" y2="40" stroke="currentColor" strokeWidth="1.2" />
                      <line x1="38" y1="40" x2="44" y2="44" stroke="currentColor" strokeWidth="1.8" className={selectedAlert.rules_triggered.some(r => r.includes('Mano')) ? 'text-red-500 animate-pulse' : 'text-indigo-400'} />
                      {/* Right arm */}
                      <line x1="58" y1="32" x2="62" y2="44" stroke="currentColor" strokeWidth="1.2" />
                      <line x1="62" y1="44" x2="60" y2="54" stroke="currentColor" strokeWidth="1.2" />
                      {/* Legs */}
                      <line x1="45" y1="50" x2="55" y2="50" stroke="currentColor" strokeWidth="1.2" />
                      <line x1="45" y1="50" x2="41" y2="60" stroke="currentColor" strokeWidth="1.2" />
                      <line x1="41" y1="60" x2="47" y2="70" stroke="currentColor" strokeWidth="1.2" className={selectedAlert.rules_triggered.some(r => r.includes('Inclinacion') || r.includes('Agacha')) ? 'text-red-500 animate-pulse' : 'text-indigo-400'} />
                      <line x1="55" y1="50" x2="59" y2="62" stroke="currentColor" strokeWidth="1.2" />
                      <line x1="59" y1="62" x2="55" y2="72" stroke="currentColor" strokeWidth="1.2" />
                    </svg>
                  </div>

                  <div className="z-20 text-center flex flex-col items-center">
                    <div className="bg-[#0b0f19]/80 border border-gray-700/40 p-3 rounded-lg max-w-[200px] text-[10px]">
                      <Video className="w-5 h-5 text-cyan-400 mx-auto mb-1" />
                      <p className="font-semibold text-gray-200">Clip en Nodo Local</p>
                      <p className="text-[9px] text-gray-400 font-mono truncate">{selectedAlert.video_path || "Sin video registrado"}</p>
                    </div>
                  </div>
                </div>

                {/* Metadata */}
                <div className="bg-[#0a0f1d] border border-gray-800/80 rounded-xl p-3 flex flex-col gap-2.5 text-[11px]">
                  <div className="grid grid-cols-2 gap-2 text-gray-400">
                    <div>
                      <span>Fecha</span>
                      <span className="font-mono text-gray-200 block mt-0.5">{formatTimestamp(selectedAlert.timestamp)}</span>
                    </div>
                    <div>
                      <span>Ruta de Video</span>
                      <span className="font-mono text-gray-200 block mt-0.5 truncate">{selectedAlert.video_path || 'N/A'}</span>
                    </div>
                  </div>

                  <div>
                    <span className="text-gray-500">Reglas Infringidas:</span>
                    <div className="flex flex-col gap-1 mt-1">
                      {selectedAlert.rules_triggered && selectedAlert.rules_triggered.length > 0 ? (
                        selectedAlert.rules_triggered.map((rule, idx) => (
                          <div key={idx} className="bg-gray-900 border border-gray-800 px-2.5 py-1 rounded text-gray-300 font-mono text-[10px]">
                            {rule}
                          </div>
                        ))
                      ) : (
                        <div className="text-[10px] text-gray-500 italic">Ninguna regla violada.</div>
                      )}
                    </div>
                  </div>

                  <div className="mt-2 pt-2 border-t border-gray-800/80 flex gap-2">
                    <button
                      onClick={() => alert(`Reproduciendo clip en Edge: \n${selectedAlert.video_path}`)}
                      className="flex-1 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-bold text-[10px] flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <Play className="w-3 h-3 fill-white" /> Reproducir Clip
                    </button>
                    <button
                      onClick={() => setSelectedAlert(null)}
                      className="px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[10px] cursor-pointer"
                    >
                      Cerrar
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

      </section>
        </>
      ) : (
        <AnalyticsPanel token={token} />
      )}

    </div>
  );
}
