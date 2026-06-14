import React, { useState } from 'react';
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, 
  CartesianGrid, Tooltip, Legend 
} from 'recharts';
import { 
  TrendingUp, Users, ArrowUpRight, ArrowDownRight, 
  Clock, Store, Percent, RefreshCw 
} from 'lucide-react';

// Mock commercial data representing traffic from 9:00 AM to 9:00 PM
const initialData = [
  { time: '09:00', entrantes: 12, salientes: 4 },
  { time: '10:00', entrantes: 24, salientes: 10 },
  { time: '11:00', entrantes: 35, salientes: 22 },
  { time: '12:00', entrantes: 62, salientes: 45 },
  { time: '13:00', entrantes: 50, salientes: 52 },
  { time: '14:00', entrantes: 38, salientes: 30 },
  { time: '15:00', entrantes: 45, salientes: 36 },
  { time: '16:00', entrantes: 58, salientes: 42 },
  { time: '17:00', entrantes: 80, salientes: 60 },
  { time: '18:00', entrantes: 95, salientes: 78 },
  { time: '19:00', entrantes: 70, salientes: 85 },
  { time: '20:00', entrantes: 42, salientes: 64 },
  { time: '21:00', entrantes: 15, salientes: 35 },
];

export default function AnalyticsPanel() {
  const [data, setData] = useState(initialData);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Compute metrics
  const totalEntrantes = data.reduce((acc, curr) => acc + curr.entrantes, 0);
  const totalSalientes = data.reduce((acc, curr) => acc + curr.salientes, 0);
  const currentOccupancy = Math.max(0, totalEntrantes - totalSalientes);
  
  // Calculate average ticket conversion rate mockup
  const conversionRate = 32.4; 

  const handleSimulateUpdate = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      // Simulate random fluctuations in recent hours
      const updatedData = data.map((item, idx) => {
        if (idx >= data.length - 3) {
          const deltaIn = Math.floor(Math.random() * 10) - 5;
          const deltaOut = Math.floor(Math.random() * 10) - 5;
          return {
            ...item,
            entrantes: Math.max(5, item.entrantes + deltaIn),
            salientes: Math.max(2, item.salientes + deltaOut)
          };
        }
        return item;
      });
      setData(updatedData);
      setIsRefreshing(false);
    }, 800);
  };

  return (
    <div className="bg-[#0f1524]/60 border border-gray-800 rounded-2xl p-6 shadow-lg flex flex-col gap-6 w-full relative overflow-hidden backdrop-blur-md">
      
      {/* Decorative gradient overlay */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
      
      {/* Panel Header */}
      <div className="flex justify-between items-center pb-4 border-b border-gray-800/80">
        <div className="flex items-center gap-2.5">
          <div className="bg-indigo-600/10 p-2 rounded-xl border border-indigo-500/20 text-indigo-400">
            <Store className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white leading-tight">Analítica Comercial</h2>
            <p className="text-xs text-gray-400 mt-0.5">Métricas de Afluencia y Ocupación en Tiempo Real</p>
          </div>
        </div>

        <button
          onClick={handleSimulateUpdate}
          className="p-1.5 hover:bg-gray-800 text-gray-400 hover:text-white border border-gray-800 hover:border-gray-700 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          Simular
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* KPI 1: Accum. Traffic */}
        <div className="bg-[#070b14]/50 border border-gray-800/50 p-4 rounded-xl relative overflow-hidden group">
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Afluencia Total</p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-black text-white font-mono">{totalEntrantes}</span>
            <span className="text-[10px] text-green-400 flex items-center gap-0.5 font-medium">
              <ArrowUpRight className="w-3 h-3" /> +12.4%
            </span>
          </div>
          <span className="text-[9px] text-gray-500 block mt-1">Personas registradas hoy</span>
        </div>

        {/* KPI 2: Current Occupancy */}
        <div className="bg-[#070b14]/50 border border-gray-800/50 p-4 rounded-xl relative overflow-hidden group">
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Ocupación Actual</p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-black text-cyan-400 font-mono">{currentOccupancy}</span>
            <span className="text-[9px] text-cyan-400 animate-pulse px-1.5 py-0.5 bg-cyan-950/40 rounded border border-cyan-800/30">
              Activo
            </span>
          </div>
          <span className="text-[9px] text-gray-500 block mt-1">Dentro del establecimiento</span>
        </div>

        {/* KPI 3: Conversion Rate */}
        <div className="bg-[#070b14]/50 border border-gray-800/50 p-4 rounded-xl relative overflow-hidden group">
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Tasa de Conversión</p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-black text-indigo-400 font-mono">{conversionRate}%</span>
            <span className="text-[10px] text-indigo-400 flex items-center gap-0.5 font-medium">
              <Percent className="w-3 h-3" />
            </span>
          </div>
          <span className="text-[9px] text-gray-500 block mt-1">Estimación de ventas</span>
        </div>

        {/* KPI 4: Peak Hours */}
        <div className="bg-[#070b14]/50 border border-gray-800/50 p-4 rounded-xl relative overflow-hidden group">
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Hora Pico</p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl font-black text-white font-mono">18:00</span>
            <Clock className="w-4 h-4 text-gray-500 shrink-0" />
          </div>
          <span className="text-[9px] text-gray-500 block mt-1">Mayor tráfico registrado</span>
        </div>

      </div>

      {/* Main Charts Area */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs text-gray-400 px-1 mb-2">
          <span className="font-semibold flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-indigo-400" />
            Curva de Tráfico Horario
          </span>
          <span className="text-[10px] text-gray-500 font-mono">Datos actualizados</span>
        </div>

        <div className="h-64 w-full bg-[#070b14]/30 border border-gray-800/40 rounded-xl p-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorIn" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0}/>
                </linearGradient>
                <linearGradient id="colorOut" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="#6b7280" 
                fontSize={10} 
                tickLine={false}
              />
              <YAxis 
                stroke="#6b7280" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false} 
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#0a0f1d', 
                  borderColor: '#1f2937',
                  borderRadius: '10px',
                  color: '#fff',
                  fontSize: '11px',
                  fontFamily: 'monospace'
                }} 
              />
              <Legend 
                verticalAlign="top" 
                height={36} 
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: '10px', color: '#9ca3af' }}
              />
              <Area 
                type="monotone" 
                name="Entrantes"
                dataKey="entrantes" 
                stroke="#6366f1" 
                strokeWidth={2}
                fillOpacity={1} 
                fill="url(#colorIn)" 
              />
              <Area 
                type="monotone" 
                name="Salientes"
                dataKey="salientes" 
                stroke="#14b8a6" 
                strokeWidth={2}
                fillOpacity={1} 
                fill="url(#colorOut)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* Footer statistics */}
      <div className="flex items-center justify-between text-[10px] text-gray-500 bg-[#070b14]/30 rounded-lg p-3 border border-gray-800/40">
        <div className="flex items-center gap-1">
          <Users className="w-3.5 h-3.5 text-indigo-400" />
          <span>Total Acumulado Hoy: <strong className="text-gray-300 font-mono">{totalEntrantes + totalSalientes}</strong> interacciones</span>
        </div>
        <span>Cámara ID principal: <strong className="text-gray-400 font-mono">CAM-01</strong></span>
      </div>

    </div>
  );
}
