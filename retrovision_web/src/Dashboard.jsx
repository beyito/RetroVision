import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  ShieldAlert, Video, Activity, RefreshCw, Search, Filter, 
  Clock, Camera, AlertTriangle, Eye, ShieldCheck, Volume2, VolumeX,
  Play, Calendar, Info
} from 'lucide-react';

export default function Dashboard() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastChecked, setLastChecked] = useState(new Date());
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState('ALL'); // ALL, CRITICAL, WARNING, LOW
  const [selectedCameraFilter, setSelectedCameraFilter] = useState('ALL');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [flashScreen, setFlashScreen] = useState(false);
  
  const prevAlertsCountRef = useRef(0);
  const audioContextRef = useRef(null);

  // Fetch alerts function
  const fetchAlerts = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/alerts/');
      const data = response.data;
      setAlerts(data);
      setError(null);
      
      // Check for new critical alerts
      if (data.length > 0) {
        const criticalAlerts = data.filter(a => a.risk_score > 0.7);
        const prevCriticalCount = prevAlertsCountRef.current;
        
        if (criticalAlerts.length > prevCriticalCount) {
          // Trigger visual flash
          setFlashScreen(true);
          setTimeout(() => setFlashScreen(false), 1000);
          
          // Trigger sound if enabled
          if (soundEnabled) {
            playAlertSound();
          }
        }
        prevAlertsCountRef.current = criticalAlerts.length;
      }
    } catch (err) {
      console.error("Error fetching security alerts:", err);
      setError("No se pudo conectar con el servidor central de RetroVision.");
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  };

  // Sound generator using Web Audio API (no external file needed!)
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
      osc.frequency.setValueAtTime(660, ctx.currentTime); // A5 note
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

  // Setup periodic polling
  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(() => {
      fetchAlerts(true);
    }, 3000); // Poll every 3 seconds for near-real-time updates
    return () => clearInterval(interval);
  }, [soundEnabled]);

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
    // 1. Search term match (rules triggered or camera id)
    const matchesSearch = 
      alert.camera_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      alert.rules_triggered.some(r => r.toLowerCase().includes(searchTerm.toLowerCase()));
      
    // 2. Risk filter match
    let matchesRisk = true;
    if (selectedRiskFilter === 'CRITICAL') {
      matchesRisk = alert.risk_score > 0.7;
    } else if (selectedRiskFilter === 'WARNING') {
      matchesRisk = alert.risk_score > 0.4 && alert.risk_score <= 0.7;
    } else if (selectedRiskFilter === 'LOW') {
      matchesRisk = alert.risk_score <= 0.4;
    }

    // 3. Camera filter match
    const matchesCamera = selectedCameraFilter === 'ALL' || alert.camera_id === selectedCameraFilter;

    return matchesSearch && matchesRisk && matchesCamera;
  });

  return (
    <div className={`min-h-screen bg-[#0b0f19] text-gray-100 transition-colors duration-300 ${flashScreen ? 'bg-red-950/40' : ''}`}>
      
      {/* Top Banner Flash Alert */}
      {flashScreen && (
        <div className="bg-red-600 text-white text-center py-2 font-bold animate-pulse uppercase tracking-widest flex items-center justify-center gap-2 text-sm z-50 fixed top-0 left-0 w-full shadow-lg">
          <ShieldAlert className="w-5 h-5 animate-bounce" />
          ¡ALERTA CRÍTICA DETECTADA EN TIEMPO REAL!
          <ShieldAlert className="w-5 h-5 animate-bounce" />
        </div>
      )}

      {/* Navigation Header */}
      <header className="border-b border-gray-800 bg-[#0f1524]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-tr from-cyan-500 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-indigo-500/20">
              <Activity className="w-6 h-6 text-white animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent m-0">
                RetroVision <span className="text-cyan-400 font-mono text-sm border border-cyan-400/30 px-2 py-0.5 rounded-full ml-2">CORE</span>
              </h1>
              <p className="text-xs text-gray-400">Panel Centralizado de Videovigilancia y Analítica IA</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Live Indicator */}
            <div className="flex items-center gap-2 bg-gray-800/60 px-3 py-1.5 rounded-lg border border-gray-700/50">
              <span className={`h-2.5 w-2.5 rounded-full ${error ? 'bg-red-500 animate-ping' : 'bg-green-500 animate-pulse'}`} />
              <span className="text-xs font-mono font-semibold">
                {error ? 'DESCONECTADO' : 'CONEXIÓN ACTIVA'}
              </span>
            </div>

            {/* Audio Toggle */}
            <button 
              onClick={() => setSoundEnabled(!soundEnabled)} 
              className={`p-2 rounded-lg border transition-all duration-200 ${soundEnabled ? 'bg-red-950/40 border-red-500/50 text-red-400' : 'bg-gray-800/80 border-gray-700 text-gray-400 hover:text-white'}`}
              title={soundEnabled ? "Desactivar alarma acústica" : "Activar alarma acústica"}
            >
              {soundEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
            </button>

            {/* Refresh button */}
            <button
              onClick={() => fetchAlerts()}
              className="flex items-center gap-1.5 px-3 py-2 bg-gray-800/80 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 rounded-lg text-xs font-medium transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Sincronizar
            </button>

            <span className="text-xs text-gray-500 font-mono hidden lg:inline-block">
              Último escaneo: {lastChecked.toLocaleTimeString()}
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Error notification */}
        {error && (
          <div className="mb-6 p-4 bg-red-950/30 border border-red-900/50 rounded-xl flex items-start gap-3 text-red-300">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Error de Comunicación</p>
              <p className="text-xs text-red-400 mt-1">{error}</p>
              <p className="text-xs text-gray-400 mt-2">Asegúrate de que el backend central Django está corriendo en `http://localhost:8000` y CORS está configurado.</p>
            </div>
          </div>
        )}

        {/* Dashboard Grid - KPI Metrics */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          
          {/* Card 1: Total Alerts */}
          <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-5 shadow-sm hover:border-gray-700 transition-all duration-300 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
              <Activity className="w-12 h-12 text-cyan-400" />
            </div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Alertas Totales</p>
            <h3 className="text-3xl font-extrabold text-white mt-2 font-mono">
              {loading && alerts.length === 0 ? '...' : totalAlerts}
            </h3>
            <p className="text-xs text-gray-400 mt-1.5 flex items-center gap-1">
              <span className="text-green-400 font-medium">Historial global</span> guardado en base de datos
            </p>
          </div>

          {/* Card 2: Critical Alerts */}
          <div className={`border rounded-xl p-5 shadow-sm transition-all duration-300 relative overflow-hidden group ${criticalAlerts.length > 0 ? 'bg-red-950/20 border-red-900/50' : 'bg-[#0f1524]/60 border-gray-800'}`}>
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
              <ShieldAlert className="w-12 h-12 text-red-400" />
            </div>
            <p className="text-xs font-semibold text-red-400 uppercase tracking-wider flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-red-500 animate-ping" />
              Eventos Críticos
            </p>
            <h3 className="text-3xl font-extrabold text-red-500 mt-2 font-mono">
              {loading && alerts.length === 0 ? '...' : criticalAlerts.length}
            </h3>
            <p className="text-xs text-red-300/80 mt-1.5">
              Riesgo detectado superior a 70% (alarma)
            </p>
          </div>

          {/* Card 3: Warning Alerts */}
          <div className={`border rounded-xl p-5 shadow-sm transition-all duration-300 relative overflow-hidden group ${warningAlerts.length > 0 ? 'bg-amber-950/10 border-amber-900/30' : 'bg-[#0f1524]/60 border-gray-800'}`}>
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
              <AlertTriangle className="w-12 h-12 text-amber-400" />
            </div>
            <p className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Eventos Sospechosos</p>
            <h3 className="text-3xl font-extrabold text-amber-400 mt-2 font-mono">
              {loading && alerts.length === 0 ? '...' : warningAlerts.length}
            </h3>
            <p className="text-xs text-amber-300/80 mt-1.5">
              Riesgo intermedio entre 40% y 70%
            </p>
          </div>

          {/* Card 4: Active Cameras */}
          <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-5 shadow-sm hover:border-gray-700 transition-all duration-300 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
              <Camera className="w-12 h-12 text-indigo-400" />
            </div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Cámaras Activas</p>
            <h3 className="text-3xl font-extrabold text-white mt-2 font-mono">
              {uniqueCameras.length - 1}
            </h3>
            <p className="text-xs text-gray-400 mt-1.5">
              Nodos de Edge reportando datos
            </p>
          </div>
        </section>

        {/* Filters and Controls */}
        <section className="bg-[#0f1524]/40 border border-gray-800/80 rounded-xl p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
            {/* Search Input */}
            <div className="relative w-full lg:w-96">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar por regla (ej. Manos Ocultas) o cámara..."
                className="w-full bg-[#0a0f1d] border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
              />
            </div>

            {/* Filter Pills */}
            <div className="flex flex-wrap items-center gap-4 w-full lg:w-auto">
              
              {/* Risk Levels filter */}
              <div className="flex items-center gap-1.5 bg-gray-900/60 p-1 rounded-lg border border-gray-800">
                <span className="text-xs text-gray-500 px-2 font-medium">Nivel:</span>
                <button
                  onClick={() => setSelectedRiskFilter('ALL')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${selectedRiskFilter === 'ALL' ? 'bg-cyan-500 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  Todos
                </button>
                <button
                  onClick={() => setSelectedRiskFilter('CRITICAL')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${selectedRiskFilter === 'CRITICAL' ? 'bg-red-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  Crítico (&gt;0.7)
                </button>
                <button
                  onClick={() => setSelectedRiskFilter('WARNING')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${selectedRiskFilter === 'WARNING' ? 'bg-amber-600 text-white shadow-sm' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  Sospecha (0.4-0.7)
                </button>
              </div>

              {/* Cameras filter */}
              <div className="flex items-center gap-1.5 bg-gray-900/60 p-1 rounded-lg border border-gray-800">
                <span className="text-xs text-gray-500 px-2 font-medium">Cámara:</span>
                <select
                  value={selectedCameraFilter}
                  onChange={(e) => setSelectedCameraFilter(e.target.value)}
                  className="bg-transparent text-xs text-gray-300 font-medium focus:outline-none pr-2 border-none cursor-pointer"
                >
                  {uniqueCameras.map(cam => (
                    <option key={cam} value={cam} className="bg-gray-900 text-gray-300">
                      {cam === 'ALL' ? 'Todas las Cámaras' : cam}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Reset filter button */}
              {(searchTerm !== '' || selectedRiskFilter !== 'ALL' || selectedCameraFilter !== 'ALL') && (
                <button 
                  onClick={() => {
                    setSearchTerm('');
                    setSelectedRiskFilter('ALL');
                    setSelectedCameraFilter('ALL');
                  }}
                  className="text-xs text-cyan-400 hover:text-cyan-300 font-medium underline"
                >
                  Limpiar Filtros
                </button>
              )}

            </div>
          </div>
        </section>

        {/* Content Section: Alert Grid & Inspector Panel */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Alerts List - taking 7/12 cols */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            <div className="flex justify-between items-center px-1">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-cyan-400" />
                Alertas Recientes ({filteredAlerts.length})
              </h2>
              {loading && <span className="text-xs text-gray-400 animate-pulse">Sincronizando con base de datos...</span>}
            </div>

            {/* Empty state */}
            {filteredAlerts.length === 0 ? (
              <div className="bg-[#0f1524]/30 border border-gray-800 rounded-xl p-12 text-center flex flex-col items-center justify-center">
                <ShieldCheck className="w-12 h-12 text-gray-600 mb-3" />
                <p className="font-semibold text-gray-400">Sin Alertas Detectadas</p>
                <p className="text-xs text-gray-500 mt-1 max-w-sm">No se encontraron alertas en la base de datos que cumplan los filtros actuales.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3 max-h-[600px] overflow-y-auto pr-1">
                {filteredAlerts.map((alert) => {
                  const isCritical = alert.risk_score > 0.7;
                  const isWarning = alert.risk_score > 0.4 && alert.risk_score <= 0.7;
                  
                  return (
                    <div 
                      key={alert.id}
                      onClick={() => setSelectedAlert(alert)}
                      className={`cursor-pointer rounded-xl border p-4 shadow-sm transition-all duration-200 relative group overflow-hidden ${
                        selectedAlert?.id === alert.id 
                          ? isCritical 
                            ? 'bg-red-950/35 border-red-500 shadow-red-950/20' 
                            : isWarning 
                              ? 'bg-amber-950/30 border-amber-500 shadow-amber-950/20'
                              : 'bg-slate-900 border-cyan-500 shadow-cyan-950/10'
                          : isCritical 
                            ? 'bg-red-950/10 border-red-900/60 hover:bg-red-950/20 hover:border-red-500 shadow-red-950/5' 
                            : isWarning 
                              ? 'bg-[#0f1524]/60 border-amber-900/30 hover:bg-amber-950/10 hover:border-amber-500/50'
                              : 'bg-[#0f1524]/60 border-gray-800 hover:bg-[#121b2f] hover:border-gray-700'
                      }`}
                    >
                      {/* Critical warning light border */}
                      {isCritical && (
                        <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-red-500 to-orange-600 animate-pulse" />
                      )}
                      {isWarning && (
                        <div className="absolute top-0 left-0 w-1.5 h-full bg-amber-500" />
                      )}

                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          
                          {/* Alert header: Camera & Timestamp */}
                          <div className="flex flex-wrap items-center gap-2 text-xs">
                            <span className="flex items-center gap-1 text-gray-300 bg-gray-800 px-2 py-0.5 rounded font-mono font-medium">
                              <Camera className="w-3.5 h-3.5 text-indigo-400" />
                              {alert.camera_id}
                            </span>
                            <span className="flex items-center gap-1 text-gray-400 font-mono">
                              <Clock className="w-3.5 h-3.5" />
                              {formatTimestamp(alert.timestamp)}
                            </span>
                          </div>

                          {/* Triggered rules list */}
                          <div className="mt-3">
                            <p className="text-xs text-gray-400 font-semibold mb-1">Reglas infringidas:</p>
                            <div className="flex flex-wrap gap-1.5">
                              {alert.rules_triggered && alert.rules_triggered.length > 0 ? (
                                alert.rules_triggered.map((rule, idx) => (
                                  <span 
                                    key={idx} 
                                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                                      isCritical 
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
                                <span className="text-[10px] text-gray-500 italic">Ninguna regla explícita</span>
                              )}
                            </div>
                          </div>

                        </div>

                        {/* Risk score circle/badge */}
                        <div className="flex flex-col items-end shrink-0 gap-1.5">
                          <div className="text-right">
                            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Score de Riesgo</p>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              {isCritical && <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" />}
                              <span className={`text-xl font-black font-mono leading-none ${
                                isCritical ? 'text-red-500' : isWarning ? 'text-amber-500' : 'text-green-500'
                              }`}>
                                {Math.round(alert.risk_score * 100)}%
                              </span>
                            </div>
                          </div>

                          {/* Simple action indicator */}
                          <span className="text-[10px] text-cyan-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 mt-1">
                            Inspeccionar <Eye className="w-3.5 h-3.5" />
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Inspector Panel / Drawer - taking 5/12 cols */}
          <div className="lg:col-span-5">
            <div className="sticky top-28">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2 px-1">
                <Video className="w-5 h-5 text-cyan-400" />
                Inspector de Video y Landmarks
              </h2>

              {!selectedAlert ? (
                <div className="bg-[#0f1524]/40 border border-gray-800 rounded-2xl p-8 text-center flex flex-col items-center justify-center min-h-[400px]">
                  <Video className="w-16 h-16 text-gray-700 mb-3 animate-pulse" />
                  <p className="text-sm font-semibold text-gray-400">Ninguna alerta seleccionada</p>
                  <p className="text-xs text-gray-500 mt-1 max-w-[200px]">Selecciona una alerta de la lista de la izquierda para reproducir su clip de seguridad y visualizar los metadatos.</p>
                </div>
              ) : (
                <div className={`bg-[#0f1524]/80 border rounded-2xl p-5 shadow-lg flex flex-col gap-4 overflow-hidden transition-all duration-300 ${
                  selectedAlert.risk_score > 0.7 ? 'border-red-900/50 shadow-red-950/10' : 'border-gray-800'
                }`}>
                  
                  {/* Visualizer header */}
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-extrabold text-white text-md flex items-center gap-1.5 font-mono">
                        Cámara ID: {selectedAlert.camera_id}
                      </h3>
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        Alert ID: #{selectedAlert.id} | Timestamp: {formatTimestamp(selectedAlert.timestamp)}
                      </p>
                    </div>
                    
                    {/* Risk Badge */}
                    <div className={`px-2.5 py-1 rounded-lg text-xs font-extrabold font-mono ${
                      selectedAlert.risk_score > 0.7 
                        ? 'bg-red-950/60 border border-red-500/50 text-red-500' 
                        : selectedAlert.risk_score > 0.4 
                          ? 'bg-amber-950/40 border border-amber-500/30 text-amber-500' 
                          : 'bg-green-950/40 border border-green-500/30 text-green-500'
                    }`}>
                      RIESGO: {Math.round(selectedAlert.risk_score * 100)}%
                    </div>
                  </div>

                  {/* Simulated Video Player */}
                  <div className="relative aspect-video bg-black rounded-xl border border-gray-800 overflow-hidden flex items-center justify-center group/player">
                    
                    {/* MediaPipe Landmarks overlay mockup */}
                    <div className="absolute inset-0 z-10 flex flex-col justify-between p-3 pointer-events-none">
                      <div className="flex justify-between">
                        <span className="bg-red-600/90 text-white font-mono text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider animate-pulse flex items-center gap-1">
                          <Play className="w-2.5 h-2.5 fill-white" /> LIVE REPLAY
                        </span>
                        <span className="bg-black/70 backdrop-blur-sm text-[9px] font-mono text-gray-300 px-1.5 py-0.5 rounded border border-gray-800">
                          FPS: 30 | MediaPipe Active
                        </span>
                      </div>
                      
                      {/* Body landmarks mockup skeleton line */}
                      <div className="w-full text-center">
                        <span className="bg-indigo-900/90 backdrop-blur-sm text-[10px] text-indigo-200 px-2 py-0.5 rounded-full border border-indigo-700/50 font-medium">
                          YOLOv8n + Extraer Esqueleto Activo
                        </span>
                      </div>
                    </div>

                    {/* Styled video screen representation */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-gray-950 via-[#101524] to-gray-900 opacity-90" />
                    
                    {/* Drawing a futuristic sci-fi visualizer target box / grid overlay */}
                    <div className="absolute inset-0 border border-cyan-500/20 m-6 rounded-lg pointer-events-none flex items-center justify-center">
                      <div className="w-8 h-8 border-t-2 border-l-2 border-cyan-400 absolute top-0 left-0" />
                      <div className="w-8 h-8 border-t-2 border-r-2 border-cyan-400 absolute top-0 right-0" />
                      <div className="w-8 h-8 border-b-2 border-l-2 border-cyan-400 absolute bottom-0 left-0" />
                      <div className="w-8 h-8 border-b-2 border-r-2 border-cyan-400 absolute bottom-0 right-0" />
                      
                      {/* Skeleton landmarks mockup drawing using SVGs */}
                      <svg className="w-full h-full text-cyan-400/70" viewBox="0 0 100 100">
                        {/* Head */}
                        <circle cx="50" cy="25" r="4" className={`fill-current ${selectedAlert.risk_score > 0.7 ? 'text-red-500 animate-ping' : 'text-cyan-400'}`} />
                        <circle cx="50" cy="25" r="3" className={`fill-current ${selectedAlert.risk_score > 0.7 ? 'text-red-500' : 'text-cyan-400'}`} />
                        {/* Torso */}
                        <line x1="50" y1="29" x2="50" y2="50" stroke="currentColor" strokeWidth="1.5" />
                        {/* Shoulders */}
                        <line x1="40" y1="33" x2="60" y2="33" stroke="currentColor" strokeWidth="1.5" />
                        {/* Left arm - bent / hidden in pocket */}
                        <line x1="40" y1="33" x2="36" y2="42" stroke="currentColor" strokeWidth="1.5" />
                        <line x1="36" y1="42" x2="43" y2="45" stroke="currentColor" strokeWidth="2" className={selectedAlert.rules_triggered.some(r => r.includes('Mano')) ? 'text-red-500 animate-pulse' : 'text-indigo-400'} />
                        {/* Right arm */}
                        <line x1="60" y1="33" x2="65" y2="45" stroke="currentColor" strokeWidth="1.5" />
                        <line x1="65" y1="45" x2="63" y2="55" stroke="currentColor" strokeWidth="1.5" />
                        {/* Hips */}
                        <line x1="44" y1="50" x2="56" y2="50" stroke="currentColor" strokeWidth="1.5" />
                        {/* Left leg - bent (squatting) */}
                        <line x1="44" y1="50" x2="40" y2="60" stroke="currentColor" strokeWidth="1.5" />
                        <line x1="40" y1="60" x2="48" y2="72" stroke="currentColor" strokeWidth="1.5" className={selectedAlert.rules_triggered.some(r => r.includes('Inclinacion') || r.includes('Agacha')) ? 'text-red-500 animate-pulse' : 'text-indigo-400'} />
                        {/* Right leg */}
                        <line x1="56" y1="50" x2="60" y2="62" stroke="currentColor" strokeWidth="1.5" />
                        <line x1="60" y1="62" x2="55" y2="74" stroke="currentColor" strokeWidth="1.5" />

                        {/* Interactive focus rings around suspicious points */}
                        {selectedAlert.rules_triggered.some(r => r.includes('Mano')) && (
                          <circle cx="43" cy="45" r="5" stroke="red" strokeWidth="0.5" fill="none" className="animate-ping" />
                        )}
                        {selectedAlert.rules_triggered.some(r => r.includes('Inclinacion') || r.includes('Agacha')) && (
                          <circle cx="40" cy="60" r="5" stroke="orange" strokeWidth="0.5" fill="none" className="animate-ping" />
                        )}
                      </svg>
                    </div>

                    <div className="z-20 text-center flex flex-col items-center">
                      <div className="bg-[#0b0f19]/80 border border-gray-700/50 p-4 rounded-xl flex flex-col items-center gap-2 backdrop-blur-sm max-w-[280px]">
                        <Video className="w-8 h-8 text-cyan-400" />
                        <p className="text-xs font-semibold text-gray-200">Clip Grabado Disponible</p>
                        <p className="text-[10px] text-gray-400 font-mono break-all line-clamp-2">
                          {selectedAlert.video_path || "Sin ruta de clip de video registrada"}
                        </p>
                        {selectedAlert.video_path && (
                          <div className="mt-1 flex items-center justify-center gap-2">
                            <span className="text-[9px] px-1.5 py-0.5 bg-green-500/20 text-green-300 rounded border border-green-500/30 font-semibold font-mono">
                              Clip de 30s
                            </span>
                            <span className="text-[9px] px-1.5 py-0.5 bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30 font-semibold font-mono">
                              Guardado en Edge
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Inspector metadata card details */}
                  <div className="bg-[#0a0f1d] border border-gray-800/80 rounded-xl p-4 flex flex-col gap-3">
                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-800 pb-2">Metadatos de la Alerta</p>
                    
                    <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-xs">
                      <div>
                        <span className="text-gray-500 block">ID del Registro</span>
                        <span className="font-mono text-gray-200">{selectedAlert.id}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Cámara Origen</span>
                        <span className="font-mono text-gray-200">{selectedAlert.camera_id}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Riesgo Calculado</span>
                        <span className={`font-mono font-bold ${selectedAlert.risk_score > 0.7 ? 'text-red-500' : 'text-amber-500'}`}>
                          {selectedAlert.risk_score} / 1.0 ({Math.round(selectedAlert.risk_score * 100)}%)
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Fecha y Hora</span>
                        <span className="font-mono text-gray-300">{formatTimestamp(selectedAlert.timestamp)}</span>
                      </div>
                    </div>

                    <div className="mt-1">
                      <span className="text-gray-500 block text-xs">Reglas Evaluadas por BehaviorAnalyzer</span>
                      <div className="flex flex-col gap-1.5 mt-1.5">
                        {selectedAlert.rules_triggered && selectedAlert.rules_triggered.length > 0 ? (
                          selectedAlert.rules_triggered.map((rule, idx) => (
                            <div key={idx} className="flex items-center gap-2 bg-gray-900 px-3 py-1.5 rounded-lg border border-gray-800 text-xs">
                              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shrink-0" />
                              <span className="text-gray-300 font-mono text-[11px]">{rule}</span>
                            </div>
                          ))
                        ) : (
                          <div className="text-xs text-gray-500 italic">No se reportaron anomalías que violaran las reglas establecidas.</div>
                        )}
                      </div>
                    </div>

                    {/* Actions panel */}
                    <div className="mt-3 pt-3 border-t border-gray-800/80 flex items-center justify-between gap-3">
                      <button
                        onClick={() => alert(`Simulando reproducción del clip en el Edge Node local: \n${selectedAlert.video_path}`)}
                        className="flex-1 py-2 bg-cyan-600 hover:bg-cyan-500 active:bg-cyan-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-cyan-900/10 cursor-pointer"
                      >
                        <Play className="w-3.5 h-3.5 fill-white" />
                        Ver Video Clip (30s)
                      </button>
                      <button
                        onClick={() => setSelectedAlert(null)}
                        className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs font-medium transition-colors cursor-pointer"
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

      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-gray-800 bg-[#0f1524]/40 py-6 text-center text-xs text-gray-500">
        <p>RetroVision Security Systems © 2026. Proyecto Diseñado para Feria Tecnológica.</p>
        <p className="mt-1 font-mono text-[10px]">Edge + Central Server + Real-time Web Platform</p>
      </footer>

    </div>
  );
}
