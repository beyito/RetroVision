import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import {
  Activity,
  AlertTriangle,
  BarChart2,
  Building2,
  Camera,
  Clock,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Store,
  Video,
  Volume2,
  VolumeX,
} from 'lucide-react';

import AnalyticsPanel from './AnalyticsPanel';
import ReportsPanel from './components/ReportsPanel';
import { API_BASE_URL, WS_BASE_URL } from './config';


export default function Dashboard({ token, profile }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [wsStatus, setWsStatus] = useState('DISCONNECTED');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState('ALL');
  const [selectedTenantId, setSelectedTenantId] = useState('ALL');
  const [selectedStoreId, setSelectedStoreId] = useState('ALL');
  const [selectedCameraId, setSelectedCameraId] = useState('ALL');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [flashScreen, setFlashScreen] = useState(false);
  const [activeTab, setActiveTab] = useState('security');
  const [latestTelemetry, setLatestTelemetry] = useState(null);
  const [latestHeatmap, setLatestHeatmap] = useState(null);
  const [alertsPage, setAlertsPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [scopeOptions, setScopeOptions] = useState({
    tenants: [],
    stores: [],
    cameras: [],
  });

  const wsRef = useRef(null);
  const isConnectingRef = useRef(false);
  const soundEnabledRef = useRef(soundEnabled);
  const audioContextRef = useRef(null);

  const canFilterTenants = profile?.role === 'ADMIN_SOFTWARE';

  useEffect(() => {
    soundEnabledRef.current = soundEnabled;
  }, [soundEnabled]);

  const buildQueryString = (includeCamera = true) => {
    const params = new URLSearchParams();
    if (selectedTenantId !== 'ALL') {
      params.set('tenant', selectedTenantId);
    }
    if (selectedStoreId !== 'ALL') {
      params.set('store', selectedStoreId);
    }
    if (includeCamera && selectedCameraId !== 'ALL') {
      params.set('camera_id', selectedCameraId);
    }
    const query = params.toString();
    return query ? `?${query}` : '';
  };

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
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch (soundError) {
      console.warn('No se pudo reproducir audio:', soundError);
    }
  };

  const fetchScopeOptions = async () => {
    if (!token) return;
    try {
      const storeQuery = selectedTenantId !== 'ALL' ? `?tenant=${selectedTenantId}` : '';
      const cameraQuery = buildQueryString(false);
      const requests = [
        axios.get(`${API_BASE_URL}/api/stores/${storeQuery}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        axios.get(`${API_BASE_URL}/api/cameras/${cameraQuery}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ];

      if (canFilterTenants) {
        requests.unshift(
          axios.get(`${API_BASE_URL}/api/tenants/`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        );
      }

      const responses = await Promise.all(requests);
      const offset = canFilterTenants ? 1 : 0;
      setScopeOptions({
        tenants: canFilterTenants ? responses[0].data : [],
        stores: responses[offset].data,
        cameras: responses[offset + 1].data,
      });
    } catch (scopeError) {
      console.error('Fetch scope options failed:', scopeError);
    }
  };

  const fetchAlerts = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const qString = buildQueryString(true);
      const params = new URLSearchParams(qString);
      params.set('page', alertsPage);
      
      const response = await axios.get(`${API_BASE_URL}/api/alerts/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      const results = Array.isArray(response.data)
        ? response.data
        : (response.data && Array.isArray(response.data.results)
            ? response.data.results
            : []);
      const count = Array.isArray(response.data)
        ? response.data.length
        : (response.data && typeof response.data.count === 'number'
            ? response.data.count
            : 0);
      
      setAlerts(results);
      setTotalPages(Math.ceil(count / 20) || 1);
      setError(null);
    } catch (fetchError) {
      console.error('Fetch alerts failed:', fetchError);
      setError('No se pudieron cargar las alertas del backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [token, selectedTenantId, selectedStoreId, selectedCameraId, alertsPage]);

  // Reset page when filters change
  useEffect(() => {
    setAlertsPage(1);
  }, [selectedTenantId, selectedStoreId, selectedCameraId]);

  useEffect(() => {
    fetchScopeOptions();
  }, [token, selectedTenantId, selectedStoreId, profile?.role]);

  useEffect(() => {
    setSelectedStoreId('ALL');
    setSelectedCameraId('ALL');
  }, [selectedTenantId]);

  useEffect(() => {
    setSelectedCameraId('ALL');
  }, [selectedStoreId]);

  useEffect(() => {
    let reconnectTimeout = null;

    const connectWS = () => {
      if (!token || wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) {
        return;
      }

      isConnectingRef.current = true;
      setWsStatus('CONNECTING');
      const ws = new WebSocket(`${WS_BASE_URL}/ws/alerts/`);

      ws.onopen = () => {
        wsRef.current = ws;
        isConnectingRef.current = false;
        setWsStatus('CONNECTED');
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          if (payload.type === 'telemetry_update') {
            const telemetryCam = payload.telemetry.camera_id;
            
            const cameraMatches = selectedCameraId === 'ALL' || telemetryCam === selectedCameraId;
            
            let storeMatches = true;
            if (selectedStoreId !== 'ALL') {
              const camObj = scopeOptions.cameras.find(c => String(c.camera_id) === String(telemetryCam));
              if (camObj && String(camObj.store) !== String(selectedStoreId)) {
                storeMatches = false;
              }
            }
            
            let tenantMatches = true;
            if (selectedTenantId !== 'ALL') {
              const camObj = scopeOptions.cameras.find(c => String(c.camera_id) === String(telemetryCam));
              if (camObj) {
                const storeObj = scopeOptions.stores.find(s => String(s.id) === String(camObj.store));
                if (storeObj && String(storeObj.tenant) !== String(selectedTenantId)) {
                  tenantMatches = false;
                }
              }
            }
            
            if (cameraMatches && storeMatches && tenantMatches) {
              setLatestTelemetry(payload.telemetry);
              setLatestHeatmap(payload.heatmap);
            }
            return;
          }
          
          if (payload.type !== 'new_alert') return;

          const newAlert = payload.alert;
          const tenantMatches = selectedTenantId === 'ALL' || String(newAlert.tenant_name) === String(
            scopeOptions.tenants.find((tenant) => String(tenant.id) === String(selectedTenantId))?.name || '',
          );
          const storeMatches = selectedStoreId === 'ALL' || String(newAlert.store_name) === String(
            scopeOptions.stores.find((store) => String(store.id) === String(selectedStoreId))?.name || '',
          );
          const cameraMatches = selectedCameraId === 'ALL' || newAlert.camera_id === selectedCameraId;

          if (!tenantMatches || !storeMatches || !cameraMatches) {
            return;
          }

          setAlerts((previous) => {
            const list = Array.isArray(previous) ? previous : [];
            if (list.some((item) => item.id === newAlert.id)) {
              return list;
            }
            if (newAlert.risk_score > 0.7) {
              setFlashScreen(true);
              setTimeout(() => setFlashScreen(false), 900);
              if (soundEnabledRef.current) {
                playAlertSound();
              }
            }
            return [newAlert, ...list];
          });
        } catch (messageError) {
          console.error('WebSocket parse error:', messageError);
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        isConnectingRef.current = false;
        setWsStatus('DISCONNECTED');
        reconnectTimeout = setTimeout(connectWS, 3000);
      };

      ws.onerror = () => {
        isConnectingRef.current = false;
      };
    };

    connectWS();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [token, selectedTenantId, selectedStoreId, selectedCameraId, scopeOptions.tenants, scopeOptions.stores]);

  const alertsList = Array.isArray(alerts) ? alerts : [];

  const filteredAlerts = alertsList.filter((alert) => {
    const searchText = `${alert.camera_id} ${(alert.rules_triggered || []).join(' ')}`.toLowerCase();
    const matchesSearch = searchText.includes(searchTerm.toLowerCase());
    const matchesRisk =
      selectedRiskFilter === 'ALL' ||
      (selectedRiskFilter === 'CRITICAL' && alert.risk_score > 0.7) ||
      (selectedRiskFilter === 'WARNING' && alert.risk_score > 0.4 && alert.risk_score <= 0.7) ||
      (selectedRiskFilter === 'LOW' && alert.risk_score <= 0.4);

    return matchesSearch && matchesRisk;
  });

  const criticalAlerts = alertsList.filter((alert) => alert.risk_score > 0.7);
  const warningAlerts = alertsList.filter((alert) => alert.risk_score > 0.4 && alert.risk_score <= 0.7);
  const cameraOptions = scopeOptions.cameras.map((camera) => ({
    value: camera.camera_id,
    label: camera.display_name || camera.camera_id,
  }));

  const formatTimestamp = (isoString) => {
    try {
      return new Date(isoString).toLocaleString('es-BO');
    } catch {
      return isoString;
    }
  };

  return (
    <div className={`transition-colors duration-300 rounded-2xl ${flashScreen ? 'bg-red-950/40 p-4 border border-red-500' : ''}`}>
      {flashScreen && (
        <div className="bg-red-600 text-white text-center py-2 font-bold animate-pulse uppercase tracking-widest flex items-center justify-center gap-2 text-sm z-50 fixed top-0 left-0 w-full shadow-lg">
          <ShieldAlert className="w-5 h-5 animate-bounce" />
          Alerta critica en tiempo real
          <ShieldAlert className="w-5 h-5 animate-bounce" />
        </div>
      )}

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
            Seguridad
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
            Analitica
          </button>
          <button
            onClick={() => setActiveTab('reports')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs uppercase tracking-wider font-bold transition-all cursor-pointer ${
              activeTab === 'reports'
                ? 'bg-purple-950/40 border-purple-500 text-purple-400'
                : 'bg-transparent border-transparent text-gray-400 hover:text-white'
            }`}
          >
            <BarChart2 className="w-4 h-4" />
            Reportes
          </button>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-gray-800/80 px-3 py-1.5 rounded-lg border border-gray-700/50">
            <span className={`h-2.5 w-2.5 rounded-full ${wsStatus === 'CONNECTED' ? 'bg-green-500 animate-pulse' : wsStatus === 'CONNECTING' ? 'bg-yellow-500 animate-bounce' : 'bg-red-500'}`} />
            <span className="text-[10px] font-mono font-bold text-gray-300">WS: {wsStatus}</span>
          </div>
          <button
            onClick={() => setSoundEnabled((previous) => !previous)}
            className={`p-2 rounded-lg border transition-all duration-200 ${soundEnabled ? 'bg-red-950/40 border-red-500/50 text-red-400' : 'bg-gray-800/80 border-gray-700 text-gray-400 hover:text-white'}`}
          >
            {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
          <button
            onClick={fetchAlerts}
            className="flex items-center gap-1.5 px-3 py-2 bg-gray-800/80 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Sincronizar
          </button>
        </div>
      </div>

      <section className="bg-[#0f1524]/40 border border-gray-800/80 rounded-xl p-4 mb-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-300">Contexto operativo</p>
            <p className="mt-1 text-xs text-slate-400">
              {canFilterTenants
                ? 'Acceso global con segmentacion por tenant, tienda y camara.'
                : 'Vista acotada por tu alcance, con filtros adicionales de tienda y camara.'}
            </p>
          </div>

          <div className={`grid w-full gap-3 ${canFilterTenants ? 'md:grid-cols-3' : 'md:grid-cols-2'} xl:w-auto`}>
            {canFilterTenants && (
              <label className="block">
                <span className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                  <Building2 className="h-3.5 w-3.5" />
                  Tenant
                </span>
                <select
                  value={selectedTenantId}
                  onChange={(event) => setSelectedTenantId(event.target.value)}
                  className="w-full rounded-lg border border-gray-700 bg-[#0a0f1d] px-3 py-2 text-xs text-gray-200"
                >
                  <option value="ALL">Todos los tenants</option>
                  {scopeOptions.tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                <Store className="h-3.5 w-3.5" />
                Tienda
              </span>
              <select
                value={selectedStoreId}
                onChange={(event) => setSelectedStoreId(event.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-[#0a0f1d] px-3 py-2 text-xs text-gray-200"
              >
                <option value="ALL">Todas las tiendas</option>
                {scopeOptions.stores.map((storeOption) => (
                  <option key={storeOption.id} value={storeOption.id}>
                    {storeOption.tenant_name ? `${storeOption.tenant_name} / ${storeOption.name}` : storeOption.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                <Camera className="h-3.5 w-3.5" />
                Camara
              </span>
              <select
                value={selectedCameraId}
                onChange={(event) => setSelectedCameraId(event.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-[#0a0f1d] px-3 py-2 text-xs text-gray-200"
              >
                <option value="ALL">Todas las camaras</option>
                {cameraOptions.map((camera) => (
                  <option key={camera.value} value={camera.value}>
                    {camera.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </section>

      {error && (
        <div className="mb-6 p-4 bg-red-950/30 border border-red-900/50 rounded-xl flex items-start gap-3 text-red-300">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-semibold">Error de conexion</p>
            <p className="text-red-400 mt-1">{error}</p>
          </div>
        </div>
      )}

      {activeTab === 'analytics' ? (
        <AnalyticsPanel
          token={token}
          selectedTenantId={selectedTenantId}
          selectedStoreId={selectedStoreId}
          selectedCameraId={selectedCameraId}
          latestTelemetry={latestTelemetry}
          latestHeatmap={latestHeatmap}
        />
      ) : activeTab === 'reports' ? (
        <ReportsPanel
          token={token}
          selectedTenantId={selectedTenantId}
          selectedStoreId={selectedStoreId}
          selectedCameraId={selectedCameraId}
        />
      ) : (
        <>
          <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4">
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Alertas Activas</p>
              <h3 className="text-2xl font-black text-white mt-1 font-mono">{alertsList.length}</h3>
              <span className="text-[9px] text-gray-500">Usuario: {profile?.username}</span>
            </div>
            <div className="border rounded-xl p-4 bg-red-950/20 border-red-900/40">
              <p className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Casos Criticos</p>
              <h3 className="text-2xl font-black text-red-500 mt-1 font-mono">{criticalAlerts.length}</h3>
              <span className="text-[9px] text-red-400/80">Riesgo mayor a 70%</span>
            </div>
            <div className="border rounded-xl p-4 bg-amber-950/10 border-amber-900/30">
              <p className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Sospechosos</p>
              <h3 className="text-2xl font-black text-amber-400 mt-1 font-mono">{warningAlerts.length}</h3>
              <span className="text-[9px] text-amber-400/80">Riesgo entre 40% y 70%</span>
            </div>
          </section>

          <section className="bg-[#0f1524]/40 border border-gray-800/80 rounded-xl p-4 mb-6 flex flex-col lg:flex-row gap-4 items-center justify-between">
            <div className="relative w-full lg:w-80">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Buscar por regla o camara..."
                className="w-full bg-[#0a0f1d] border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto text-xs">
              <select
                value={selectedRiskFilter}
                onChange={(event) => setSelectedRiskFilter(event.target.value)}
                className="bg-gray-900/60 p-2 rounded-lg border border-gray-800 text-gray-300"
              >
                <option value="ALL">Todos los riesgos</option>
                <option value="CRITICAL">Critico</option>
                <option value="WARNING">Warning</option>
                <option value="LOW">Bajo</option>
              </select>

              <select
                value={selectedCameraId}
                onChange={(event) => setSelectedCameraId(event.target.value)}
                className="bg-gray-900/60 p-2 rounded-lg border border-gray-800 text-gray-300"
              >
                <option value="ALL">Todas las camaras</option>
                {cameraOptions.map((camera) => (
                  <option key={camera.value} value={camera.value}>
                    {camera.label}
                  </option>
                ))}
              </select>
            </div>
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7 flex flex-col gap-3">
              <div className="flex flex-col gap-3 max-h-[500px] overflow-y-auto pr-1">
                {filteredAlerts.length === 0 ? (
                  <div className="bg-[#0f1524]/30 border border-gray-800 rounded-xl p-12 text-center">
                    <ShieldCheck className="w-10 h-10 text-gray-600 mb-2 mx-auto" />
                    <p className="text-xs font-semibold text-gray-400">Sin alertas visibles para este usuario.</p>
                  </div>
                ) : (
                  filteredAlerts.map((alert) => {
                    const isCritical = alert.risk_score > 0.7;
                    return (
                      <button
                        type="button"
                        key={alert.id}
                        onClick={() => setSelectedAlert(alert)}
                        className={`text-left rounded-xl border p-4 shadow-sm transition-all duration-200 ${
                          selectedAlert?.id === alert.id
                            ? 'bg-slate-900 border-cyan-500'
                            : isCritical
                              ? 'bg-red-950/10 border-red-900/60 hover:border-red-500'
                              : 'bg-[#0f1524]/60 border-gray-800 hover:border-gray-700'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex flex-wrap items-center gap-2 text-[10px]">
                              <span className="flex items-center gap-1 text-gray-300 bg-gray-800 px-2 py-0.5 rounded font-mono font-semibold">
                                <Camera className="w-3 h-3 text-indigo-400" />
                                {alert.camera_display_name || alert.camera_id}
                              </span>
                              {alert.zona && (
                                <span className="flex items-center gap-1 text-purple-200 bg-purple-900/30 border border-purple-500/30 px-2 py-0.5 rounded font-mono font-bold animate-pulse">
                                  📍 {alert.zona}
                                </span>
                              )}
                              {alert.tenant_name && (
                                <span className="text-gray-400 font-mono">{alert.tenant_name}</span>
                              )}
                              {alert.store_name && (
                                <span className="text-gray-500 font-mono">/ {alert.store_name}</span>
                              )}
                              <span className="flex items-center gap-1 text-gray-400 font-mono">
                                <Clock className="w-3 h-3" />
                                {formatTimestamp(alert.timestamp)}
                              </span>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-1">
                              {(alert.rules_triggered || []).map((rule) => (
                                <span key={`${alert.id}-${rule}`} className="text-[9px] px-2 py-0.5 rounded-full font-medium bg-gray-800 text-gray-300 border border-gray-700">
                                  {rule}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="text-[9px] text-gray-500 font-bold uppercase">Score</span>
                            <div className={`text-lg font-black font-mono leading-none ${isCritical ? 'text-red-500' : 'text-amber-400'}`}>
                              {Math.round(alert.risk_score * 100)}%
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="flex justify-between items-center bg-[#0f1524]/60 border border-gray-800 p-3 rounded-xl text-xs">
                  <button
                    disabled={alertsPage <= 1}
                    onClick={() => setAlertsPage(prev => Math.max(1, prev - 1))}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white rounded-lg cursor-pointer"
                  >
                    Anterior
                  </button>
                  <span className="text-gray-400 font-mono">
                    Página {alertsPage} de {totalPages}
                  </span>
                  <button
                    disabled={alertsPage >= totalPages}
                    onClick={() => setAlertsPage(prev => Math.min(totalPages, prev + 1))}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white rounded-lg cursor-pointer"
                  >
                    Siguiente
                  </button>
                </div>
              )}
            </div>

            <div className="lg:col-span-5">
              {!selectedAlert ? (
                <div className="bg-[#0f1524]/40 border border-gray-800 rounded-2xl p-8 text-center min-h-[350px] flex flex-col items-center justify-center">
                  <Video className="w-12 h-12 text-gray-700 mb-2 animate-pulse" />
                  <p className="text-xs font-semibold text-gray-400">Selecciona una alerta</p>
                </div>
              ) : (
                <div className="bg-[#0f1524]/85 border border-gray-800 rounded-2xl p-4 flex flex-col gap-4 shadow-lg">
                  <div className="flex justify-between items-center pb-2 border-b border-gray-800/80">
                    <div>
                      <h4 className="font-extrabold text-white text-xs font-mono">CAMARA: {selectedAlert.camera_display_name || selectedAlert.camera_id}</h4>
                      {selectedAlert.zona && (
                        <p className="text-[10px] text-purple-300 font-bold mt-1 font-mono">📍 ZONA: {selectedAlert.zona}</p>
                      )}
                      <p className="text-[9px] text-gray-400 mt-0.5 font-mono">Alert ID: #{selectedAlert.id}</p>
                    </div>
                    <div className="px-2 py-0.5 rounded text-[10px] font-black font-mono bg-red-950/60 border border-red-500/30 text-red-500">
                      {Math.round(selectedAlert.risk_score * 100)}% RIESGO
                    </div>
                  </div>

                  <div className="relative aspect-video bg-black rounded-lg border border-gray-800 overflow-hidden flex items-center justify-center">
                    {selectedAlert.video_path && (selectedAlert.video_path.startsWith('http://') || selectedAlert.video_path.startsWith('https://')) ? (
                      <video
                        src={selectedAlert.video_path}
                        controls
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="z-20 text-center flex flex-col items-center">
                        <div className="bg-[#0b0f19]/80 border border-gray-700/40 p-3 rounded-lg max-w-[220px] text-[10px]">
                          <Video className="w-5 h-5 text-cyan-400 mx-auto mb-1" />
                          <p className="font-semibold text-gray-200">Clip en Nodo Local</p>
                          <p className="text-[9px] text-gray-400 font-mono truncate">{selectedAlert.video_path || 'Sin video registrado'}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="bg-[#0a0f1d] border border-gray-800/80 rounded-xl p-3 flex flex-col gap-2.5 text-[11px]">
                    <div className="grid grid-cols-2 gap-2 text-gray-400">
                      <div>
                        <span>Fecha</span>
                        <span className="font-mono text-gray-200 block mt-0.5">{formatTimestamp(selectedAlert.timestamp)}</span>
                      </div>
                      <div>
                        <span>Video</span>
                        <span className="font-mono text-gray-200 block mt-0.5 truncate">{selectedAlert.video_path || 'N/A'}</span>
                      </div>
                    </div>
                    <div className="flex gap-2 pt-2 border-t border-gray-800/80">
                      <button
                        type="button"
                        onClick={() => {
                          if (selectedAlert.video_path && (selectedAlert.video_path.startsWith('http://') || selectedAlert.video_path.startsWith('https://'))) {
                            window.open(selectedAlert.video_path, '_blank');
                          } else {
                            window.alert(`Reproduciendo clip local: ${selectedAlert.video_path || 'No disponible'}`);
                          }
                        }}
                        className="flex-1 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-bold text-[10px] flex items-center justify-center gap-1 cursor-pointer"
                      >
                        <Play className="w-3 h-3 fill-white" /> Reproducir Clip
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
