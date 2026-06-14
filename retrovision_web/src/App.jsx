import React from 'react';
import Dashboard from './Dashboard';
import AnalyticsPanel from './AnalyticsPanel';
import { Activity } from 'lucide-react';

function App() {
  return (
    <div className="min-h-screen bg-[#0b0f19] text-gray-100 flex flex-col">
      {/* Brand Header */}
      <header className="border-b border-gray-800/85 bg-[#0f1524]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-4">
        <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-tr from-cyan-500 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-indigo-500/20">
              <Activity className="w-6 h-6 text-white animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent m-0 flex items-center">
                RetroVision 
                <span className="text-cyan-400 font-mono text-[10px] border border-cyan-400/30 px-2 py-0.5 rounded-full ml-2">CORE PLATFORM</span>
              </h1>
              <p className="text-[10px] text-gray-400 mt-0.5">Sistema Distribuido de Videovigilancia y Analítica IA de Tiendas</p>
            </div>
          </div>
          <div className="text-xs text-gray-500 font-mono">
            Feria Tecnológica • Versión 1.2.0
          </div>
        </div>
      </header>

      {/* Main Content Layout - Side-by-Side Grid */}
      <main className="max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1">
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
          
          {/* Dashboard (Alerts & Inspector) - Left Column taking 8/12 cols */}
          <div className="xl:col-span-8 w-full">
            <Dashboard />
          </div>

          {/* Analytics Panel - Right Column taking 4/12 cols */}
          <div className="xl:col-span-4 w-full">
            <AnalyticsPanel />
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 bg-[#0f1524]/40 py-6 text-center text-xs text-gray-500">
        <p>RetroVision Security Systems © 2026. Proyecto Diseñado para la Feria Tecnológica.</p>
        <p className="mt-1 font-mono text-[9px]">Edge + Central Server + Real-time WebSockets & Analytics</p>
      </footer>
    </div>
  );
}

export default App;
