import React, { useState } from 'react';

export default function CustomZonesEditor({ value, onChange, snapshotUrl }) {
  const width = 640;
  const height = 360;
  
  const zones = Array.isArray(value) ? value : [];
  
  const [currentZoneName, setCurrentZoneName] = useState('');
  const [currentPoints, setCurrentPoints] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');

  const handleCanvasClick = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    // Normalizar coordenadas a float [0.0, 1.0] con 4 decimales de precisión
    const x = parseFloat(((event.clientX - rect.left) / rect.width).toFixed(4));
    const y = parseFloat(((event.clientY - rect.top) / rect.height).toFixed(4));
    
    setCurrentPoints((prev) => [...prev, [x, y]]);
  };

  const handleSaveZone = () => {
    if (!currentZoneName.trim()) {
      setErrorMsg('Debes asignar un nombre al sector.');
      return;
    }
    if (currentPoints.length < 3) {
      setErrorMsg('Un sector debe tener al menos 3 puntos (polígono).');
      return;
    }

    const newZone = {
      name: currentZoneName.trim(),
      polygon: currentPoints,
    };

    const nextZones = [...zones, newZone];
    onChange(nextZones);

    // Reset current drawing state
    setCurrentZoneName('');
    setCurrentPoints([]);
    setErrorMsg('');
  };

  const handleDeleteZone = (indexToDelete) => {
    const nextZones = zones.filter((_, idx) => idx !== indexToDelete);
    onChange(nextZones);
  };

  const handleUndoPoint = () => {
    setCurrentPoints((prev) => prev.slice(0, -1));
  };

  const handleClearCurrent = () => {
    setCurrentPoints([]);
    setErrorMsg('');
  };

  // Convert normalized points back to SVG coordinates
  const getPointsAttr = (polygon) => {
    return polygon.map(([x, y]) => `${x * width},${y * height}`).join(' ');
  };

  // Harmonious Tailwind-like colors for zones
  const zoneColors = [
    { border: '#ec4899', fill: 'rgba(236,72,153,0.15)', text: 'text-pink-400' }, // Pink
    { border: '#a855f7', fill: 'rgba(168,85,247,0.15)', text: 'text-purple-400' }, // Purple
    { border: '#10b981', fill: 'rgba(16,185,129,0.15)', text: 'text-emerald-400' }, // Emerald
    { border: '#3b82f6', fill: 'rgba(59,130,246,0.15)', text: 'text-blue-400' }, // Blue
    { border: '#f59e0b', fill: 'rgba(245,158,11,0.15)', text: 'text-amber-400' }, // Amber
  ];

  return (
    <div className="mt-2 rounded-2xl border border-white/10 bg-[#0a1220] p-4 space-y-4">
      <div>
        <p className="text-[11px] text-slate-400">Dibuja múltiples sectores (ej. Lácteos, Panadería) sobre la cámara feed.</p>
      </div>

      {/* Lista de sectores existentes */}
      {zones.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold text-slate-300">Sectores Guardados ({zones.length}):</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {zones.map((zone, idx) => {
              const color = zoneColors[idx % zoneColors.length];
              return (
                <div key={idx} className="flex items-center justify-between rounded-xl border border-white/5 bg-white/5 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color.border }} />
                    <span className="text-xs font-semibold text-white">{zone.name}</span>
                    <span className="text-[10px] text-slate-400">({zone.polygon.length} pts)</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteZone(idx)}
                    className="text-[10px] font-bold text-red-400 transition hover:text-red-300"
                  >
                    Eliminar
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Editor SVG */}
      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-auto w-full cursor-crosshair rounded-xl border border-white/10 bg-[linear-gradient(0deg,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:32px_32px]"
          onClick={handleCanvasClick}
        >
          {snapshotUrl && (
            <image href={snapshotUrl} x="0" y="0" width={width} height={height} preserveAspectRatio="none" opacity="0.9" />
          )}

          {/* Renderizar zonas guardadas */}
          {zones.map((zone, idx) => {
            const color = zoneColors[idx % zoneColors.length];
            return (
              <g key={idx}>
                <polygon
                  points={getPointsAttr(zone.polygon)}
                  fill={color.fill}
                  stroke={color.border}
                  strokeWidth="2"
                />
                {zone.polygon.length > 0 && (
                  <text
                    x={zone.polygon[0][0] * width + 5}
                    y={zone.polygon[0][1] * height - 5}
                    fill={color.border}
                    fontSize="11"
                    fontWeight="bold"
                  >
                    {zone.name}
                  </text>
                )}
              </g>
            );
          })}

          {/* Renderizar zona activa en progreso de dibujo */}
          {currentPoints.length >= 2 && (
            <polyline
              points={currentPoints.map(([x, y]) => `${x * width},${y * height}`).join(' ')}
              fill={currentPoints.length >= 3 ? 'rgba(6,182,212,0.2)' : 'none'}
              stroke="#22d3ee"
              strokeWidth="2"
              strokeDasharray="4"
            />
          )}

          {/* Marcadores para puntos de la zona activa */}
          {currentPoints.map(([x, y], index) => (
            <g key={`cur-${index}`}>
              <circle cx={x * width} cy={y * height} r="4" fill="#06b6d4" />
              <text x={x * width + 6} y={y * height - 6} fill="#22d3ee" fontSize="10" fontWeight="bold">
                {index + 1}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* Inputs para nueva zona */}
      <div className="flex flex-col gap-3 rounded-xl border border-white/5 bg-[#08101c] p-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="text"
            placeholder="Nombre del nuevo sector (ej. Lácteos)"
            value={currentZoneName}
            onChange={(e) => setCurrentZoneName(e.target.value)}
            className="flex-1 rounded-xl border border-white/10 bg-[#060c16] px-3 py-2 text-xs text-white placeholder-slate-500 outline-none transition focus:border-cyan-500"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleUndoPoint}
              disabled={currentPoints.length === 0}
              className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-white/10 disabled:opacity-50"
            >
              Deshacer
            </button>
            <button
              type="button"
              onClick={handleClearCurrent}
              disabled={currentPoints.length === 0}
              className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-white/10 disabled:opacity-50"
            >
              Limpiar
            </button>
          </div>
        </div>

        {errorMsg && (
          <p className="text-xs font-semibold text-red-400">{errorMsg}</p>
        )}

        <button
          type="button"
          onClick={handleSaveZone}
          disabled={!currentZoneName.trim() || currentPoints.length < 3}
          className="w-full rounded-xl bg-cyan-500 py-2.5 text-xs font-black uppercase tracking-[0.16em] text-slate-950 transition hover:bg-cyan-400 disabled:bg-slate-700 disabled:text-slate-400"
        >
          Guardar Sector en la Cámara
        </button>
      </div>
    </div>
  );
}
