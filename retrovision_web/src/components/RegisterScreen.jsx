import React, { useState } from 'react';
import axios from 'axios';
import {
  Activity,
  ArrowLeft,
  Building2,
  Check,
  CreditCard,
  Key,
  Mail,
  Shield,
  User,
} from 'lucide-react';
import { API_BASE_URL } from '../config';

const PLANS = [
  {
    id: 'basico',
    name: 'Plan Básico',
    price: '$19',
    cameras: 'Hasta 2 cámaras',
    desc: 'Ideal para pequeñas tiendas locales o de conveniencia.',
    color: 'from-cyan-500 to-blue-500',
    shadow: 'shadow-cyan-500/10',
    features: ['2 Hilos de Procesamiento YOLO', 'Alertas por Robo en Tiempo Real', 'Soporte BYOH standard', 'Dashboard de Seguridad'],
  },
  {
    id: 'estandar',
    name: 'Plan Estándar',
    price: '$39',
    cameras: 'Hasta 5 cámaras',
    desc: 'Excelente para supermercados medianos o minimarkets.',
    color: 'from-cyan-500 to-emerald-500',
    shadow: 'shadow-emerald-500/15',
    features: ['5 Hilos de Procesamiento YOLO', 'Alertas por Robo y Armas Blancas', 'Analítica Comercial & Heatmaps', 'Onboarding automatizado', 'Soporte Prioritario'],
    popular: true,
  },
  {
    id: 'premium',
    name: 'Plan Premium',
    price: '$69',
    cameras: 'Hasta 10 cámaras',
    desc: 'Diseñado para grandes establecimientos o almacenes.',
    color: 'from-emerald-500 to-teal-500',
    shadow: 'shadow-teal-500/20',
    features: ['10 Hilos de Procesamiento YOLO', 'Armas de Fuego y Personas Enmascaradas', 'Analítica Comercial Avanzada', 'API de Integración Local', 'Soporte 24/7 Dedicado'],
  },
];

export default function RegisterScreen({ onBackToLogin, onRegisterSuccess }) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    tenant_name: '',
    plan: 'estandar',
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [globalError, setGlobalError] = useState('');

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const copy = { ...prev };
        delete copy[field];
        return copy;
      });
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setErrors({});
    setGlobalError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/accounts/register/`, formData);
      
      // Guardar credenciales temporalmente para el inicio de sesión automático después del pago
      window.sessionStorage.setItem('temp_reg_creds', JSON.stringify({
        username: formData.username,
        password: formData.password
      }));

      // Redirigir a la URL de Stripe Checkout (Real o Simulada)
      const checkoutUrl = response.data.checkout_url;
      if (checkoutUrl.startsWith('http')) {
        window.location.href = checkoutUrl;
      } else {
        // Redirección local para el simulador de Stripe Checkout
        window.location.href = window.location.origin + checkoutUrl;
      }
    } catch (error) {
      console.error(error);
      const payload = error?.response?.data;
      if (payload && typeof payload === 'object') {
        setErrors(payload);
        if (payload.detail) {
          setGlobalError(payload.detail);
        }
      } else {
        setGlobalError('No se pudo establecer conexión con el servidor.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(6,182,212,0.15),_transparent_35%),linear-gradient(180deg,#07111e_0%,#0b0f19_100%)] text-gray-100 flex flex-col justify-center px-4 sm:px-6 py-12 lg:px-8">
      <div className="max-w-[1280px] w-full mx-auto grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-start">
        
        {/* Planes y Precios */}
        <section className="space-y-6">
          <div className="flex items-center gap-2">
            <button
              onClick={onBackToLogin}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Regresar al inicio de sesión
            </button>
          </div>
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">
              <CreditCard className="h-3.5 w-3.5" />
              Planes de Suscripción
            </span>
            <h2 className="mt-4 text-3xl font-black text-white sm:text-4xl tracking-tight">
              Adquiere tu licencia SaaS y conecta tus cámaras
            </h2>
            <p className="mt-2 text-sm text-slate-400">
              SaaS Bring Your Own Hardware (BYOH). Selecciona el plan que se adapte al tamaño de tu establecimiento comercial.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-3 mt-8">
            {PLANS.map((plan) => {
              const isSelected = formData.plan === plan.id;
              return (
                <button
                  type="button"
                  key={plan.id}
                  onClick={() => handleChange('plan', plan.id)}
                  className={`text-left rounded-3xl border p-5 flex flex-col h-full relative transition-all duration-300 ${
                    isSelected
                      ? `border-cyan-500 bg-[#0d1627]/90 shadow-lg ${plan.shadow}`
                      : 'border-white/5 bg-[#090f1a]/60 hover:border-white/10 hover:bg-[#0a1220]/80'
                  }`}
                >
                  {plan.popular && (
                    <span className="absolute -top-3 left-6 rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500 px-3 py-0.5 text-[9px] font-extrabold uppercase tracking-wider text-slate-950">
                      Popular
                    </span>
                  )}
                  
                  <div className="mb-4">
                    <p className={`text-xs uppercase tracking-wider font-extrabold ${isSelected ? 'text-cyan-400' : 'text-slate-400'}`}>
                      {plan.name}
                    </p>
                    <div className="flex items-baseline gap-1 mt-2">
                      <span className="text-3xl font-black text-white">{plan.price}</span>
                      <span className="text-xs text-slate-400">/ mes</span>
                    </div>
                    <span className={`inline-block mt-2 text-[10px] px-2 py-0.5 rounded font-bold ${isSelected ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20' : 'bg-white/5 text-slate-400'}`}>
                      {plan.cameras}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed mb-4 flex-grow">
                    {plan.desc}
                  </p>

                  <div className="border-t border-white/5 pt-4 w-full">
                    <ul className="space-y-2 text-[10px] text-slate-300">
                      {plan.features.map((feat) => (
                        <li key={feat} className="flex items-center gap-1.5">
                          <Check className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
                          <span className="truncate">{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* Formulario de Registro */}
        <section className="rounded-[32px] border border-white/10 bg-[#0d1627]/80 backdrop-blur-xl p-8 shadow-[0_30px_100px_rgba(0,0,0,0.45)]">
          <h2 className="text-2xl font-black text-white">Crear cuenta SaaS</h2>
          <p className="mt-1 text-xs text-slate-400">
            Completa tus credenciales y los datos de tu empresa para dar de alta el servicio.
          </p>

          {globalError && (
            <div className="mt-5 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-200">
              {globalError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-cyan-400" />
                Nombre de Usuario (Acceso)
              </label>
              <input
                required
                value={formData.username}
                onChange={(e) => handleChange('username', e.target.value)}
                className={`mt-2 w-full rounded-2xl border bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500 ${
                  errors.username ? 'border-red-500/50' : 'border-white/10'
                }`}
                placeholder="ej: juan_perez"
              />
              {errors.username && (
                <span className="text-[10px] text-red-400 mt-1 block">{errors.username.join(' ')}</span>
              )}
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-cyan-400" />
                Correo Electrónico
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
                placeholder="juan@ejemplo.com"
              />
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-cyan-400" />
                Contraseña
              </label>
              <input
                required
                type="password"
                value={formData.password}
                onChange={(e) => handleChange('password', e.target.value)}
                className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
                placeholder="********"
              />
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-cyan-400" />
                Nombre de tu Empresa / Tienda
              </label>
              <input
                required
                value={formData.tenant_name}
                onChange={(e) => handleChange('tenant_name', e.target.value)}
                className={`mt-2 w-full rounded-2xl border bg-[#0a1220] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500 ${
                  errors.tenant_name ? 'border-red-500/50' : 'border-white/10'
                }`}
                placeholder="ej: Hipermercados El Solar"
              />
              {errors.tenant_name && (
                <span className="text-[10px] text-red-400 mt-1 block">{errors.tenant_name.join(' ')}</span>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 rounded-2xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-400 hover:to-emerald-400 px-4 py-3 text-sm font-black uppercase tracking-[0.2em] text-slate-950 transition disabled:opacity-60 cursor-pointer"
            >
              {loading ? 'Procesando pago y registro...' : 'Registrar y Contratar'}
            </button>
          </form>
        </section>

      </div>
    </div>
  );
}
