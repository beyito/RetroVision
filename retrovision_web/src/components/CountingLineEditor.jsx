import React, { useEffect, useState } from 'react';

export default function CountingLineEditor({ value, direction, onChange, onDirectionChange, snapshotUrl }) {
  const width = 640;
  const height = 360;
  const [points, setPoints] = useState(() => (Array.isArray(value) ? value : []));

  useEffect(() => {
    setPoints(Array.isArray(value) ? value : []);
  }, [value]);

  const emitChange = (nextPoints) => {
    setPoints(nextPoints);
    onChange(nextPoints);
  };

  const handleCanvasClick = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    
    // Standardize to 4 decimal floats
    const nx = Math.round(x * 10000) / 10000;
    const ny = Math.round(y * 10000) / 10000;

    if (points.length < 2) {
      emitChange([...points, [nx, ny]]);
    } else {
      // Start a new line
      emitChange([[nx, ny]]);
    }
  };

  const toggleDirection = () => {
    const nextDir = direction === 'forward' ? 'backward' : 'forward';
    onDirectionChange(nextDir);
  };

  const clearAll = () => emitChange([]);

  // Calculate absolute pixel values for display
  const p1 = points[0] ? [points[0][0] * width, points[0][1] * height] : null;
  const p2 = points[1] ? [points[1][0] * width, points[1][1] * height] : null;

  // Calculate normal vector and midpoint for entry direction arrow
  let arrowStart = null;
  let arrowEnd = null;
  if (p1 && p2) {
    const dx = p2[0] - p1[0];
    const dy = p2[1] - p1[1];
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len > 0) {
      const mx = (p1[0] + p2[0]) / 2;
      const my = (p1[1] + p2[1]) / 2;
      arrowStart = [mx, my];

      // Perpendicular vector pointing right (clockwise) relative to P1 -> P2
      let nx = -dy / len;
      let ny = dx / len;

      if (direction === 'backward') {
        nx = -nx;
        ny = -ny;
      }

      // Arrow length of 35px
      arrowEnd = [mx + nx * 35, my + ny * 35];
    }
  }

  return (
    <div className="mt-2 rounded-2xl border border-white/10 bg-[#0a1220] p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wider">Línea Virtual de Conteo</p>
          <p className="text-[10px] text-slate-500">Haz clic en 2 puntos para trazar la línea. El sentido indica Entrada.</p>
        </div>
        <div className="flex gap-2">
          {points.length === 2 && (
            <button
              type="button"
              onClick={toggleDirection}
              className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 text-[10px] text-cyan-300 hover:bg-cyan-500/20 transition cursor-pointer font-bold uppercase tracking-wider"
            >
              🔄 Invertir Sentido
            </button>
          )}
          <button
            type="button"
            onClick={clearAll}
            className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-slate-200 hover:bg-white/10 transition cursor-pointer font-bold uppercase tracking-wider"
          >
            Limpiar
          </button>
        </div>
      </div>

      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-auto w-full cursor-crosshair rounded-xl border border-cyan-500/20 bg-[linear-gradient(0deg,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:32px_32px]"
          onClick={handleCanvasClick}
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="8"
              markerHeight="6"
              refX="6"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#f59e0b" />
            </marker>
          </defs>

          {snapshotUrl && (
            <image href={snapshotUrl} x="0" y="0" width={width} height={height} preserveAspectRatio="none" opacity="0.92" />
          )}

          {/* Draw line */}
          {p1 && p2 && (
            <line
              x1={p1[0]}
              y1={p1[1]}
              x2={p2[0]}
              y2={p2[1]}
              stroke="#22d3ee"
              strokeWidth="3"
              strokeDasharray="4 4"
            />
          )}

          {/* Draw direction arrow */}
          {arrowStart && arrowEnd && (
            <g>
              <line
                x1={arrowStart[0]}
                y1={arrowStart[1]}
                x2={arrowEnd[0]}
                y2={arrowEnd[1]}
                stroke="#f59e0b"
                strokeWidth="3"
                markerEnd="url(#arrowhead)"
              />
              <circle cx={arrowStart[0]} cy={arrowStart[1]} r="3" fill="#f59e0b" />
              <text
                x={arrowEnd[0] + 8}
                y={arrowEnd[1] + 4}
                fill="#f59e0b"
                fontSize="10"
                fontWeight="black"
                className="select-none"
              >
                ENTRADA
              </text>
            </g>
          )}

          {/* Draw markers */}
          {points.map(([x, y], index) => (
            <g key={`${x}-${y}-${index}`}>
              <circle cx={x * width} cy={y * height} r="6" fill="#f59e0b" stroke="#000" strokeWidth="1.5" />
              <text x={x * width + 10} y={y * height - 8} fill="#fff" fontSize="11" fontWeight="bold" className="select-none bg-black/60 rounded px-0.5">
                {index === 0 ? 'P1' : 'P2'}
              </text>
            </g>
          ))}
        </svg>
      </div>

      <div className="mt-3 flex gap-2">
        <div className="w-1/2">
          <p className="text-[10px] text-slate-500 font-bold uppercase">Datos Guardados (Normalizados):</p>
          <code className="mt-1 block w-full rounded-lg bg-[#060a12] border border-white/5 p-2 font-mono text-[10px] text-cyan-200">
            {JSON.stringify(points)}
          </code>
        </div>
        <div className="w-1/2">
          <p className="text-[10px] text-slate-500 font-bold uppercase">Sentido del Cruce:</p>
          <code className="mt-1 block w-full rounded-lg bg-[#060a12] border border-white/5 p-2 font-mono text-[10px] text-amber-400 capitalize">
            {direction}
          </code>
        </div>
      </div>
    </div>
  );
}
