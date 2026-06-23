import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Users, Clock, Calendar, BarChart3, TrendingUp, MapPin, 
  RefreshCw, AlertTriangle, AlertCircle, ShoppingBag
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, 
  CartesianGrid, Legend, LineChart, Line, AreaChart, Area, Cell, PieChart, Pie
} from 'recharts';
import { API_BASE_URL } from '../config';

export default function ReportsPanel({ token, selectedTenantId, selectedStoreId, selectedCameraId }) {
  const [timeRange, setTimeRange] = useState('7days');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchHistoricalData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('range', timeRange);
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

      const response = await axios.get(`${API_BASE_URL}/api/telemetry/historical/${query}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setData(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching historical reports:", err);
      setError("No se pudieron cargar los reportes históricos desde la API central.");
    } finally {
      setLoading(false);
      setLastUpdated(new Date());
    }
  };

  useEffect(() => {
    fetchHistoricalData();
  }, [token, timeRange, selectedTenantId, selectedStoreId, selectedCameraId]);

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center p-12 min-h-[400px]">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mb-4" />
        <p className="text-xs text-gray-400">Compilando datos históricos de la tienda...</p>
      </div>
    );
  }

  // Fallback defaults if API fails or returns empty
  const analyzedCount = data?.total_records_analyzed ?? 0;
  const totalVisitors = data?.total_visitors_estimated ?? 0;
  const peakHour = data?.peak_hour ?? 'N/A';
  const busiestSector = data?.busiest_sector ?? 'N/A';
  
  const queue = data?.queue_metrics ?? {
    avg_people_in_queue: 0,
    avg_wait_time_seconds: 0,
    max_wait_time_seconds: 0,
    saturation_percentage: 0
  };

  // Convert sectors dictionary to array for charting
  const sectorsData = data?.sectors_metrics 
    ? Object.entries(data.sectors_metrics).map(([name, metrics]) => ({
        name,
        'Promedio': metrics.avg_occupancy,
        'Máximo': metrics.max_occupancy
      }))
    : [];

  const hourlyData = data?.hourly_inflow ?? [];
  const dailyData = data?.daily_inflow ?? [];

  // Pie chart data for queue saturation
  const queuePieData = [
    { name: 'Saturado', value: Math.round(queue.saturation_percentage) },
    { name: 'Despejado', value: Math.max(0, 100 - Math.round(queue.saturation_percentage)) }
  ];
  const COLORS = ['#ef4444', '#10b981']; // Red vs Green

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      
      {/* Selector and Refresh bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#0f1524]/60 border border-gray-800 p-4 rounded-xl">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-cyan-400" />
          <div>
            <h4 className="text-sm font-bold text-white uppercase tracking-wider">Histórico & Análisis de Negocio</h4>
            <p className="text-[10px] text-gray-500 font-mono">
              Registros analizados: <span className="text-gray-300 font-bold">{analyzedCount} muestras</span> | Sincronizado: <span className="text-gray-300 font-bold">{lastUpdated.toLocaleTimeString('es-BO')}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="inline-flex rounded-lg border border-gray-700 bg-[#0a0f1d] p-1">
            <button
              onClick={() => setTimeRange('7days')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                timeRange === '7days'
                  ? 'bg-cyan-500 text-slate-950 shadow'
                  : 'text-gray-400 hover:text-white bg-transparent'
              }`}
            >
              7 Días
            </button>
            <button
              onClick={() => setTimeRange('30days')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                timeRange === '30days'
                  ? 'bg-cyan-500 text-slate-950 shadow'
                  : 'text-gray-400 hover:text-white bg-transparent'
              }`}
            >
              30 Días
            </button>
          </div>
          <button
            onClick={fetchHistoricalData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 bg-gray-800/80 hover:bg-gray-700 border border-gray-700 rounded-lg text-xs font-medium transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/20 border border-red-900/40 text-red-400 text-xs rounded-xl flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
          {error}
        </div>
      )}

      {/* KPI Dashboard Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Visitor estimate */}
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-cyan-500" />
          <div>
            <p className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Afluencia Estimada</p>
            <h3 className="text-2xl font-black text-white mt-1 font-mono">{totalVisitors}</h3>
            <span className="text-[9px] text-gray-500">Visitantes totales detectados</span>
          </div>
          <div className="p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-lg text-cyan-400">
            <Users className="w-6 h-6" />
          </div>
        </div>

        {/* Wait time */}
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-amber-500" />
          <div>
            <p className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Permanencia Media</p>
            <h3 className="text-2xl font-black text-white mt-1 font-mono">{queue.avg_wait_time_seconds.toFixed(1)}s</h3>
            <span className="text-[9px] text-gray-500">Espera en cola (Máx: {queue.max_wait_time_seconds.toFixed(0)}s)</span>
          </div>
          <div className="p-3 bg-amber-950/20 border border-amber-500/20 rounded-lg text-amber-400">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        {/* Traffic peak hour */}
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-emerald-500" />
          <div>
            <p className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Horario Concurrido</p>
            <h3 className="text-2xl font-black text-white mt-1 font-mono">{peakHour}</h3>
            <span className="text-[9px] text-gray-500">Hora con mayor pico de entradas</span>
          </div>
          <div className="p-3 bg-emerald-950/20 border border-emerald-500/20 rounded-lg text-emerald-400">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>

        {/* Hot sector */}
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-purple-500" />
          <div>
            <p className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Sector de Tránsito</p>
            <h3 className="text-2xl font-black text-white mt-1 font-mono capitalize">{busiestSector}</h3>
            <span className="text-[9px] text-gray-500">Área con mayor afluencia media</span>
          </div>
          <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-lg text-purple-400">
            <MapPin className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Aggregated Reports Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Sector average & max occupancy (7 columns) */}
        <div className="lg:col-span-7 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-purple-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Afluencia de Shoppers por Sector</h4>
          </div>
          
          <div className="h-[280px] w-full text-[10px]">
            {sectorsData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 italic">
                Sin datos de sectores registrados en este rango temporal.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sectorsData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" vertical={false} />
                  <XAxis dataKey="name" stroke="#6b7280" />
                  <YAxis stroke="#6b7280" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                    labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                  />
                  <Legend iconType="circle" />
                  <Bar dataKey="Promedio" fill="#a855f7" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Máximo" fill="#ec4899" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Queue Saturation Monitor (5 columns) */}
        <div className="lg:col-span-5 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col justify-between gap-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <ShoppingBag className="w-4 h-4 text-indigo-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Índice de Saturación de Cajas</h4>
            </div>
            <span className="px-2 py-0.5 rounded text-[9px] font-black border bg-indigo-950/20 border-indigo-500/30 text-indigo-300">
              Espera Cola
            </span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-around py-4 gap-4">
            <div className="w-40 h-40 relative flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={queuePieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {queuePieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute text-center">
                <span className="text-2xl font-black font-mono text-white">{Math.round(queue.saturation_percentage)}%</span>
                <p className="text-[8px] text-gray-400 font-bold uppercase tracking-wider mt-0.5">Saturado</p>
              </div>
            </div>

            <div className="flex flex-col gap-2.5 text-xs text-gray-300">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded bg-red-500" />
                <span>Congestionada: <strong className="text-white">{queue.saturation_percentage.toFixed(1)}%</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded bg-emerald-500" />
                <span>Despejada: <strong className="text-white">{(100 - queue.saturation_percentage).toFixed(1)}%</strong></span>
              </div>
              <div className="mt-2 pt-2 border-t border-gray-800 text-[10px] text-gray-400">
                Límite de alerta: <strong>&gt;= 3 personas</strong>
              </div>
            </div>
          </div>

          <div className="bg-[#0a0f1d] border border-gray-800/80 rounded-xl p-3 flex flex-col gap-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-gray-400">Promedio de personas en espera:</span>
              <span className="font-bold text-white font-mono">{queue.avg_people_in_queue.toFixed(1)} pers.</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Tiempo de espera medio:</span>
              <span className="font-bold text-amber-400 font-mono">{queue.avg_wait_time_seconds.toFixed(0)} segundos</span>
            </div>
          </div>
        </div>
      </div>

      {/* Hourly Flow and Weekly shopper trends */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Hourly traffic flow AreaChart (6 cols) */}
        <div className="lg:col-span-6 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Afluencia Horaria (Distribución del Día)</h4>
          </div>

          <div className="h-[240px] w-full text-[10px]">
            {hourlyData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 italic">
                Sin datos de tráfico horario en este rango.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={hourlyData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorInflow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" vertical={false} />
                  <XAxis dataKey="hour" stroke="#6b7280" />
                  <YAxis stroke="#6b7280" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                    labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                  />
                  <Area type="monotone" dataKey="inflow" name="Ingresos" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#colorInflow)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Weekly traffic BarChart (6 cols) */}
        <div className="lg:col-span-6 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Distribución Semanal de Visitas</h4>
          </div>

          <div className="h-[240px] w-full text-[10px]">
            {dailyData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 italic">
                Sin datos semanales acumulados.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dailyData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" vertical={false} />
                  <XAxis dataKey="day" stroke="#6b7280" />
                  <YAxis stroke="#6b7280" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                    labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="inflow" name="Ingresos totales" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
