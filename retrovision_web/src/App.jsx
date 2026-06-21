import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Activity,
  Building2,
  Camera,
  Cpu,
  LogOut,
  Shield,
  Store,
  Users,
} from 'lucide-react';

import CameraConfigurationPanel from './components/CameraConfigurationPanel';
import RegisterScreen from './components/RegisterScreen';
import Dashboard from './Dashboard';
import { API_BASE_URL } from './config';

const AUTH_STORAGE_KEY = 'retrovision_auth';
const VIEW_STORAGE_KEY = 'retrovision_active_view';

const ROLE_LABELS = {
  ADMIN_SOFTWARE: 'Administrador General',
  ADMIN_EMPRESA: 'Administrador de Empresa',
  SEGURIDAD: 'Seguridad',
};


function apiHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}


function extractApiError(error, fallbackMessage) {
  const payload = error?.response?.data;
  if (!payload) {
    return fallbackMessage;
  }

  if (typeof payload === 'string') {
    return payload;
  }

  if (Array.isArray(payload)) {
    return payload.join(' ');
  }

  const fragments = Object.entries(payload).flatMap(([key, value]) => {
    if (Array.isArray(value)) {
      return `${key}: ${value.join(', ')}`;
    }
    if (typeof value === 'string') {
      return `${key}: ${value}`;
    }
    return [];
  });

  return fragments.length > 0 ? fragments.join(' | ') : fallbackMessage;
}


function ScopeBadge({ profile }) {
  const scopeText = profile?.tenant_name
    ? profile.store_name
      ? `${profile.tenant_name} / ${profile.store_name}`
      : profile.tenant_name
    : 'Acceso global';

  return (
    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-xs text-cyan-100">
      <p className="font-semibold uppercase tracking-[0.22em] text-cyan-300">Alcance</p>
      <p className="mt-1 text-sm font-medium text-white">{scopeText}</p>
    </div>
  );
}


function LoginScreen({ credentials, onChange, onSubmit, loading, error, onRegisterClick }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(6,182,212,0.18),_transparent_35%),linear-gradient(180deg,#07111e_0%,#0b0f19_100%)] text-gray-100 flex items-center justify-center px-6 py-10">
      <div className="w-full max-w-5xl grid lg:grid-cols-[1.15fr_0.85fr] gap-8">
        <section className="rounded-[32px] border border-white/10 bg-[#0d1627]/80 backdrop-blur-xl p-8 shadow-[0_30px_100px_rgba(0,0,0,0.45)]">
          <div className="inline-flex items-center gap-3 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-300">
            <Activity className="h-4 w-4" />
            RetroVision Control Center
          </div>
          <h1 className="mt-8 max-w-xl text-4xl font-black tracking-tight text-white sm:text-5xl">
            Una sola plataforma para operar tiendas, cámaras y alertas en tiempo real.
          </h1>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-slate-300">
            La misma aplicación sirve para el administrador general, el administrador de cada empresa y el equipo de seguridad.
            El menú y el alcance cambian según el usuario autenticado.
          </p>

          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/8 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Multi-tenant</p>
              <p className="mt-2 text-lg font-bold text-white">Tenants y tiendas</p>
              <p className="mt-1 text-xs text-slate-400">Aislamiento por empresa y sucursal.</p>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Edge</p>
              <p className="mt-2 text-lg font-bold text-white">Nodos y camaras</p>
              <p className="mt-1 text-xs text-slate-400">Configuracion y ROI por camera_id.</p>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Operacion</p>
              <p className="mt-2 text-lg font-bold text-white">Alertas y analitica</p>
              <p className="mt-1 text-xs text-slate-400">Seguridad y negocio en la misma vista.</p>
            </div>
          </div>
        </section>

        <section className="rounded-[32px] border border-white/10 bg-[#101726]/90 p-8 shadow-[0_30px_100px_rgba(0,0,0,0.45)]">
          <h2 className="text-2xl font-black text-white">Iniciar sesion</h2>
          <p className="mt-2 text-sm text-slate-400">
            Usa tus credenciales de Django. El panel se adapta al rol asignado en backend.
          </p>

          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Usuario</label>
              <input
                value={credentials.username}
                onChange={(event) => onChange('username', event.target.value)}
                className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
                placeholder="admin"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Contrasena</label>
              <input
                type="password"
                value={credentials.password}
                onChange={(event) => onChange('password', event.target.value)}
                className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
                placeholder="********"
              />
            </div>

            {error && (
              <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-black uppercase tracking-[0.2em] text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60 cursor-pointer"
            >
              {loading ? 'Ingresando...' : 'Entrar al sistema'}
            </button>

            <div className="text-center pt-2">
              <button
                type="button"
                onClick={onRegisterClick}
                className="text-xs text-slate-400 hover:text-white transition cursor-pointer"
              >
                ¿No tienes cuenta? Regístrate y contrata
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}


function ManagementSection({
  title,
  subtitle,
  items,
  columns,
  formFields,
  formState,
  onChange,
  onSubmit,
  onSelectItem,
  selectedItemKey,
  onReset,
  onDelete,
  isEditing,
  snapshotUrl,
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
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
                    No hay registros visibles para este usuario.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr
                    key={item.id || item.camera_id || item.node_id || item.slug || item.code}
                    className={`border-t border-white/6 text-slate-200 cursor-pointer transition ${
                      selectedItemKey === (item.id || item.camera_id || item.node_id || item.slug || item.code)
                        ? 'bg-cyan-500/10'
                        : 'hover:bg-white/5'
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
          <h3 className="text-lg font-black text-white">{isEditing ? 'Editar registro' : 'Crear nuevo'}</h3>
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
        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          {formFields.map((field) => (
            <div key={field.name}>
              <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                {field.label}
              </label>
              {field.type === 'select' ? (
                <select
                  value={formState[field.name] ?? ''}
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
                  value={Array.isArray(formState[field.name]) ? JSON.stringify(formState[field.name]) : (formState[field.name] ?? '')}
                  onChange={(event) => onChange(field.name, event.target.value)}
                  placeholder={field.placeholder}
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
                />
              )}
            </div>
          ))}

          <button
            type="submit"
            className="w-full rounded-2xl bg-white px-4 py-3 text-sm font-black uppercase tracking-[0.18em] text-slate-950 transition hover:bg-slate-200"
          >
            {isEditing ? 'Guardar cambios' : 'Guardar registro'}
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


function AdminConsole({ token, profile, onRequestRefresh }) {
  const [activeModule, setActiveModule] = useState('tenants');
  const [datasets, setDatasets] = useState({
    tenants: [],
    stores: [],
    edgeNodes: [],
    cameras: [],
  });
  const [forms, setForms] = useState({
    tenants: { name: '', slug: '', max_cameras: '5', is_active: 'true' },
    stores: { tenant: '', name: '', code: '', address: '' },
    edgeNodes: { store: '', node_id: '', display_name: '', control_api_base_url: '' },
    cameras: {
      store: '',
      edge_node: '',
      camera_id: '',
      display_name: '',
      queue_wait_threshold: '5',
      video_source: '',
      queue_roi_polygon: [],
      queue_dwell_seconds: '2',
      queue_alert_people_threshold: '3',
      queue_alert_duration_seconds: '5',
      max_allowed_wait_seconds: '120',
      cashier_count: '1',
      service_rate_per_cashier_per_minute: '12',
    },
  });
  const [selectedRecords, setSelectedRecords] = useState({
    tenants: null,
    stores: null,
    edgeNodes: null,
    cameras: null,
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [cameraSnapshotUrl, setCameraSnapshotUrl] = useState('');

  const loadCameraSnapshot = async (cameraId) => {
    if (!cameraId || !token) {
      setCameraSnapshotUrl('');
      return;
    }
    try {
      const response = await axios.get(`${API_BASE_URL}/api/cameras/${cameraId}/snapshot/`, {
        headers: apiHeaders(token),
        responseType: 'blob',
      });
      const objectUrl = window.URL.createObjectURL(response.data);
      setCameraSnapshotUrl((previous) => {
        if (previous && previous.startsWith('blob:')) {
          window.URL.revokeObjectURL(previous);
        }
        return objectUrl;
      });
    } catch (snapshotError) {
      console.error(snapshotError);
      setCameraSnapshotUrl('');
    }
  };

  const canManageTenants = profile?.role === 'ADMIN_SOFTWARE';
  const canManageStructure = profile?.role === 'ADMIN_SOFTWARE' || profile?.role === 'ADMIN_EMPRESA';

  const fetchAdminData = async () => {
    if (!token) return;
    try {
      const cacheBust = Date.now();
      const requests = [
        axios.get(`${API_BASE_URL}/api/stores/?_=${cacheBust}`, { headers: apiHeaders(token) }),
        axios.get(`${API_BASE_URL}/api/edge-nodes/?_=${cacheBust}`, { headers: apiHeaders(token) }),
        axios.get(`${API_BASE_URL}/api/cameras/?_=${cacheBust}`, { headers: apiHeaders(token) }),
      ];

      if (canManageTenants) {
        requests.unshift(axios.get(`${API_BASE_URL}/api/tenants/?_=${cacheBust}`, { headers: apiHeaders(token) }));
      }

      const responses = await Promise.all(requests);
      const offset = canManageTenants ? 1 : 0;
      setDatasets({
        tenants: canManageTenants ? responses[0].data : [],
        stores: responses[offset].data,
        edgeNodes: responses[offset + 1].data,
        cameras: responses[offset + 2].data,
      });
      setError('');
    } catch (fetchError) {
      console.error(fetchError);
      setError(extractApiError(fetchError, 'No se pudieron cargar los modulos administrativos.'));
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, [token, profile?.role]);

  const handleFormChange = (section, field, value) => {
    setForms((previous) => ({
      ...previous,
      [section]: {
        ...previous[section],
        [field]: value,
      },
    }));
  };

  const resetSectionForm = (section) => {
    const defaults = {
      tenants: { name: '', slug: '', max_cameras: '5', is_active: 'true' },
      stores: { tenant: '', name: '', code: '', address: '' },
      edgeNodes: { store: '', node_id: '', display_name: '', control_api_base_url: '' },
      cameras: {
        store: '',
        edge_node: '',
        camera_id: '',
        display_name: '',
        queue_wait_threshold: '5',
        video_source: '',
        queue_roi_polygon: [],
        queue_dwell_seconds: '2',
        queue_alert_people_threshold: '3',
        queue_alert_duration_seconds: '5',
        max_allowed_wait_seconds: '120',
        cashier_count: '1',
        service_rate_per_cashier_per_minute: '12',
      },
    };
    setForms((previous) => ({ ...previous, [section]: defaults[section] }));
    setSelectedRecords((previous) => ({ ...previous, [section]: null }));
    if (section === 'cameras') {
      if (cameraSnapshotUrl && cameraSnapshotUrl.startsWith('blob:')) {
        window.URL.revokeObjectURL(cameraSnapshotUrl);
      }
      setCameraSnapshotUrl('');
    }
  };

  const selectRecord = (section, item) => {
    setSelectedRecords((previous) => ({ ...previous, [section]: item }));
    if (section === 'tenants') {
      setForms((previous) => ({
        ...previous,
        tenants: {
          name: item.name || '',
          slug: item.slug || '',
          max_cameras: String(item.max_cameras ?? '5'),
          is_active: String(item.is_active ?? 'true'),
        },
      }));
    }
    if (section === 'stores') {
      setForms((previous) => ({
        ...previous,
        stores: {
          tenant: item.tenant ? String(item.tenant) : '',
          name: item.name || '',
          code: item.code || '',
          address: item.address || '',
        },
      }));
    }
    if (section === 'edgeNodes') {
      setForms((previous) => ({
        ...previous,
        edgeNodes: {
          store: item.store ? String(item.store) : '',
          node_id: item.node_id || '',
          display_name: item.display_name || '',
          control_api_base_url: item.control_api_base_url || '',
        },
      }));
    }
    if (section === 'cameras') {
      loadCameraSnapshot(item.camera_id);
      const queuePolygon = Array.isArray(item.queue_roi_polygon) && item.queue_roi_polygon.length > 0
        ? item.queue_roi_polygon
        : (Array.isArray(item.roi_polygon) ? item.roi_polygon : []);
      setForms((previous) => ({
        ...previous,
        cameras: {
          store: item.store ? String(item.store) : '',
          edge_node: item.edge_node ? String(item.edge_node) : '',
          camera_id: item.camera_id || '',
          display_name: item.display_name || '',
          queue_wait_threshold: String(item.queue_wait_threshold ?? '5'),
          video_source: item.video_source || '',
          queue_roi_polygon: queuePolygon,
          queue_dwell_seconds: String(item.queue_dwell_seconds ?? '2'),
          queue_alert_people_threshold: String(item.queue_alert_people_threshold ?? '3'),
          queue_alert_duration_seconds: String(item.queue_alert_duration_seconds ?? '5'),
          max_allowed_wait_seconds: String(item.max_allowed_wait_seconds ?? '120'),
          cashier_count: String(item.cashier_count ?? '1'),
          service_rate_per_cashier_per_minute: String(item.service_rate_per_cashier_per_minute ?? '12'),
        },
      }));
    }
  };

  const createRecord = async (path, payload, section, resetState) => {
    try {
      await axios.post(`${API_BASE_URL}${path}`, payload, { headers: apiHeaders(token) });
      setForms((previous) => ({ ...previous, [section]: resetState }));
      setMessage('Registro creado correctamente.');
      setError('');
      fetchAdminData();
      onRequestRefresh?.();
    } catch (createError) {
      console.error(createError);
      setError(extractApiError(createError, 'No se pudo guardar el registro. Revisa permisos y datos.'));
    }
  };

  const updateRecord = async (path, payload, section) => {
    try {
      await axios.patch(`${API_BASE_URL}${path}`, payload, { headers: apiHeaders(token) });
      setMessage('Registro actualizado correctamente.');
      setError('');
      resetSectionForm(section);
      fetchAdminData();
      onRequestRefresh?.();
    } catch (updateError) {
      console.error(updateError);
      setError(extractApiError(updateError, 'No se pudo actualizar el registro.'));
    }
  };

  const deleteRecord = async (path, section) => {
    try {
      await axios.delete(`${API_BASE_URL}${path}`, { headers: apiHeaders(token) });
      setMessage('Registro eliminado correctamente.');
      setError('');
      resetSectionForm(section);
      fetchAdminData();
      onRequestRefresh?.();
    } catch (deleteError) {
      console.error(deleteError);
      setError(extractApiError(deleteError, 'No se pudo eliminar el registro.'));
    }
  };

  const modules = [
    canManageTenants && { key: 'tenants', label: 'Tenants', icon: Building2 },
    canManageStructure && { key: 'stores', label: 'Tiendas', icon: Store },
    canManageStructure && { key: 'edgeNodes', label: 'Nodos Edge', icon: Cpu },
    canManageStructure && { key: 'cameras', label: 'Camaras', icon: Camera },
  ].filter(Boolean);

  const storeOptions = datasets.stores.map((store) => ({ value: store.id, label: `${store.tenant_name || 'Tenant'} / ${store.name}` }));
  const tenantOptions = datasets.tenants.map((tenant) => ({ value: tenant.id, label: tenant.name }));
  const edgeNodeOptions = datasets.edgeNodes.map((edgeNode) => ({ value: edgeNode.id, label: edgeNode.display_name || edgeNode.node_id }));

  const sectionConfig = {
    tenants: {
      title: 'Tenants',
      subtitle: 'Empresas cliente registradas en la plataforma.',
      items: datasets.tenants,
      columns: [
        { key: 'name', label: 'Nombre' },
        { key: 'slug', label: 'Slug' },
        { key: 'max_cameras', label: 'Límite Cámaras' },
        { key: 'is_active', label: 'Activo', render: (item) => (item.is_active ? 'Sí' : 'No') },
      ],
      fields: [
        { name: 'name', label: 'Nombre' },
        { name: 'slug', label: 'Slug' },
        { name: 'max_cameras', label: 'Máx. Cámaras (Límite)', type: 'number' },
        {
          name: 'is_active',
          label: 'Estado Suscripción',
          type: 'select',
          options: [
            { value: 'true', label: 'Sí - Activo / Al día' },
            { value: 'false', label: 'No - Suspendido / Inactivo' },
          ],
        },
      ],
      submit: (event) => {
        event.preventDefault();
        const payload = {
          ...forms.tenants,
          max_cameras: Number(forms.tenants.max_cameras || 5),
          is_active: forms.tenants.is_active === 'true' || forms.tenants.is_active === true,
        };
        if (selectedRecords.tenants) {
          updateRecord(`/api/tenants/${selectedRecords.tenants.id}/`, payload, 'tenants');
          return;
        }
        createRecord('/api/tenants/', payload, 'tenants', { name: '', slug: '', max_cameras: '5', is_active: 'true' });
      },
      deleteAction: () => deleteRecord(`/api/tenants/${selectedRecords.tenants.id}/`, 'tenants'),
    },
    stores: {
      title: 'Tiendas',
      subtitle: 'Sucursales visibles segun el alcance del usuario.',
      items: datasets.stores,
      columns: [
        { key: 'tenant_name', label: 'Tenant' },
        { key: 'name', label: 'Tienda' },
        { key: 'code', label: 'Codigo' },
      ],
      fields: [
        ...(canManageTenants ? [{ name: 'tenant', label: 'Tenant', type: 'select', options: tenantOptions }] : []),
        { name: 'name', label: 'Nombre' },
        { name: 'code', label: 'Codigo' },
        { name: 'address', label: 'Direccion' },
      ],
      submit: (event) => {
        event.preventDefault();
        const payload = {
          ...forms.stores,
          tenant: canManageTenants ? forms.stores.tenant : profile.tenant,
        };
        if (selectedRecords.stores) {
          updateRecord(`/api/stores/${selectedRecords.stores.id}/`, payload, 'stores');
          return;
        }
        createRecord('/api/stores/', payload, 'stores', { tenant: '', name: '', code: '', address: '' });
      },
      deleteAction: () => deleteRecord(`/api/stores/${selectedRecords.stores.id}/`, 'stores'),
    },
    edgeNodes: {
      title: 'Nodos Edge',
      subtitle: 'Dispositivos autorizados para sincronizar configuracion y reportar camaras.',
      items: datasets.edgeNodes,
      columns: [
        { key: 'tenant_name', label: 'Tenant' },
        { key: 'store_name', label: 'Tienda' },
        { key: 'node_id', label: 'ID del Nodo' },
        { key: 'api_key', label: 'API Key' },
      ],
      fields: [
        { name: 'store', label: 'Tienda', type: 'select', options: storeOptions },
        { name: 'node_id', label: 'ID del Nodo' },
        { name: 'display_name', label: 'Nombre visible' },
      ],
      submit: (event) => {
        event.preventDefault();
        if (selectedRecords.edgeNodes) {
          updateRecord(`/api/edge-nodes/${selectedRecords.edgeNodes.id}/`, forms.edgeNodes, 'edgeNodes');
          return;
        }
        createRecord('/api/edge-nodes/', forms.edgeNodes, 'edgeNodes', { store: '', node_id: '', display_name: '', control_api_base_url: '' });
      },
      deleteAction: () => deleteRecord(`/api/edge-nodes/${selectedRecords.edgeNodes.id}/`, 'edgeNodes'),
    },
    cameras: {
      title: 'Camaras',
      subtitle: 'Catalogo central de camaras, ROI y configuracion operativa.',
      items: datasets.cameras,
      columns: [
        { key: 'tenant_name', label: 'Tenant' },
        { key: 'store_name', label: 'Tienda' },
        { key: 'camera_id', label: 'Camera ID' },
        { key: 'edge_node_name', label: 'Edge Node' },
        { key: 'queue_alert_people_threshold', label: 'Umbral cola' },
      ],
      fields: [
        { name: 'store', label: 'Tienda', type: 'select', options: storeOptions },
        { name: 'edge_node', label: 'Nodo Edge', type: 'select', options: edgeNodeOptions },
        { name: 'camera_id', label: 'Camera ID' },
        { name: 'display_name', label: 'Nombre visible' },
        { name: 'video_source', label: 'Video source' },
        { name: 'queue_roi_polygon', label: 'ROI de cola', type: 'polygon' },
        { name: 'queue_dwell_seconds', label: 'Permanencia minima (s)', type: 'number' },
        { name: 'queue_alert_people_threshold', label: 'Personas para alerta', type: 'number' },
        { name: 'queue_alert_duration_seconds', label: 'Duracion alerta (s)', type: 'number' },
        { name: 'max_allowed_wait_seconds', label: 'Espera maxima permitida (s)', type: 'number' },
        { name: 'cashier_count', label: 'Cantidad de cajeros', type: 'number' },
        { name: 'service_rate_per_cashier_per_minute', label: 'Atencion por cajero/min', type: 'number' },
        { name: 'queue_wait_threshold', label: 'Threshold cola (s)', type: 'number' },
      ],
      submit: (event) => {
        event.preventDefault();
        const payload = {
          ...forms.cameras,
          queue_wait_threshold: Number(forms.cameras.queue_wait_threshold || 5),
          queue_dwell_seconds: Number(forms.cameras.queue_dwell_seconds || 2),
          queue_alert_people_threshold: Number(forms.cameras.queue_alert_people_threshold || 3),
          queue_alert_duration_seconds: Number(forms.cameras.queue_alert_duration_seconds || 5),
          max_allowed_wait_seconds: Number(forms.cameras.max_allowed_wait_seconds || 120),
          cashier_count: Number(forms.cameras.cashier_count || 1),
          service_rate_per_cashier_per_minute: Number(forms.cameras.service_rate_per_cashier_per_minute || 12),
          queue_roi_polygon: forms.cameras.queue_roi_polygon,
          roi_polygon: forms.cameras.queue_roi_polygon,
        };
        if (selectedRecords.cameras) {
          updateRecord(`/api/cameras/${selectedRecords.cameras.camera_id}/`, payload, 'cameras');
          return;
        }
        createRecord('/api/cameras/', payload, 'cameras', {
          store: '',
          edge_node: '',
          camera_id: '',
          display_name: '',
          queue_wait_threshold: '5',
          video_source: '',
          queue_roi_polygon: [],
          queue_dwell_seconds: '2',
          queue_alert_people_threshold: '3',
          queue_alert_duration_seconds: '5',
          max_allowed_wait_seconds: '120',
          cashier_count: '1',
          service_rate_per_cashier_per_minute: '12',
        });
      },
      deleteAction: () => deleteRecord(`/api/cameras/${selectedRecords.cameras.camera_id}/`, 'cameras'),
    },
  };

  const activeSection = sectionConfig[activeModule];
  const cameraGeneralFields = [
    { name: 'store', label: 'Tienda', type: 'select', options: storeOptions },
    { name: 'edge_node', label: 'Nodo Edge', type: 'select', options: edgeNodeOptions },
    { name: 'camera_id', label: 'Camera ID' },
    { name: 'display_name', label: 'Nombre visible' },
    { name: 'video_source', label: 'Video source' },
  ];
  const cameraRoiFields = [
    { name: 'queue_dwell_seconds', label: 'Permanencia minima (s)', type: 'number' },
    { name: 'queue_alert_people_threshold', label: 'Personas para alerta', type: 'number' },
    { name: 'queue_alert_duration_seconds', label: 'Duracion alerta (s)', type: 'number' },
    { name: 'max_allowed_wait_seconds', label: 'Espera maxima permitida (s)', type: 'number' },
    { name: 'cashier_count', label: 'Cantidad de cajeros', type: 'number' },
    { name: 'service_rate_per_cashier_per_minute', label: 'Atencion por cajero/min', type: 'number' },
    { name: 'queue_wait_threshold', label: 'Threshold cola (s)', type: 'number' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[0.78fr_1.22fr]">
        <section className="rounded-[28px] border border-white/10 bg-[#0f1524]/80 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">Consola Administrativa</p>
          <h2 className="mt-3 text-3xl font-black text-white">Gestion estructural por rol</h2>
          <p className="mt-3 text-sm leading-7 text-slate-400">
            La misma app muestra opciones distintas segun el usuario autenticado. El backend tambien filtra el alcance.
          </p>
          <div className="mt-6">
            <ScopeBadge profile={profile} />
          </div>
        </section>

        <section className="rounded-[28px] border border-white/10 bg-[#121b2f]/80 p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Modulos administrativos</p>
            <button
              type="button"
              onClick={fetchAdminData}
              className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-200"
            >
              Recargar
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {modules.map((module) => {
              const Icon = module.icon;
              const isActive = activeModule === module.key;
              return (
                <button
                  key={module.key}
                  type="button"
                  onClick={() => setActiveModule(module.key)}
                  className={`rounded-2xl border p-4 text-left transition ${isActive ? 'border-cyan-500 bg-cyan-500/10' : 'border-white/8 bg-white/5 hover:border-white/20'}`}
                >
                  <Icon className={`h-5 w-5 ${isActive ? 'text-cyan-300' : 'text-slate-400'}`} />
                  <p className="mt-4 text-sm font-black uppercase tracking-[0.18em] text-white">{module.label}</p>
                </button>
              );
            })}
          </div>
        </section>
      </div>

      {message && <div className="rounded-2xl border border-green-500/20 bg-green-500/10 px-4 py-3 text-sm text-green-200">{message}</div>}
      {error && <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}

      {activeSection && activeModule === 'cameras' ? (
        <CameraConfigurationPanel
          title={activeSection.title}
          subtitle={activeSection.subtitle}
          items={activeSection.items}
          columns={activeSection.columns}
          formState={forms.cameras}
          onChange={(field, value) => handleFormChange('cameras', field, value)}
          onSubmit={activeSection.submit}
          onSelectItem={(item) => selectRecord('cameras', item)}
          selectedItemKey={selectedRecords.cameras?.camera_id}
          onReset={() => resetSectionForm('cameras')}
          onDelete={() => {
            if (selectedRecords.cameras && window.confirm('Esta accion eliminara el registro seleccionado. Deseas continuar?')) {
              activeSection.deleteAction();
            }
          }}
          isEditing={Boolean(selectedRecords.cameras)}
          snapshotUrl={cameraSnapshotUrl}
          generalFields={cameraGeneralFields}
          roiFields={cameraRoiFields}
        />
      ) : activeSection ? (
        <div className="space-y-8 animate-fade-in">
          <ManagementSection
            title={activeSection.title}
            subtitle={activeSection.subtitle}
            items={activeSection.items}
            columns={activeSection.columns}
            formFields={activeSection.fields}
            formState={forms[activeModule]}
            onChange={(field, value) => handleFormChange(activeModule, field, value)}
            onSubmit={activeSection.submit}
            onSelectItem={(item) => selectRecord(activeModule, item)}
            selectedItemKey={selectedRecords[activeModule]?.id || selectedRecords[activeModule]?.camera_id || selectedRecords[activeModule]?.node_id || selectedRecords[activeModule]?.slug || selectedRecords[activeModule]?.code}
            onReset={() => resetSectionForm(activeModule)}
            onDelete={() => {
              if (selectedRecords[activeModule] && window.confirm('Esta accion eliminara el registro seleccionado. Deseas continuar?')) {
                activeSection.deleteAction();
              }
            }}
            isEditing={Boolean(selectedRecords[activeModule])}
            snapshotUrl={activeModule === 'cameras' ? cameraSnapshotUrl : ''}
          />
          
          {activeModule === 'edgeNodes' && selectedRecords.edgeNodes && (
            <EdgeOnboardingCard node={selectedRecords.edgeNodes} />
          )}
        </div>
      ) : null}
    </div>
  );
}


function EdgeOnboardingCard({ node }) {
  const [copiedId, setCopiedId] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  
  const handleCopyId = () => {
    navigator.clipboard.writeText(node.node_id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(node.api_key);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <div className="rounded-[28px] border border-cyan-500/30 bg-[#0d1627]/90 p-6 shadow-xl relative overflow-hidden transition-all duration-300">
      <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-cyan-500/10 p-2.5 rounded-2xl border border-cyan-500/20">
            <Cpu className="w-6 h-6 text-cyan-400" />
          </div>
          <div>
            <h4 className="text-lg font-black text-white">🚀 Guía de Instalación del Agente de Cámaras</h4>
            <p className="text-xs text-slate-400">Sigue estos sencillos pasos para activar el procesamiento de video en tu local.</p>
          </div>
        </div>

        <a
          href={`${API_BASE_URL}/static/retrovision_edge.zip`}
          download
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-500 px-5 py-3 text-xs font-black uppercase tracking-wider text-slate-950 hover:bg-cyan-400 transition cursor-pointer text-center"
        >
          <span>📥 Descargar Agente (.ZIP)</span>
        </a>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl bg-white/5 border border-white/8 p-4">
          <p className="text-xs uppercase tracking-wider font-bold text-slate-400">ID del Nodo</p>
          <div className="mt-2 flex items-center justify-between gap-3 bg-[#060a12] border border-white/8 rounded-xl p-3">
            <code className="text-sm font-mono text-cyan-200 select-all">{node.node_id}</code>
            <button
              type="button"
              onClick={handleCopyId}
              className="text-[10px] uppercase font-bold text-cyan-400 hover:text-cyan-300 transition cursor-pointer"
            >
              {copiedId ? '¡Copiado!' : 'Copiar'}
            </button>
          </div>
        </div>

        <div className="rounded-2xl bg-white/5 border border-white/8 p-4">
          <p className="text-xs uppercase tracking-wider font-bold text-slate-400">Clave de API (API Key)</p>
          <div className="mt-2 flex items-center justify-between gap-3 bg-[#060a12] border border-white/8 rounded-xl p-3">
            <code className="text-sm font-mono text-cyan-200 select-all">{node.api_key.substring(0, 15)}...</code>
            <button
              type="button"
              onClick={handleCopyKey}
              className="text-[10px] uppercase font-bold text-cyan-400 hover:text-cyan-300 transition cursor-pointer"
            >
              {copiedKey ? '¡Copiado!' : 'Copiar'}
            </button>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-4">
        <div className="rounded-2xl bg-white/3 border border-white/6 p-4">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-300">1</span>
          <h5 className="mt-3 font-bold text-white text-sm">Descargar</h5>
          <p className="mt-1 text-xs text-slate-400">Descarga el archivo ZIP del agente con el botón de arriba y descomprímelo en tu computadora.</p>
        </div>

        <div className="rounded-2xl bg-white/3 border border-white/6 p-4">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-300">2</span>
          <h5 className="mt-3 font-bold text-white text-sm">Ejecutar Script</h5>
          <p className="mt-1 text-xs text-slate-400">Abre la carpeta y haz doble clic en <code>iniciar_retrovision.bat</code> (o corre <code>iniciar_retrovision.sh</code> si usas Linux).</p>
        </div>

        <div className="rounded-2xl bg-white/3 border border-white/6 p-4">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-300">3</span>
          <h5 className="mt-3 font-bold text-white text-sm">Pegar Credenciales</h5>
          <p className="mt-1 text-xs text-slate-400">Copia el ID del Nodo y la Clave de API de arriba e ingrésalos en la ventana de la consola cuando te lo pida.</p>
        </div>

        <div className="rounded-2xl bg-white/3 border border-white/6 p-4">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-300">4</span>
          <h5 className="mt-3 font-bold text-white text-sm">Configurar Cámaras</h5>
          <p className="mt-1 text-xs text-slate-400">Una vez conectado, ve a la pestaña "Cámaras" en esta consola web para añadir tus streams locales.</p>
        </div>
      </div>
    </div>
  );
}


export default function App() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [screen, setScreen] = useState('login');
  const [auth, setAuth] = useState(() => {
    try {
      const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
      return raw ? JSON.parse(raw) : { token: '', refresh: '' };
    } catch {
      return { token: '', refresh: '' };
    }
  });
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [activeView, setActiveView] = useState(() => window.localStorage.getItem(VIEW_STORAGE_KEY) || 'operations');

  const roleLabel = useMemo(() => ROLE_LABELS[profile?.role] || 'Usuario', [profile]);
  const canManageAdmin = profile?.role === 'ADMIN_SOFTWARE' || profile?.role === 'ADMIN_EMPRESA';

  const handleCredentialsChange = (field, value) => {
    setCredentials((previous) => ({ ...previous, [field]: value }));
  };

  const loadProfile = async (accessToken) => {
    const response = await axios.get(`${API_BASE_URL}/api/accounts/me/`, {
      headers: apiHeaders(accessToken),
    });
    setProfile(response.data);
  };

  useEffect(() => {
    if (!auth.token) {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
  }, [auth]);

  useEffect(() => {
    window.localStorage.setItem(VIEW_STORAGE_KEY, activeView);
  }, [activeView]);

  useEffect(() => {
    if (!auth.token || profile) return;

    const bootstrapProfile = async () => {
      try {
        await loadProfile(auth.token);
      } catch (bootstrapError) {
        console.error(bootstrapError);
        setAuth({ token: '', refresh: '' });
        setProfile(null);
        setAuthError('Tu sesion expiro. Vuelve a iniciar sesion.');
      }
    };

    bootstrapProfile();
  }, [auth.token, profile]);

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/token/`, credentials);
      const nextAuth = { token: response.data.access, refresh: response.data.refresh };
      setAuth(nextAuth);
      await loadProfile(nextAuth.token);
      setAuthError('');
    } catch (loginError) {
      console.error(loginError);
      setAuthError('Credenciales invalidas o backend no disponible.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setAuth({ token: '', refresh: '' });
    setProfile(null);
    setActiveView('operations');
    setCredentials({ username: '', password: '' });
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  };

  if (!auth.token || !profile) {
    if (screen === 'register') {
      return (
        <RegisterScreen
          onBackToLogin={() => setScreen('login')}
          onRegisterSuccess={(nextAuth) => {
            setAuth(nextAuth);
            setScreen('login');
          }}
        />
      );
    }
    
    return (
      <LoginScreen
        credentials={credentials}
        onChange={handleCredentialsChange}
        onSubmit={handleLogin}
        loading={loading}
        error={authError}
        onRegisterClick={() => setScreen('register')}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(34,211,238,0.09),_transparent_30%),linear-gradient(180deg,#09101d_0%,#0b0f19_100%)] text-gray-100">
      {profile?.tenant_is_active === false && (
        <div className="bg-gradient-to-r from-red-950 via-red-900 to-red-950 text-red-200 border-b border-red-500/30 px-6 py-3.5 text-center text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 animate-pulse z-50 sticky top-0">
          <Shield className="w-4 h-4 text-red-400 shrink-0" />
          <span>⚠️ Suscripción de {profile.tenant_name} Inactiva o Suspendida. El procesamiento de alertas en tus cámaras está pausado.</span>
        </div>
      )}
      <header className="border-b border-gray-800/85 bg-[#0f1524]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-4">
        <div className="max-w-[1600px] mx-auto flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-tr from-cyan-500 to-emerald-500 p-2.5 rounded-2xl shadow-lg shadow-cyan-500/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-white">RetroVision Unified Console</h1>
              <p className="text-[11px] text-gray-400">Operacion y administracion multi-tenant desde una sola interfaz.</p>
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            {profile?.tenant_max_cameras !== undefined && (
              <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-xs">
                <p className="font-semibold uppercase tracking-[0.22em] text-cyan-300">Licencia SaaS</p>
                <p className="mt-0.5 text-white font-mono">Máx. {profile.tenant_max_cameras} Cámaras</p>
              </div>
            )}
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm">
              <p className="font-semibold text-white">{profile.username}</p>
              <p className="text-xs text-slate-400">{roleLabel}</p>
            </div>
            <button
              type="button"
              onClick={() => setActiveView('operations')}
              className={`rounded-2xl px-4 py-3 text-xs font-black uppercase tracking-[0.18em] ${activeView === 'operations' ? 'bg-cyan-500 text-slate-950' : 'bg-white/5 text-white'}`}
            >
              Operacion
            </button>
            {canManageAdmin && (
              <button
                type="button"
                onClick={() => setActiveView('admin')}
                className={`rounded-2xl px-4 py-3 text-xs font-black uppercase tracking-[0.18em] ${activeView === 'admin' ? 'bg-white text-slate-950' : 'bg-white/5 text-white'}`}
              >
                Administracion
              </button>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs font-black uppercase tracking-[0.18em] text-white"
            >
              <span className="inline-flex items-center gap-2">
                <LogOut className="h-4 w-4" />
                Salir
              </span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeView === 'admin' && canManageAdmin ? (
          <AdminConsole token={auth.token} profile={profile} onRequestRefresh={() => {}} />
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
            <div className="xl:col-span-12">
              <Dashboard token={auth.token} profile={profile} />
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-gray-800 bg-[#0f1524]/40 py-6 text-center text-xs text-gray-500">
        <p>RetroVision Security Systems © 2026</p>
        <p className="mt-1 font-mono text-[10px]">Multi-tenant admin + Edge operations + live analytics</p>
      </footer>
    </div>
  );
}
