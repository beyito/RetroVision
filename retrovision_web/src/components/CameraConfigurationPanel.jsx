import React, { useState } from 'react';

import QueueRoiEditor from './QueueRoiEditor';


function InputField({ field, value, onChange }) {
  return (
    <div>
      <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
        {field.label}
      </label>
      {field.type === 'select' ? (
        <select
          value={value ?? ''}
          onChange={(event) => onChange(field.name, event.target.value)}
          className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
        >
          <option value="">Selecciona</option>
          {field.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          type={field.type || 'text'}
          value={value ?? ''}
          onChange={(event) => onChange(field.name, event.target.value)}
          placeholder={field.placeholder}
          className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
        />
      )}
    </div>
  );
}


export default function CameraConfigurationPanel({
  title,
  subtitle,
  items,
  columns,
  formState,
  onChange,
  onSubmit,
  onSelectItem,
  selectedItemKey,
  onReset,
  onDelete,
  isEditing,
  snapshotUrl,
  generalFields,
  roiFields,
}) {
  const [activeTab, setActiveTab] = useState('general');

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
      <section className="rounded-[28px] border border-white/10 bg-[#0f1524]/80 p-6">
        <h3 className="text-lg font-black text-white">{title}</h3>
        <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        <div className="mt-6 overflow-hidden rounded-2xl border border-white/8">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-slate-400">
              <tr>
                {columns.map((column) => (
                  <th key={column.key} className="px-4 py-3 font-semibold uppercase tracking-[0.16em] text-[11px]">
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-6 text-center text-slate-500">
                    No hay cámaras visibles para este usuario.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr
                    key={item.camera_id}
                    className={`border-t border-white/6 text-slate-200 cursor-pointer transition ${
                      selectedItemKey === item.camera_id ? 'bg-cyan-500/10' : 'hover:bg-white/5'
                    }`}
                    onClick={() => onSelectItem(item)}
                  >
                    {columns.map((column) => (
                      <td key={column.key} className="px-4 py-3 align-top">
                        {column.render ? column.render(item) : item[column.key] ?? '-'}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-[28px] border border-white/10 bg-[#121b2f]/80 p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-black text-white">{isEditing ? `Configurar ${formState.camera_id || 'camara'}` : 'Crear nueva camara'}</h3>
            <p className="mt-1 text-sm text-slate-400">Separa configuracion general y configuracion espacial de colas.</p>
          </div>
          {isEditing && (
            <button
              type="button"
              onClick={onReset}
              className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-200"
            >
              Nuevo
            </button>
          )}
        </div>

        <div className="mt-5 flex gap-3">
          <button
            type="button"
            onClick={() => setActiveTab('general')}
            className={`rounded-xl px-4 py-2 text-xs font-black uppercase tracking-[0.16em] ${activeTab === 'general' ? 'bg-cyan-500 text-slate-950' : 'bg-white/5 text-white'}`}
          >
            General
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('roi')}
            className={`rounded-xl px-4 py-2 text-xs font-black uppercase tracking-[0.16em] ${activeTab === 'roi' ? 'bg-white text-slate-950' : 'bg-white/5 text-white'}`}
          >
            ROI y Colas
          </button>
        </div>

        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          {activeTab === 'general' ? (
            generalFields.map((field) => (
              <InputField
                key={field.name}
                field={field}
                value={formState[field.name] ?? ''}
                onChange={onChange}
              />
            ))
          ) : (
            <>
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                  ROI de cola
                </label>
                <QueueRoiEditor
                  value={formState.queue_roi_polygon ?? []}
                  onChange={(nextValue) => onChange('queue_roi_polygon', nextValue)}
                  snapshotUrl={snapshotUrl}
                />
              </div>
              {roiFields.map((field) => (
                <InputField
                  key={field.name}
                  field={field}
                  value={formState[field.name] ?? ''}
                  onChange={onChange}
                />
              ))}
            </>
          )}

          <button
            type="submit"
            className="w-full rounded-2xl bg-white px-4 py-3 text-sm font-black uppercase tracking-[0.18em] text-slate-950 transition hover:bg-slate-200"
          >
            {isEditing ? 'Guardar cambios' : 'Guardar camara'}
          </button>
          {isEditing && (
            <button
              type="button"
              onClick={onDelete}
              className="w-full rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm font-black uppercase tracking-[0.18em] text-red-200 transition hover:bg-red-500/20"
            >
              Eliminar registro
            </button>
          )}
        </form>
      </section>
    </div>
  );
}
