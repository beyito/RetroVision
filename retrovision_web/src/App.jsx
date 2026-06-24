import React, { useEffect, useMemo, useState, useRef } from 'react';
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
  CreditCard,
  Lock,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

import CameraConfigurationPanel from './components/CameraConfigurationPanel';
import RegisterScreen from './components/RegisterScreen';
import StripeCheckoutMock from './components/StripeCheckoutMock';
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
              {field.hint && (
                <span className="text-[10px] text-slate-400 mt-1.5 block leading-normal">
                  💡 {field.hint}
                </span>
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
      counting_line: [],
      counting_line_direction: 'forward',
      custom_zones: [],
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
        counting_line: [],
        counting_line_direction: 'forward',
        custom_zones: [],
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
          counting_line: item.counting_line || [],
          counting_line_direction: item.counting_line_direction || 'forward',
          custom_zones: item.custom_zones || [],
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
      title: 'Dispositivos de Procesamiento Local (Nodos Edge)',
      subtitle: 'Servidores o computadoras instaladas físicamente en tus locales para procesar transmisiones de video mediante Inteligencia Artificial.',
      items: datasets.edgeNodes,
      columns: [
        { key: 'tenant_name', label: 'Empresa' },
        { key: 'store_name', label: 'Tienda / Sucursal' },
        { key: 'node_id', label: 'ID del Nodo' },
        { key: 'api_key', label: 'API Key (Clave)' },
      ],
      fields: [
        { name: 'store', label: 'Tienda / Sucursal Física', type: 'select', options: storeOptions, hint: 'Sucursal de tu empresa donde estará físicamente instalada la computadora.' },
        { name: 'node_id', label: 'Código Único de Dispositivo (Node ID)', placeholder: 'ej: sucursal_central_servidor_01', hint: 'Identificador único que se ingresa en la consola del agente local para enlazar el hardware.' },
        { name: 'display_name', label: 'Nombre Descriptivo del Servidor', placeholder: 'ej: Servidor Pasillo Central', hint: 'Nombre de fantasía amigable para reconocer fácilmente el dispositivo.' },
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
      title: 'Cámaras de Seguridad e IA',
      subtitle: 'Catálogo de cámaras IP vinculadas para análisis de tráfico, colas y detección de amenazas en tiempo real.',
      items: datasets.cameras,
      columns: [
        { key: 'tenant_name', label: 'Empresa' },
        { key: 'store_name', label: 'Tienda' },
        { key: 'camera_id', label: 'Cámara ID' },
        { key: 'edge_node_name', label: 'Servidor Asociado' },
        { key: 'queue_alert_people_threshold', label: 'Umbral Alerta' },
      ],
      fields: [
        { name: 'store', label: 'Tienda / Sucursal Asociada', type: 'select', options: storeOptions, hint: 'Sucursal de tu empresa a la que pertenece esta cámara.' },
        { name: 'edge_node', label: 'Dispositivo Procesador (Nodo Edge)', type: 'select', options: edgeNodeOptions, hint: 'Computadora local que procesará la señal de video de esta cámara.' },
        { name: 'camera_id', label: 'Código de Cámara (Camera ID)', placeholder: 'ej: camara_salida_cajas_01', hint: 'Nombre identificador único de la cámara en el sistema.' },
        { name: 'display_name', label: 'Nombre Visible de la Cámara', placeholder: 'ej: Cámara Principal Pasillo 1', hint: 'Nombre amigable mostrado en los paneles de seguridad e informes.' },
        { name: 'video_source', label: 'Enlace del Video de la Cámara (Origen)', placeholder: 'ej: rtsp://user:pass@192.168.1.100:554/stream o 0 para cámara web', hint: 'Dirección de red de transmisión (RTSP) de tu cámara de seguridad IP, o un identificador de webcam local (ej: 0).' },
        { name: 'queue_roi_polygon', label: 'Área Poligonal de Cola (ROI)', type: 'polygon', hint: 'Polígono que delimita la zona donde se vigilan las colas de espera.' },
        { name: 'queue_dwell_seconds', label: 'Tiempo Mínimo de Permanencia (Segundos)', type: 'number', hint: 'Segundos que debe pasar un cliente dentro del área para ser considerado como en cola (previene conteo de transeúntes).' },
        { name: 'queue_alert_people_threshold', label: 'Umbral de Alerta (Personas)', type: 'number', hint: 'Cantidad de personas acumuladas en cola a partir de la cual se genera una alerta automática de congestión.' },
        { name: 'queue_alert_duration_seconds', label: 'Tiempo de Estabilidad de Alerta (Segundos)', type: 'number', hint: 'Segundos continuos que debe sostenerse la congestión para notificar formalmente de la alerta.' },
        { name: 'max_allowed_wait_seconds', label: 'Tiempo Máximo Sugerido de Espera (Segundos)', type: 'number', hint: 'Tiempo de espera máximo recomendado por estándares comerciales de la empresa.' },
        { name: 'cashier_count', label: 'Cantidad de Cajas Abiertas', type: 'number', hint: 'Cantidad de terminales de pago activas en esa área de colas.' },
        { name: 'service_rate_per_cashier_per_minute', label: 'Ritmo Medio de Atención (Personas/Minuto)', type: 'number', hint: 'Clientes estimados atendidos por minuto por cada cajero.' },
        { name: 'queue_wait_threshold', label: 'Tolerancia Operativa (Segundos)', type: 'number', hint: 'Margen técnico de holgura en el cálculo analítico de esperas.' },
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
          counting_line: forms.cameras.counting_line,
          counting_line_direction: forms.cameras.counting_line_direction,
          custom_zones: forms.cameras.custom_zones,
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
          counting_line: [],
          counting_line_direction: 'forward',
          custom_zones: [],
        });
      },
      deleteAction: () => deleteRecord(`/api/cameras/${selectedRecords.cameras.camera_id}/`, 'cameras'),
    },
  };

  const activeSection = sectionConfig[activeModule];
  const cameraGeneralFields = [
    { name: 'store', label: 'Tienda / Sucursal Asociada', type: 'select', options: storeOptions, hint: 'Sucursal de tu empresa a la que pertenece esta cámara.' },
    { name: 'edge_node', label: 'Dispositivo Procesador (Nodo Edge)', type: 'select', options: edgeNodeOptions, hint: 'Computadora local que procesará la señal de video de esta cámara.' },
    { name: 'camera_id', label: 'Código de Cámara (Camera ID)', placeholder: 'ej: camara_salida_cajas_01', hint: 'Nombre identificador único de la cámara en el sistema.' },
    { name: 'display_name', label: 'Nombre Visible de la Cámara', placeholder: 'ej: Cámara Principal Pasillo 1', hint: 'Nombre amigable mostrado en los paneles de seguridad e informes.' },
    { name: 'video_source', label: 'Enlace del Video de la Cámara (Origen)', placeholder: 'ej: rtsp://user:pass@192.168.1.100:554/stream o 0 para cámara web', hint: 'Dirección de red de transmisión (RTSP) de tu cámara de seguridad IP, o un identificador de webcam local (ej: 0).' },
  ];
  const cameraRoiFields = [
    { name: 'queue_dwell_seconds', label: 'Tiempo Mínimo de Permanencia (Segundos)', type: 'number', hint: 'Segundos que debe pasar un cliente dentro del área para ser considerado como en cola (previene conteo de transeúntes).' },
    { name: 'queue_alert_people_threshold', label: 'Umbral de Alerta (Personas)', type: 'number', hint: 'Cantidad de personas acumuladas en cola a partir de la cual se genera una alerta automática de congestión.' },
    { name: 'queue_alert_duration_seconds', label: 'Tiempo de Estabilidad de Alerta (Segundos)', type: 'number', hint: 'Segundos continuos que debe sostenerse la congestión para notificar formalmente de la alerta.' },
    { name: 'max_allowed_wait_seconds', label: 'Tiempo Máximo Sugerido de Espera (Segundos)', type: 'number', hint: 'Tiempo de espera máximo recomendado por estándares comerciales de la empresa.' },
    { name: 'cashier_count', label: 'Cantidad de Cajas Abiertas', type: 'number', hint: 'Cantidad de terminales de pago activas en esa área de colas.' },
    { name: 'service_rate_per_cashier_per_minute', label: 'Ritmo Medio de Atención (Personas/Minuto)', type: 'number', hint: 'Clientes estimados atendidos por minuto por cada cajero.' },
    { name: 'queue_wait_threshold', label: 'Tolerancia Operativa (Segundos)', type: 'number', hint: 'Margen técnico de holgura en el cálculo analítico de esperas.' },
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
          href="/retrovision_edge.zip"
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
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};


export default function App() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [screen, setScreen] = useState(() => {
    if (window.location.pathname === '/stripe-checkout-mock') return 'checkout-mock';
    if (window.location.pathname === '/register/success') return 'checkout-success';
    return 'login';
  });
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState('');
  const [successProcessing, setSuccessProcessing] = useState(false);
  const [successError, setSuccessError] = useState('');
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
  const authRef = useRef(auth);
  useEffect(() => {
    authRef.current = auth;
  }, [auth]);

  useEffect(() => {
    window.localStorage.setItem(VIEW_STORAGE_KEY, activeView);
  }, [activeView]);

  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        const currentAuth = authRef.current;
        if (
          error.response?.status === 401 &&
          !originalRequest._retry &&
          currentAuth?.refresh &&
          originalRequest.url &&
          !originalRequest.url.includes('/api/token/')
        ) {
          if (isRefreshing) {
            return new Promise((resolve, reject) => {
              failedQueue.push({ resolve, reject });
            })
              .then((token) => {
                if (originalRequest.headers) {
                  if (typeof originalRequest.headers.set === 'function') {
                    originalRequest.headers.set('Authorization', `Bearer ${token}`);
                  } else {
                    originalRequest.headers['Authorization'] = `Bearer ${token}`;
                  }
                }
                originalRequest._retry = true;
                return axios(originalRequest);
              })
              .catch((err) => {
                return Promise.reject(err);
              });
          }

          originalRequest._retry = true;
          isRefreshing = true;

          try {
            const refreshResponse = await axios.post(`${API_BASE_URL}/api/token/refresh/`, {
              refresh: currentAuth.refresh,
            });
            const nextAuth = {
              token: refreshResponse.data.access,
              refresh: refreshResponse.data.refresh || currentAuth.refresh,
            };
            setAuth(nextAuth);
            window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextAuth));
            processQueue(null, refreshResponse.data.access);
            isRefreshing = false;

            if (originalRequest.headers) {
              if (typeof originalRequest.headers.set === 'function') {
                originalRequest.headers.set('Authorization', `Bearer ${refreshResponse.data.access}`);
              } else {
                originalRequest.headers['Authorization'] = `Bearer ${refreshResponse.data.access}`;
              }
            }
            return axios(originalRequest);
          } catch (refreshError) {
            processQueue(refreshError, null);
            isRefreshing = false;
            console.error('Failed to refresh token in interceptor:', refreshError);
            handleLogout();
          }
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  useEffect(() => {
    if (screen !== 'checkout-success') return;

    const completeCheckout = async () => {
      const params = new URLSearchParams(window.location.search);
      const sessionId = params.get('session_id') || '';
      const tenantId = params.get('tenant_id') || '';
      const plan = params.get('plan') || '';
      
      if (!sessionId) {
        setSuccessError('No se encontró el ID de la sesión de pago.');
        return;
      }
      
      try {
        await axios.post(`${API_BASE_URL}/api/accounts/checkout-complete/`, {
          session_id: sessionId,
          tenant_id: tenantId,
          plan: plan
        });
        
        setSuccessProcessing(true);
        
        // Try auto login using stored credentials
        const rawCreds = window.sessionStorage.getItem('temp_reg_creds');
        if (rawCreds) {
          const creds = JSON.parse(rawCreds);
          const loginRes = await axios.post(`${API_BASE_URL}/api/token/`, {
            username: creds.username,
            password: creds.password
          });
          window.sessionStorage.removeItem('temp_reg_creds');
          
          const authData = {
            token: loginRes.data.access,
            refresh: loginRes.data.refresh
          };
          setAuth(authData);
          setProfile(null); // trigger profile reload
          setScreen('login');
          window.history.replaceState({}, document.title, '/');
        } else {
          // If no stored credentials, check if they are already logged in (paying from block screen)
          const localAuth = window.localStorage.getItem('retrovision_auth');
          if (localAuth) {
            const authData = JSON.parse(localAuth);
            if (authData && authData.token) {
              setAuth(authData);
              setProfile(null); // reload profile to update status to active
              setScreen('login');
              window.history.replaceState({}, document.title, '/');
              return;
            }
          }
          // Fallback: direct to login with success message
          setAuthError('¡Pago completado con éxito! Por favor inicie sesión.');
          setScreen('login');
          window.history.replaceState({}, document.title, '/');
        }
      } catch (err) {
        console.error(err);
        setSuccessError(err.response?.data?.detail || err.message || 'Error al validar el pago con Stripe.');
      }
    };
    
    completeCheckout();
  }, [screen]);

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

  const handlePaySaaS = async () => {
    setSessionLoading(true);
    setSessionError('');
    try {
      const response = await axios.post(`${API_BASE_URL}/api/accounts/create-checkout-session/`, {}, {
        headers: apiHeaders(auth.token)
      });
      const checkoutUrl = response.data.checkout_url;
      if (checkoutUrl.startsWith('http')) {
        window.location.href = checkoutUrl;
      } else {
        window.location.href = window.location.origin + checkoutUrl;
      }
    } catch (err) {
      console.error(err);
      setSessionError(extractApiError(err, 'No se pudo generar la sesión de pago. Intente más tarde.'));
    } finally {
      setSessionLoading(false);
    }
  };

  function handleLogout() {
    setAuth({ token: '', refresh: '' });
    setProfile(null);
    setActiveView('operations');
    setCredentials({ username: '', password: '' });
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  if (screen === 'checkout-mock') {
    return (
      <StripeCheckoutMock
        onPaymentSuccess={(authData) => {
          setAuth(authData);
          setScreen('login');
          setProfile(null); // Force profile reload to get the new active status
          window.history.replaceState({}, document.title, '/');
        }}
        onCancel={() => {
          setScreen('login');
          window.history.replaceState({}, document.title, '/');
        }}
      />
    );
  }

  if (screen === 'checkout-success') {
    return (
      <div className="min-h-screen bg-[#07111e] text-white flex flex-col items-center justify-center p-6 text-center animate-fade-in">
        <div className="bg-[#0f1a30] border border-cyan-500/30 rounded-3xl p-8 max-w-md w-full shadow-2xl relative overflow-hidden flex flex-col items-center">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 to-emerald-500" />
          
          {successError ? (
            <>
              <AlertCircle className="w-16 h-16 text-red-400 mb-5 animate-bounce" />
              <h2 className="text-2xl font-black mb-2 uppercase tracking-wide text-red-400">Error de Validación</h2>
              <p className="text-sm text-slate-300 mb-6 leading-relaxed">
                {successError}
              </p>
              <button
                onClick={() => {
                  setScreen('login');
                  window.history.replaceState({}, document.title, '/');
                }}
                className="w-full rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 text-white px-4 py-3 text-xs font-black uppercase tracking-[0.15em] transition cursor-pointer"
              >
                Volver al Inicio
              </button>
            </>
          ) : (
            <>
              <RefreshCw className="w-16 h-16 text-cyan-400 animate-spin mb-5" />
              <h2 className="text-2xl font-black mb-2 uppercase tracking-wide">Confirmando Pago</h2>
              <p className="text-sm text-slate-300 mb-6 leading-relaxed">
                Estamos validando la transacción con Stripe. Esto tomará solo unos segundos.
              </p>
              <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase animate-pulse">
                <Lock className="w-3.5 h-3.5" />
                Conexión segura SSL
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

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

  if (profile?.tenant_subscription_status !== 'active') {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(239,68,68,0.1),_transparent_35%),linear-gradient(180deg,#07111e_0%,#0b0f19_100%)] text-slate-100 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-[#0d1627]/90 border border-red-500/20 rounded-[32px] p-8 shadow-2xl relative overflow-hidden flex flex-col items-center text-center">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 to-amber-500" />
          
          <div className="bg-red-500/10 p-4 rounded-full border border-red-500/20 mb-6">
            <Lock className="w-8 h-8 text-red-400 animate-pulse" />
          </div>

          <h2 className="text-2xl font-black text-white uppercase tracking-wide">Acceso Restringido</h2>
          <p className="text-xs text-red-400 font-extrabold uppercase tracking-widest mt-1">Suscripción Inactiva</p>

          <p className="text-sm text-slate-300 mt-4 leading-relaxed">
            La suscripción para tu empresa <strong>{profile.tenant_name}</strong> se encuentra en estado <strong>{
              profile.tenant_subscription_status === 'incomplete' ? 'Incompleta' :
              profile.tenant_subscription_status === 'past_due' ? 'Pago Vencido' :
              profile.tenant_subscription_status === 'canceled' ? 'Cancelada' : profile.tenant_subscription_status
            }</strong>.
          </p>

          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
            Los paneles operativos de monitoreo, cámaras y la administración están bloqueados hasta que se complete el pago de la licencia SaaS.
          </p>

          {sessionError && (
            <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-xs text-red-200 w-full">
              {sessionError}
            </div>
          )}

          <div className="mt-8 w-full space-y-3">
            <button
              onClick={handlePaySaaS}
              disabled={sessionLoading}
              className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-slate-950 px-4 py-3.5 text-xs font-black uppercase tracking-[0.15em] transition disabled:opacity-60 cursor-pointer flex justify-center items-center gap-2"
            >
              {sessionLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Cargando pasarela...
                </>
              ) : (
                <>
                  <CreditCard className="w-3.5 h-3.5" />
                  Completar Pago en Stripe
                </>
              )}
            </button>

            <button
              onClick={handleLogout}
              className="w-full rounded-2xl border border-white/10 bg-white/5 text-white hover:bg-white/10 px-4 py-3 text-xs font-black uppercase tracking-[0.15em] transition flex justify-center items-center gap-2 cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              Cerrar Sesión
            </button>
          </div>
        </div>
      </div>
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
