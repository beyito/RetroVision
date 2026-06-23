import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Users, Clock, TrendingUp, TrendingDown, ShoppingBag, 
  AlertCircle, MapPin, RefreshCw, BarChart3, Users2
} from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, 
  CartesianGrid, Legend, ScatterChart, Scatter, ZAxis
} from 'recharts';
import { API_BASE_URL } from './config';

export default function AnalyticsPanel({
  token,
  selectedTenantId,
  selectedStoreId,
  selectedCameraId,
  latestTelemetry,
  latestHeatmap
}) {
  const [telemetry, setTelemetry] = useState([]);
  const [heatmaps, setHeatmaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchData = async () => {
    if (!token) return;
    try {
      const params = new URLSearchParams();
      if (selectedTenantId && selectedTenantId !== 'ALL') {
        params.set('tenant', selectedTenantId);
      }
      if (selectedStoreId && selectedStoreId !== 'ALL') {
        params.set('store', selectedStoreId);
      }
      if (selectedCameraId && selectedCameraId !== 'ALL') {
        params.set('camera_id', selectedCameraId);
      }
      const query = params.toString() ? `?${params.toString()}` : '';

      // Fetch both telemetry and heatmap data
      const [telemetryRes, heatmapsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/telemetry/${query}`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE_URL}/api/heatmaps/${query}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      setTelemetry(telemetryRes.data);
      setHeatmaps(heatmapsRes.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching analytics data:", err);
      setError("No se pudieron cargar los datos analíticos desde la API central.");
    } finally {
      setLoading(false);
      setLastUpdated(new Date());
    }
  };

  useEffect(() => {
    fetchData();
  }, [token, selectedTenantId, selectedStoreId, selectedCameraId]);

  // Reactive WebSocket telemetry update listener
  useEffect(() => {
    if (!latestTelemetry) return;

    setTelemetry((prev) => {
      // Prevent duplicate records for the same camera at the same timestamp
      if (prev.some((item) => item.timestamp === latestTelemetry.timestamp && item.camera_id === latestTelemetry.camera_id)) {
        return prev;
      }
      return [latestTelemetry, ...prev].slice(0, 100);
    });
    setLastUpdated(new Date());
  }, [latestTelemetry]);

  // Reactive WebSocket heatmap update listener
  useEffect(() => {
    if (!latestHeatmap) return;

    setHeatmaps((prev) => {
      // Prevent duplicate records for the same camera at the same timestamp
      if (prev.some((item) => item.timestamp === latestHeatmap.timestamp && item.camera_id === latestHeatmap.camera_id)) {
        return prev;
      }
      return [latestHeatmap, ...prev].slice(0, 50);
    });
  }, [latestHeatmap]);

  // Derived metrics
  const latest = telemetry.length > 0 ? telemetry[0] : null;
  const totalIn = latest ? latest.personas_entrantes : 0;
  const totalOut = latest ? latest.personas_salientes : 0;
  
  // Historical average wait time
  const avgWait = telemetry.length > 0 
    ? (telemetry.reduce((sum, item) => sum + item.tiempo_espera_promedio, 0) / telemetry.length).toFixed(1) 
    : '0.0';

  // Current queue status
  const currentQueue = latest ? latest.personas_en_cola : 0;
  const queueAvgWait = latest ? latest.tiempo_espera_promedio.toFixed(1) : '0.0';

  // Process sectors (zones)
  const sectors = latest && typeof latest.sectores === 'object' && latest.sectores ? latest.sectores : {};
  const sectorEntries = Object.entries(sectors);
  
  // Calculate total people in all sectors
  const totalPeopleInSectors = sectorEntries.reduce((sum, [_, val]) => sum + (Number(val) || 0), 0);
  
  // Find busiest sector
  let busiestSectorName = 'Ninguno';
  let maxSectorPeople = 0;
  sectorEntries.forEach(([name, count]) => {
    const val = Number(count) || 0;
    if (val > maxSectorPeople) {
      maxSectorPeople = val;
      busiestSectorName = name;
    }
  });

  // Format line chart data (chronological order)
  const chartData = [...telemetry].reverse().map(item => ({
    time: new Date(item.timestamp).toLocaleTimeString('es-BO', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }),
    entrantes: item.personas_entrantes,
    salientes: item.personas_salientes,
    en_cola: item.personas_en_cola,
  }));

  // Flatten coordinates from all heatmap historical records
  const heatmapPoints = [];
  heatmaps.forEach(record => {
    if (record.coordenadas_json && Array.isArray(record.coordenadas_json.points)) {
      record.coordenadas_json.points.forEach(pt => {
        if (Array.isArray(pt) && pt.length >= 2) {
          heatmapPoints.push({ x: pt[0], y: pt[1], z: 1 });
        }
      });
    }
  });

  // Scale down coordinate points if resolution is too high
  const displayPoints = heatmapPoints.slice(-150); // Show last 150 points for clarity

  // Determine queue status style
  const getQueueStatus = (count) => {
    if (count === 0) return { label: 'Despejado', color: 'text-green-400 bg-green-950/20 border-green-500/30', desc: 'Sin clientes en cola de espera.' };
    if (count <= 2) return { label: 'Moderado', color: 'text-amber-400 bg-amber-950/20 border-amber-500/30', desc: 'Operación fluida en zona de cajas.' };
    return { label: 'Congestión', color: 'text-red-400 bg-red-950/30 border-red-500/40 animate-pulse', desc: 'Alta afluencia de espera detectada.' };
  };

  const queueStatus = getQueueStatus(currentQueue);

  return (
    <div className="flex flex-col gap-6">
      
      {/* Top Controls/Sync Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 bg-[#0f1524]/40 border border-gray-800 p-3 rounded-xl">
        <div className="text-[11px] text-gray-400 font-mono">
          Última actualización: <span className="text-cyan-400">{lastUpdated.toLocaleTimeString('es-BO')}</span>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-950/40 hover:bg-indigo-900/60 border border-indigo-500/40 rounded-lg text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          Sincronizar Datos
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-950/20 border border-red-900/40 text-red-400 text-xs rounded-xl flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
          {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* KPI 1: Ingresos */}
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-cyan-500" />
          <div>
            <p className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Ingresos de Clientes</p>
            <h3 className="text-2xl font-black text-white mt-1 font-mono">{totalIn}</h3>
            <span className="text-[9px] text-gray-500">Total acumulado hoy</span>
          </div>
          <div className="p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-lg text-cyan-400">
            <Users className="w-6 h-6" />
          </div>
        </div>

        {/* KPI 2: Salidas */}
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-fuchsia-500" />
          <div>
            <p className="text-[10px] font-bold text-fuchsia-400 uppercase tracking-wider">Salidas de Clientes</p>
            <h3 className="text-2xl font-black text-white mt-1 font-mono">{totalOut}</h3>
            <span className="text-[9px] text-gray-500">Total egresados hoy</span>
          </div>
          <div className="p-3 bg-fuchsia-950/20 border border-fuchsia-500/20 rounded-lg text-fuchsia-400">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>

        {/* KPI 3: Espera Promedio */}
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-amber-500" />
          <div>
            <p className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Tiempo Promedio de Espera</p>
            <h3 className="text-2xl font-black text-white mt-1 font-mono">{avgWait}s</h3>
            <span className="text-[9px] text-gray-500">Historial medio en cajas</span>
          </div>
          <div className="p-3 bg-amber-950/20 border border-amber-500/20 rounded-lg text-amber-400">
            <Clock className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Charts & Visuals Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Line Chart Inflow vs Outflow (7 cols) */}
        <div className="lg:col-span-7 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Historial de Flujo Comercial</h4>
          </div>
          
          <div className="h-[280px] w-full text-[10px]">
            {chartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 italic">
                Esperando datos de telemetría del nodo Edge...
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" vertical={false} />
                  <XAxis dataKey="time" stroke="#6b7280" />
                  <YAxis stroke="#6b7280" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                    labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                  />
                  <Legend iconType="circle" />
                  <Line 
                    type="monotone" 
                    dataKey="entrantes" 
                    name="Ingresos" 
                    stroke="#06b6d4" 
                    strokeWidth={2.5} 
                    dot={false}
                    activeDot={{ r: 6 }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="salientes" 
                    name="Egresos" 
                    stroke="#ec4899" 
                    strokeWidth={2.5} 
                    dot={false}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Queue/Cajas Monitor Panel (5 cols) */}
        <div className="lg:col-span-5 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4 justify-between">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <ShoppingBag className="w-4 h-4 text-indigo-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Estado de Cola y Cajas</h4>
            </div>
            <span className={`px-2 py-0.5 rounded text-[9px] font-black border uppercase ${queueStatus.color}`}>
              {queueStatus.label}
            </span>
          </div>

          {/* Queue visualizer box */}
          <div className="bg-[#070b13] border border-gray-800 rounded-xl p-4 flex flex-col items-center justify-center gap-4 py-8">
            <div className="flex items-center gap-2">
              {currentQueue === 0 ? (
                <Users2 className="w-12 h-12 text-gray-700 opacity-40" />
              ) : (
                <div className="flex flex-wrap justify-center gap-2.5 max-w-[180px]">
                  {Array.from({ length: Math.min(currentQueue, 10) }).map((_, i) => (
                    <div 
                      key={i} 
                      className={`p-1.5 rounded-full border ${
                        currentQueue >= 3 
                          ? 'bg-red-950/40 border-red-500/40 text-red-400' 
                          : 'bg-indigo-950/40 border-indigo-500/40 text-indigo-400'
                      }`}
                    >
                      <Users className="w-5 h-5" />
                    </div>
                  ))}
                  {currentQueue > 10 && (
                    <div className="text-xs font-bold text-red-500 flex items-center px-1 font-mono">
                      +{currentQueue - 10}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="text-center">
              <h3 className="text-3xl font-black text-white font-mono">{currentQueue}</h3>
              <p className="text-[10px] text-gray-400 font-semibold uppercase mt-0.5">Personas en Cola</p>
            </div>
          </div>

          {/* Details row */}
          <div className="bg-[#0a0f1d] border border-gray-800/80 rounded-xl p-3 flex flex-col gap-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-gray-400">Espera de la Cola Actual:</span>
              <span className="font-bold text-white font-mono">{queueAvgWait}s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Diagnóstico:</span>
              <span className="text-gray-300 font-medium text-right max-w-[160px] truncate" title={queueStatus.desc}>
                {queueStatus.desc}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Grid: Custom Sectors (Zonas) & Spatial Density Heatmap */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Monitoreo de Sectores (Zonas) (6 cols) */}
        <div className="lg:col-span-6 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4 justify-between">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-purple-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Monitoreo de Sectores (Zonas)</h4>
            </div>
            <span className="px-2 py-0.5 rounded text-[9px] font-black border uppercase bg-purple-950/20 border-purple-500/30 text-purple-300">
              {sectorEntries.length} Zonas Activas
            </span>
          </div>

          {/* Sectors List / Grid */}
          <div className="flex-1 flex flex-col justify-center min-h-[180px]">
            {sectorEntries.length === 0 ? (
              <div className="text-gray-500 italic text-[11px] text-center p-4 border border-dashed border-gray-800 rounded-xl bg-[#070b13]">
                No hay sectores de tránsito activos en esta cámara.
                <p className="mt-1 text-[9px] text-gray-600">Dibuja zonas poligonales en la sección de Administración para medir la afluencia por área.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {sectorEntries.map(([name, val], idx) => {
                  const count = Number(val) || 0;
                  const borderColors = ['border-pink-500/40', 'border-purple-500/40', 'border-emerald-500/40', 'border-blue-500/40', 'border-amber-500/40'];
                  const bgColors = ['bg-pink-500/5', 'bg-purple-500/5', 'bg-emerald-500/5', 'bg-blue-500/5', 'bg-amber-500/5'];
                  const textColors = ['text-pink-400', 'text-purple-400', 'text-emerald-400', 'text-blue-400', 'text-amber-400'];
                  const cIdx = idx % borderColors.length;

                  return (
                    <div 
                      key={name}
                      className={`flex flex-col justify-between p-3 rounded-xl border ${borderColors[cIdx]} ${bgColors[cIdx]}`}
                    >
                      <div>
                        <span className="text-[9px] font-bold text-gray-500 uppercase">Sector</span>
                        <h5 className="font-extrabold text-white text-xs truncate mt-0.5">{name}</h5>
                      </div>
                      <div className="mt-2 flex items-baseline gap-1">
                        <span className={`text-xl font-black font-mono ${textColors[cIdx]}`}>{count}</span>
                        <span className="text-[9px] text-gray-400 font-semibold uppercase">{count === 1 ? 'persona' : 'personas'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Sector metrics info */}
          <div className="bg-[#0a0f1d] border border-gray-800/80 rounded-xl p-3 flex flex-col gap-2 text-[11px] mt-2">
            <div className="flex justify-between">
              <span className="text-gray-400">Personas Totales en Sectores:</span>
              <span className="font-bold text-white font-mono">{totalPeopleInSectors}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Sector más Concurrido:</span>
              <span className="font-bold text-cyan-400 font-mono">
                {busiestSectorName} {maxSectorPeople > 0 ? `(${maxSectorPeople} pers.)` : ''}
              </span>
            </div>
          </div>
        </div>

        {/* Spatial Density Heatmap Coordinates Panel (6 cols) */}
        <div className="lg:col-span-6 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Densidad Espacial de Tránsito</h4>
          </div>
          
          <div className="relative aspect-[1.8/1] min-h-[220px] bg-black/60 border border-gray-800 rounded-xl overflow-hidden flex items-center justify-center">
            <div className="absolute inset-0 pointer-events-none z-10 flex flex-col justify-between p-3">
              <span className="bg-cyan-500/90 text-[#070b13] font-mono text-[8px] px-1.5 py-0.5 rounded font-black uppercase self-start">
                VISTA EN PLANTA
              </span>
              <span className="bg-black/75 text-[8px] font-mono text-gray-400 px-2 py-1 rounded border border-gray-800/60 self-end">
                Concentración espacial de tránsitos
              </span>
            </div>

            {displayPoints.length === 0 ? (
              <div className="text-gray-500 italic text-[11px] z-20">
                Esperando coordenadas del seguidor espacial...
              </div>
            ) : (
              <div className="w-full h-full p-2">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid stroke="#1f2937/30" />
                    <XAxis type="number" dataKey="x" domain={[0, 1280]} hide />
                    <YAxis type="number" dataKey="y" domain={[0, 720]} hide reversed />
                    <ZAxis type="number" dataKey="z" range={[8, 12]} />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} hide />
                    <Scatter 
                      name="Hotspots" 
                      data={displayPoints} 
                      fill="#3b82f6" 
                      line={false} 
                      shape={(props) => {
                        const { cx, cy } = props;
                        return (
                          <g>
                            <circle cx={cx} cy={cy} r={6} fill="#ef4444" fillOpacity={0.4} />
                            <circle cx={cx} cy={cy} r={3} fill="#fbbf24" />
                          </g>
                        );
                      }}
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
