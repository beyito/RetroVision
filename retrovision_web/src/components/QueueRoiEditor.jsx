import React, { useEffect, useState } from 'react';


export default function QueueRoiEditor({ value, onChange, snapshotUrl }) {
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
    const x = Math.round(((event.clientX - rect.left) / rect.width) * 1280);
    const y = Math.round(((event.clientY - rect.top) / rect.height) * 720);
    emitChange([...points, [x, y]]);
  };

  const removeLast = () => emitChange(points.slice(0, -1));
  const clearAll = () => emitChange([]);

  const pointsAttr = points
    .map(([x, y]) => `${(x / 1280) * width},${(y / 720) * height}`)
    .join(' ');

  return (
    <div className="mt-2 rounded-2xl border border-white/10 bg-[#0a1220] p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="text-[11px] text-slate-400">Canvas 1280x720 para dibujar la zona de cola.</p>
        <div className="flex gap-2">
          <button type="button" onClick={removeLast} className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-slate-200">
            Deshacer
          </button>
          <button type="button" onClick={clearAll} className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-slate-200">
            Limpiar
          </button>
        </div>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full cursor-crosshair rounded-xl border border-cyan-500/20 bg-[linear-gradient(0deg,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:32px_32px]"
        onClick={handleCanvasClick}
      >
        {snapshotUrl && (
          <image href={snapshotUrl} x="0" y="0" width={width} height={height} preserveAspectRatio="none" opacity="0.92" />
        )}
        {points.length >= 2 && (
          <polyline
            points={pointsAttr}
            fill={points.length >= 3 ? 'rgba(6,182,212,0.15)' : 'none'}
            stroke="#22d3ee"
            strokeWidth="2"
          />
        )}
        {points.map(([x, y], index) => (
          <g key={`${x}-${y}-${index}`}>
            <circle cx={(x / 1280) * width} cy={(y / 720) * height} r="5" fill="#f59e0b" />
            <text x={(x / 1280) * width + 8} y={(y / 720) * height - 8} fill="#fff" fontSize="12">
              {index + 1}
            </text>
          </g>
        ))}
      </svg>
      <textarea
        value={JSON.stringify(points)}
        onChange={(event) => {
          try {
            const nextValue = JSON.parse(event.target.value);
            emitChange(Array.isArray(nextValue) ? nextValue : []);
          } catch {
            return;
          }
        }}
        className="mt-3 h-24 w-full rounded-xl border border-white/10 bg-[#08101c] px-3 py-2 font-mono text-xs text-slate-200 outline-none"
      />
    </div>
  );
}
