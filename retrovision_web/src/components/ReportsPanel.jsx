import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Users, Clock, Calendar, BarChart3, TrendingUp, MapPin, 
  RefreshCw, AlertTriangle, AlertCircle, ShoppingBag,
  Sparkles, Brain, Download

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

  // AI report states
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiFormat, setAiFormat] = useState('json');
  const [aiModel, setAiModel] = useState('gemini-3.1-flash-lite-preview');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiProgressText, setAiProgressText] = useState('');
  const [aiReportResult, setAiReportResult] = useState(null);
  const [aiError, setAiError] = useState(null);

  const handleGenerateAiReport = async (forcedFormat = null) => {
    if (!aiPrompt.trim()) return;

    const formatToUse = forcedFormat || aiFormat;
    setAiLoading(true);
    setAiError(null);
    if (formatToUse === 'json') {
      setAiReportResult(null);
    }

    const progressSteps = [
      "Analizando tu consulta en lenguaje natural...",
      "Consultando la base de datos de RetroVision...",
      "Compilando métricas y redactando el informe analítico..."
    ];

    let stepIdx = 0;
    setAiProgressText(progressSteps[0]);
    const progressInterval = setInterval(() => {
      if (stepIdx < progressSteps.length - 1) {
        stepIdx++;
        setAiProgressText(progressSteps[stepIdx]);
      }
    }, 2000);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/reports/dynamic/`,
        {
          prompt: aiPrompt,
          format: formatToUse,
          model: aiModel
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: formatToUse === 'json' ? 'json' : 'blob'
        }
      );

      clearInterval(progressInterval);

      if (formatToUse === 'json') {
        setAiReportResult(response.data);
      } else {
        const blob = new Blob([response.data], { type: response.headers['content-type'] });
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        const filename = `reporte_retrovision_${new Date().toISOString().slice(0, 10)}.${formatToUse === 'pdf' ? 'pdf' : 'xlsx'}`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(link.href);
      }
    } catch (err) {
      clearInterval(progressInterval);
      console.error("Error generating AI report:", err);
      if (formatToUse !== 'json' && err.response && err.response.data) {
        try {
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const errObj = JSON.parse(reader.result);
              setAiError(errObj.error || "Ocurrió un error al generar el reporte con IA.");
            } catch {
              setAiError("Ocurrió un error al generar el reporte con IA.");
            }
          };
          reader.readAsText(err.response.data);
        } catch {
          setAiError("Ocurrió un error al generar el reporte con IA.");
        }
      } else {
        setAiError(err.response?.data?.error || "No se pudo conectar con el servicio de IA o la API Key no es válida.");
      }
    } finally {
      setAiLoading(false);
    }
  };

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

  const [viewMode, setViewMode] = useState('historical'); // 'historical' or 'predictive'
  const [predictiveCameraId, setPredictiveCameraId] = useState('camara_local');
  const [predictiveData, setPredictiveData] = useState(null);
  const [predictiveLoading, setPredictiveLoading] = useState(false);
  const [predictiveError, setPredictiveError] = useState(null);

  const fetchPredictiveData = async () => {
    if (!token) return;
    setPredictiveLoading(true);
    setPredictiveError(null);
    try {
      let activeCam = predictiveCameraId;
      if (!activeCam || activeCam === 'ALL') {
        activeCam = 'camara_local';
      }
      const response = await axios.get(`${API_BASE_URL}/api/telemetry/predictive/?camera_id=${activeCam}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPredictiveData(response.data.predictions);
    } catch (err) {
      console.error("Error fetching predictions:", err);
      setPredictiveError(err.response?.data?.error || "No se pudieron cargar las predicciones de Machine Learning. Asegúrate de que los modelos estén entrenados en el servidor.");
    } finally {
      setPredictiveLoading(false);
    }
  };

  useEffect(() => {
    fetchHistoricalData();
  }, [token, timeRange, selectedTenantId, selectedStoreId, selectedCameraId]);

  useEffect(() => {
    if (viewMode === 'predictive') {
      fetchPredictiveData();
    }
  }, [token, viewMode, predictiveCameraId]);


  const renderHeader = () => (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#0f1524]/60 border border-gray-800 p-5 rounded-2xl relative overflow-hidden">
      <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-purple-500 to-cyan-500" />
      <div>
        <h2 className="text-lg font-black text-white uppercase tracking-wider flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-cyan-400" />
          Módulo de Reportes & Analítica
        </h2>
        <p className="text-xs text-gray-400">Analiza datos históricos del negocio y consulta predicciones inteligentes con ML.</p>
      </div>
      
      <div className="inline-flex rounded-xl border border-gray-800 bg-[#0a0f1d] p-1 shrink-0 self-stretch md:self-auto justify-center">
        <button
          onClick={() => setViewMode('historical')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
            viewMode === 'historical'
              ? 'bg-gradient-to-r from-cyan-500/20 to-purple-500/20 border border-cyan-500/50 text-white font-extrabold shadow-lg shadow-cyan-500/5'
              : 'border border-transparent text-gray-400 hover:text-white bg-transparent'
          }`}
        >
          <Calendar className="w-4 h-4 text-cyan-400" />
          Histórico
        </button>
        <button
          onClick={() => setViewMode('predictive')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
            viewMode === 'predictive'
              ? 'bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/50 text-white font-extrabold shadow-lg shadow-purple-500/5'
              : 'border border-transparent text-gray-400 hover:text-white bg-transparent'
          }`}
        >
          <Brain className="w-4 h-4 text-purple-400 animate-pulse" />
          🔮 Predictivo (ML)
        </button>
      </div>
    </div>
  );

  if (loading && !data && viewMode === 'historical') {
    return (
      <div className="flex flex-col gap-6 animate-fade-in">
        {renderHeader()}
        <div className="flex flex-col items-center justify-center p-12 bg-[#0f1524]/60 border border-gray-800 rounded-2xl min-h-[400px]">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mb-4" />
          <p className="text-xs text-gray-400">Compilando datos históricos de la tienda...</p>
        </div>
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

  const queuePieData = [
    { name: 'Saturado', value: Math.round(queue.saturation_percentage) },
    { name: 'Despejado', value: Math.max(0, 100 - Math.round(queue.saturation_percentage)) }
  ];
  const COLORS = ['#ef4444', '#10b981']; // Red vs Green

  // Security metrics formatting
  const securityAlertsCount = data?.security_metrics?.total_alerts ?? 0;
  const securityDailyData = data?.security_metrics?.alerts_by_day ?? [];
  const securityRuleData = data?.security_metrics?.rule_breakdown
    ? Object.entries(data.security_metrics.rule_breakdown).map(([name, count]) => ({
        name,
        value: count
      })).sort((a, b) => b.value - a.value)
    : [];

  if (viewMode === 'predictive') {
    // Calculate summary metrics from predictions
    let peakInflowHour = 'N/A';
    let maxPredictedInflow = 0;
    let peakWaitHour = 'N/A';
    let maxPredictedWait = 0;
    let maxQueueLen = 0;
    let maxRiskProb = 0;
    let riskHour = 'N/A';
    
    if (predictiveData && predictiveData.length > 0) {
      predictiveData.forEach(item => {
        if (item.predicted_inflow > maxPredictedInflow) {
          maxPredictedInflow = item.predicted_inflow;
          peakInflowHour = item.hour;
        }
        if (item.predicted_wait_seconds > maxPredictedWait) {
          maxPredictedWait = item.predicted_wait_seconds;
          peakWaitHour = item.hour;
          maxQueueLen = item.predicted_queue;
        }
        if (item.alert_probability > maxRiskProb) {
          maxRiskProb = item.alert_probability;
          riskHour = item.hour;
        }
      });
    }

    const get15MinsPrior = (timeStr) => {
      if (!timeStr || timeStr === 'N/A') return '15 minutos antes';
      const [hStr, mStr] = timeStr.split(':');
      let hr = parseInt(hStr);
      let min = parseInt(mStr);
      min -= 15;
      if (min < 0) {
        min += 60;
        hr -= 1;
        if (hr < 0) hr += 24;
      }
      return `${String(hr).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
    };
    const actionTime = get15MinsPrior(peakWaitHour);

    // Formulate recommendations
    const recommendations = [];
    if (maxPredictedWait >= 30.0 || maxQueueLen >= 2) {
      recommendations.push({
        type: 'queue',
        icon: <Clock className="w-4 h-4 text-amber-400" />,
        text: `[Reventamiento de Colas] Abrir caja auxiliar a las ${actionTime} para mitigar la congestión proyectada de ${maxQueueLen} personas en cola a las ${peakWaitHour}.`
      });
    }
    if (maxPredictedInflow >= 10.0) {
      const zoneName = predictiveCameraId === 'camara_entrada' ? 'Acceso Principal' : 
                       predictiveCameraId === 'camara_carnes' ? 'Fiambrería y Carnes' : 
                       predictiveCameraId === 'camara_lacteos' ? 'Lácteos y Bebidas' : 'Salón Principal';
      recommendations.push({
        type: 'staff',
        icon: <Users className="w-4 h-4 text-cyan-400" />,
        text: `[Distribución de Personal] Reforzar personal de atención y góndola en la zona de ${zoneName} cerca de las ${peakInflowHour} para asimilar el flujo máximo proyectado de ${maxPredictedInflow.toFixed(1)} shoppers/hora.`
      });
    }
    if (maxRiskProb >= 0.50) {
      recommendations.push({
        type: 'security',
        icon: <AlertTriangle className="w-4 h-4 text-red-400 animate-pulse" />,
        text: `[Seguridad Proactiva] Incrementar rondas de guardias en el sector a las ${riskHour} debido a probabilidad elevada de alerta/anomalía (${Math.round(maxRiskProb * 100)}%).`
      });
    }
    if (recommendations.length === 0) {
      recommendations.push({
        type: 'normal',
        icon: <Users className="w-4 h-4 text-emerald-400" />,
        text: "[Operación Normal] Flujos estables proyectados para las próximas 12 horas. Se sugiere mantener operación estándar."
      });
    }

    return (
      <div className="flex flex-col gap-6 animate-fade-in">
        {renderHeader()}
        
        {/* Predictor Selector bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#0f1524]/60 border border-gray-800 p-4 rounded-xl">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400 animate-pulse" />
            <div>
              <h4 className="text-sm font-bold text-white uppercase tracking-wider">Pronóstico de Operaciones (Siguientes 12 Horas)</h4>
              <p className="text-[10px] text-gray-500 font-mono">
                Modelo: <span className="text-purple-400 font-bold">RandomForestRegressor / Classifier Autoregresivo</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="flex flex-col gap-0.5 w-full sm:w-auto">
              <span className="text-[9px] font-bold text-gray-500 uppercase">Sector / Área a Analizar</span>
              <select
                value={predictiveCameraId}
                onChange={(e) => setPredictiveCameraId(e.target.value)}
                disabled={predictiveLoading}
                className="bg-[#0a0f1d] border border-gray-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500/50 cursor-pointer font-bold w-full sm:w-48"
              >
                <option value="camara_entrada">Acceso Principal</option>
                <option value="camara_local">Salón Principal & Cajas</option>
                <option value="camara_carnes">Fiambrería y Carnes</option>
                <option value="camara_lacteos">Lácteos y Bebidas</option>
              </select>
            </div>
            <button
              onClick={fetchPredictiveData}
              disabled={predictiveLoading}
              className="flex items-center gap-1.5 px-3 py-2 bg-gray-800/80 hover:bg-gray-700 border border-gray-700 rounded-lg text-xs font-medium transition-colors cursor-pointer self-end"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${predictiveLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {predictiveError && (
          <div className="p-4 bg-red-950/20 border border-red-900/40 text-red-400 text-xs rounded-xl flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              <span className="font-bold">Error en predicción</span>
            </div>
            <p>{predictiveError}</p>
          </div>
        )}

        {predictiveLoading && !predictiveData && (
          <div className="flex flex-col items-center justify-center p-12 bg-[#0f1524]/40 border border-gray-800 rounded-xl min-h-[300px]">
            <RefreshCw className="w-6 h-6 text-purple-400 animate-spin mb-3" />
            <p className="text-xs text-gray-400">Calculando modelos predictivos...</p>
          </div>
        )}

        {predictiveData && (
          <>
            {/* Predictive KPIs and Recommendations */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Executive metrics (5 cols) */}
              <div className="lg:col-span-5 grid grid-cols-1 gap-4">
                <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-purple-500" />
                  <div>
                    <p className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Afluencia Máxima Proyectada</p>
                    <h3 className="text-2xl font-black text-white mt-1 font-mono">{maxPredictedInflow.toFixed(1)} <span className="text-xs font-normal text-gray-400">vis./h</span></h3>
                    <span className="text-[9px] text-gray-500">Pico estimado a las {peakInflowHour}</span>
                  </div>
                  <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-lg text-purple-400">
                    <Users className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-amber-500" />
                  <div>
                    <p className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Máxima Espera Proyectada</p>
                    <h3 className="text-2xl font-black text-white mt-1 font-mono">{maxPredictedWait.toFixed(0)}s</h3>
                    <span className="text-[9px] text-gray-500">Pico de {maxQueueLen} personas a las {peakWaitHour}</span>
                  </div>
                  <div className="p-3 bg-amber-950/20 border border-amber-500/20 rounded-lg text-amber-400">
                    <Clock className="w-6 h-6" />
                  </div>
                </div>

                <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-rose-500" />
                  <div>
                    <p className="text-[10px] font-bold text-rose-400 uppercase tracking-wider">Riesgo Máximo de Anomalías</p>
                    <h3 className="text-2xl font-black text-white mt-1 font-mono">{Math.round(maxRiskProb * 100)}%</h3>
                    <span className="text-[9px] text-gray-500">Mayor vulnerabilidad a las {riskHour}</span>
                  </div>
                  <div className="p-3 bg-rose-950/20 border border-rose-500/20 rounded-lg text-rose-400">
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                </div>
              </div>

              {/* Proactive Recommendations Panel (7 cols) */}
              <div className="lg:col-span-7 bg-[#0f1524]/80 border border-gray-800 p-5 rounded-2xl flex flex-col gap-4 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/5 blur-[80px] rounded-full pointer-events-none" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Brain className="w-4 h-4 text-purple-400" />
                  Plan de Acción Proactivo Recomendado (ML)
                </h4>
                <p className="text-[10px] text-gray-400 font-semibold">Basado en el análisis predictivo de las variables de tráfico, colas y alertas de seguridad para las siguientes 12 horas.</p>

                <div className="flex flex-col gap-3 mt-1">
                  {recommendations.map((rec, idx) => (
                    <div key={idx} className="flex gap-3 items-start p-3 rounded-xl bg-[#0a0f1d]/60 border border-gray-800 hover:border-gray-700 transition-colors">
                      <div className="p-1.5 rounded-lg bg-gray-900 border border-gray-800 shrink-0">
                        {rec.icon}
                      </div>
                      <span className="text-xs text-gray-300 leading-relaxed font-mono">{rec.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Predictive Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Traffic inflow forecast (6 cols) */}
              <div className="lg:col-span-6 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-purple-400" />
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Afluencia Proyectada (Siguientes 12h)</h4>
                </div>

                <div className="h-[240px] w-full text-[10px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={predictiveData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorPredInflow" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#a855f7" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" vertical={false} />
                      <XAxis dataKey="hour" stroke="#6b7280" />
                      <YAxis stroke="#6b7280" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                        labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                      />
                      <Area type="monotone" dataKey="predicted_inflow" name="Ingresos Proyectados" stroke="#a855f7" strokeWidth={2.5} fillOpacity={1} fill="url(#colorPredInflow)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Wait time forecast (6 cols) */}
              <div className="lg:col-span-6 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-400" />
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Espera Promedio en Cajas Proyectada (Siguientes 12h)</h4>
                </div>

                <div className="h-[240px] w-full text-[10px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={predictiveData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" vertical={false} />
                      <XAxis dataKey="hour" stroke="#6b7280" />
                      <YAxis stroke="#6b7280" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                        labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                      />
                      <Bar dataKey="predicted_wait_seconds" name="Espera Estimada (seg)">
                        {predictiveData.map((entry, index) => {
                          const val = entry.predicted_wait_seconds;
                          const color = val >= 45 ? '#ef4444' : val >= 20 ? '#f59e0b' : '#10b981';
                          return <Cell key={`cell-${index}`} fill={color} />;
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

            </div>

            {/* Risk probability forecast (full width) */}
            <div className="bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 animate-pulse" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Probabilidad Proyectada de Anomalía/Amenaza de Seguridad (Siguientes 12h)</h4>
              </div>

              <div className="h-[200px] w-full text-[10px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart 
                    data={predictiveData.map(d => ({ ...d, alert_prob_percent: Math.round(d.alert_probability * 100) }))} 
                    margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorPredRisk" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" vertical={false} />
                    <XAxis dataKey="hour" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" unit="%" domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                      labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                    />
                    <Area type="monotone" dataKey="alert_prob_percent" name="Probabilidad de Anomalía" stroke="#f43f5e" strokeWidth={2.5} fillOpacity={1} fill="url(#colorPredRisk)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {renderHeader()}

      
      {/* AI Dynamic Reports Section */}
      <div className="bg-[#0f1524]/80 border border-gray-800 rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 blur-[80px] rounded-full pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/5 blur-[80px] rounded-full pointer-events-none" />

        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-purple-500/20 to-cyan-500/20 border border-purple-500/30 rounded-lg text-cyan-400">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white uppercase tracking-wider">Asistente de Reportes con IA (Gemini)</h4>
            <p className="text-[10px] text-gray-400">Describe en lenguaje natural qué quieres saber y el formato que deseas exportar</p>
          </div>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); handleGenerateAiReport(); }} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <textarea
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="Ej: ¿Cuáles fueron las alertas de seguridad más frecuentes la última semana y en qué sectores ocurrieron? O: Resumen de afluencia de personas por hora de ayer."
              rows={3}
              disabled={aiLoading}
              className="w-full bg-[#0a0f1d] border border-gray-800 hover:border-gray-700 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 rounded-xl px-4 py-3 text-xs text-white placeholder-gray-500 focus:outline-none transition-all resize-none font-mono"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex flex-col gap-1">
                <span className="text-[9px] font-bold text-gray-500 uppercase">Modelo de IA</span>
                <select
                  value={aiModel}
                  onChange={(e) => setAiModel(e.target.value)}
                  disabled={aiLoading}
                  className="bg-[#0a0f1d] border border-gray-800 rounded-lg px-2.5 py-1.5 text-[11px] text-white focus:outline-none focus:border-cyan-500/50 cursor-pointer font-semibold"
                >
                  <option value="gemini-3.1-flash-lite-preview">gemini-3.1-flash-lite-preview</option>
                  <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
                  <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                  <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
                  <option value="gemini-flash-latest">gemini-flash-latest</option>
                  <option value="gemini-flash-lite-latest">gemini-flash-lite-latest</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <span className="text-[9px] font-bold text-gray-500 uppercase">Formato de Salida</span>
                <select
                  value={aiFormat}
                  onChange={(e) => setAiFormat(e.target.value)}
                  disabled={aiLoading}
                  className="bg-[#0a0f1d] border border-gray-800 rounded-lg px-2.5 py-1.5 text-[11px] text-white focus:outline-none focus:border-cyan-500/50 cursor-pointer font-semibold"
                >
                  <option value="json">Previsualizar en pantalla</option>
                  <option value="pdf">Documento PDF (.pdf)</option>
                  <option value="excel">Planilla Excel (.xlsx)</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={aiLoading || !aiPrompt.trim()}
              className={`px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider text-slate-950 bg-gradient-to-r from-purple-400 to-cyan-400 hover:from-purple-300 hover:to-cyan-300 cursor-pointer shadow-lg shadow-cyan-500/10 transition-all flex items-center gap-2 ${
                (aiLoading || !aiPrompt.trim()) ? 'opacity-50 cursor-not-allowed filter grayscale' : ''
              }`}
            >
              {aiLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Generando...
                </>
              ) : (
                <>
                  <Brain className="w-3.5 h-3.5" />
                  Generar Reporte
                </>
              )}
            </button>
          </div>
        </form>

        {/* Loading Progress State */}
        {aiLoading && (
          <div className="flex flex-col gap-2 mt-2 p-4 bg-[#0a0f1d] border border-gray-800/80 rounded-xl items-center text-center animate-pulse">
            <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin mb-1" />
            <p className="text-xs font-medium text-white">{aiProgressText}</p>
            <span className="text-[9px] text-gray-500">Procesando y agregando datos de RetroVision en la nube...</span>
          </div>
        )}

        {/* AI Error Alert */}
        {aiError && (
          <div className="p-4 bg-red-950/20 border border-red-900/40 text-red-400 text-xs rounded-xl flex items-center gap-2 mt-2">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
            {aiError}
          </div>
        )}

        {/* Dynamic Screen Preview */}
        {aiReportResult && aiFormat === 'json' && (
          <div className="flex flex-col gap-4 mt-2 p-5 bg-[#0a0f1d] border border-cyan-500/20 rounded-xl relative animate-fade-in">
            <div className="flex justify-between items-start gap-4">
              <div>
                <span className="px-2 py-0.5 rounded text-[8px] font-black tracking-widest uppercase border bg-cyan-950/20 border-cyan-500/30 text-cyan-400 font-mono">
                  Reporte Generado por IA
                </span>
                <h3 className="text-base font-black text-white mt-1.5 uppercase tracking-wide">
                  {aiReportResult.title}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleGenerateAiReport('pdf')}
                  className="flex items-center gap-1 px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-[10px] text-white transition-colors cursor-pointer"
                >
                  <Download className="w-3 h-3 text-red-400" />
                  PDF
                </button>
                <button
                  type="button"
                  onClick={() => handleGenerateAiReport('excel')}
                  className="flex items-center gap-1 px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-[10px] text-white transition-colors cursor-pointer"
                >
                  <Download className="w-3 h-3 text-emerald-400" />
                  Excel
                </button>
              </div>
            </div>

            {/* Executive Summary Block */}
            <div className="border-l-4 border-purple-500 pl-4 py-2 text-xs text-gray-300 italic bg-[#0f1524]/40 pr-3 rounded-r-lg">
              {aiReportResult.executive_summary}
            </div>

            {/* KPIs Grid */}
            {aiReportResult.kpis && aiReportResult.kpis.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {aiReportResult.kpis.map((kpi, idx) => (
                  <div key={idx} className="bg-[#0f1524]/60 border border-gray-800/80 p-3 rounded-lg flex flex-col gap-0.5">
                    <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">{kpi.label}</span>
                    <span className="text-sm font-black text-white font-mono">{kpi.value}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Detailed Table */}
            {aiReportResult.table && aiReportResult.table.headers && aiReportResult.table.headers.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Datos Detallados</span>
                <div className="overflow-x-auto border border-gray-800/80 rounded-lg">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-[#0f1524] border-b border-gray-800 text-gray-400 font-bold">
                        {aiReportResult.table.headers.map((hdr, idx) => (
                          <th key={idx} className="px-3 py-2 text-[10px] uppercase tracking-wider">{hdr}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {aiReportResult.table.rows && aiReportResult.table.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="border-b border-gray-800/40 hover:bg-[#0f1524]/30 text-gray-300">
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="px-3 py-2 font-mono text-[10px]">{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Recommendations */}
            {aiReportResult.recommendations && aiReportResult.recommendations.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Recomendaciones Sugeridas</span>
                <ul className="flex flex-col gap-1 text-[11px] text-gray-400 pl-1 list-none">
                  {aiReportResult.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex gap-2 items-start">
                      <span className="text-cyan-400 mt-0.5">✔</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

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
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
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

        {/* Security alerts (NEW) */}
        <div className="bg-[#0f1524]/60 border border-gray-800 rounded-xl p-4 relative overflow-hidden flex items-center justify-between">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-red-500" />
          <div>
            <p className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Alertas Emitidas</p>
            <h3 className="text-2xl font-black text-white mt-1 font-mono">{securityAlertsCount}</h3>
            <span className="text-[9px] text-gray-500">Total anomalías detectadas</span>
          </div>
          <div className="p-3 bg-red-950/20 border border-red-500/20 rounded-lg text-red-400">
            <AlertTriangle className="w-6 h-6" />
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

      {/* Security Alerts Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Weekly Alerts Distribution (7 columns) */}
        <div className="lg:col-span-7 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Distribución Semanal de Alertas</h4>
          </div>
          
          <div className="h-[240px] w-full text-[10px]">
            {securityDailyData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 italic">
                Sin alertas registradas en este período.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={securityDailyData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" vertical={false} />
                  <XAxis dataKey="day" stroke="#6b7280" />
                  <YAxis stroke="#6b7280" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                    labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="alerts" name="Total Alertas" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Alerts Breakdown by Rule (5 columns) */}
        <div className="lg:col-span-5 bg-[#0f1524]/80 border border-gray-800 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-red-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider m-0">Anomalías por Regla Disparada</h4>
          </div>

          <div className="h-[240px] w-full text-[10px]">
            {securityRuleData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 italic">
                Sin anomalías de seguridad registradas.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={securityRuleData} layout="vertical" margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937/40" horizontal={false} />
                  <XAxis type="number" stroke="#6b7280" />
                  <YAxis dataKey="name" type="category" stroke="#6b7280" width={110} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0a0f1d', border: '1px solid #374151', borderRadius: '8px' }}
                    labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="value" name="Cantidad" fill="#f87171" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
