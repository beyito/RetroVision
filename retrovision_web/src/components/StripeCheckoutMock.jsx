import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  ShieldCheck,
  CreditCard,
  Lock,
  ArrowLeft,
  RefreshCw,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { API_BASE_URL } from '../config';

export default function StripeCheckoutMock({ onPaymentSuccess, onCancel }) {
  // Extract query parameters
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get('session_id') || '';
  const tenantId = params.get('tenant_id') || '';
  const planId = params.get('plan') || 'estandar';
  const userEmail = params.get('email') || 'cliente@retrovision.com';

  const [formData, setFormData] = useState({
    cardNumber: '',
    cardExpiry: '',
    cardCvc: '',
    cardName: '',
    postalCode: ''
  });

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [cardBrand, setCardBrand] = useState('generic'); // 'visa', 'mastercard', 'amex', 'generic'

  // Plan info mapping
  const planDetails = {
    basico: { name: 'Plan Básico', price: 19.00 },
    estandar: { name: 'Plan Estándar', price: 39.00 },
    premium: { name: 'Plan Premium', price: 69.00 }
  };
  const plan = planDetails[planId] || planDetails.estandar;

  // Detect card brand in real-time
  useEffect(() => {
    const cleanNum = formData.cardNumber.replace(/\s+/g, '');
    if (cleanNum.startsWith('4')) {
      setCardBrand('visa');
    } else if (cleanNum.startsWith('5')) {
      setCardBrand('mastercard');
    } else if (cleanNum.startsWith('34') || cleanNum.startsWith('37')) {
      setCardBrand('amex');
    } else {
      setCardBrand('generic');
    }
  }, [formData.cardNumber]);

  const handleInputChange = (field, value) => {
    setError('');
    
    // Auto-formatting card number
    if (field === 'cardNumber') {
      const clean = value.replace(/\D/g, '');
      let formatted = '';
      for (let i = 0; i < clean.length && i < 16; i++) {
        if (i > 0 && i % 4 === 0) formatted += ' ';
        formatted += clean[i];
      }
      setFormData(prev => ({ ...prev, cardNumber: formatted }));
      return;
    }

    // Auto-formatting expiry (MM/YY)
    if (field === 'cardExpiry') {
      const clean = value.replace(/\D/g, '');
      let formatted = '';
      if (clean.length > 0) {
        formatted += clean.substring(0, 2);
        if (clean.length > 2) {
          formatted += '/' + clean.substring(2, 4);
        }
      }
      setFormData(prev => ({ ...prev, cardExpiry: formatted }));
      return;
    }

    // Format CVC
    if (field === 'cardCvc') {
      const clean = value.replace(/\D/g, '').substring(0, 4);
      setFormData(prev => ({ ...prev, cardCvc: clean }));
      return;
    }

    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handlePay = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Validate card details client-side
      const cleanCard = formData.cardNumber.replace(/\s+/g, '');
      if (cleanCard.length < 15 || cleanCard.length > 16) {
        throw new Error('Número de tarjeta inválido. Debe tener 15 o 16 dígitos.');
      }
      if (!formData.cardExpiry.includes('/') || formData.cardExpiry.length < 5) {
        throw new Error('Fecha de expiración inválida. Formato MM/YY requerido.');
      }
      if (formData.cardCvc.length < 3) {
        throw new Error('Código CVC inválido. Requiere 3 o 4 dígitos.');
      }

      // Call Backend Complete checkout
      const response = await axios.post(`${API_BASE_URL}/api/accounts/checkout-complete/`, {
        session_id: sessionId,
        tenant_id: tenantId,
        plan: planId,
        card_number: formData.cardNumber,
        card_expiry: formData.cardExpiry,
        card_cvc: formData.cardCvc
      });

      setSuccess(true);
      
      // Auto login using stored credentials
      setTimeout(async () => {
        try {
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
            onPaymentSuccess(authData);
          } else {
            // Check if user is already logged in (has active session)
            const localAuth = window.localStorage.getItem('retrovision_auth');
            if (localAuth) {
              const authData = JSON.parse(localAuth);
              if (authData && authData.token) {
                onPaymentSuccess(authData);
                return;
              }
            }
            // Fallback: go back to login if creds not found
            onCancel();
          }
        } catch (loginError) {
          console.error("Auto login failed after mock checkout:", loginError);
          onCancel();
        }
      }, 2000);

    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'El pago fue declinado por Stripe. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-[#07111e] text-white flex flex-col items-center justify-center p-6 text-center animate-fade-in">
        <div className="bg-[#0f1a30] border border-emerald-500/30 rounded-3xl p-8 max-w-md w-full shadow-2xl relative overflow-hidden flex flex-col items-center">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-teal-500" />
          <CheckCircle className="w-16 h-16 text-emerald-400 animate-bounce mb-5" />
          <h2 className="text-2xl font-black mb-2 uppercase tracking-wide">¡Pago Autorizado!</h2>
          <p className="text-sm text-slate-300 mb-6 leading-relaxed">
            Stripe ha procesado el pago de <strong>${plan.price.toFixed(2)} USD</strong> con éxito. Tu suscripción está activa.
          </p>
          <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            Configurando tu Licencia SaaS...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#07111e] text-slate-100 flex flex-col lg:flex-row">
      
      {/* Resumen del pedido (Izquierda) */}
      <div className="w-full lg:w-[45%] bg-[#0b1323] p-8 lg:p-16 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-slate-800">
        <div>
          <button
            onClick={onCancel}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition cursor-pointer mb-10"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Cancelar registro
          </button>
          
          <div className="flex items-center gap-2 mb-6">
            <ShieldCheck className="w-6 h-6 text-cyan-400" />
            <span className="font-extrabold uppercase text-xs tracking-wider text-cyan-300">RetroVision Billing</span>
          </div>

          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Suscripción SaaS</span>
          <h2 className="text-3xl font-black text-white mt-1 uppercase tracking-wide">{plan.name}</h2>
          <div className="flex items-baseline gap-1 mt-3">
            <span className="text-4xl font-black text-white">${plan.price.toFixed(2)}</span>
            <span className="text-sm text-slate-400">USD / mes</span>
          </div>

          <div className="mt-8 border-t border-slate-800 pt-6 space-y-4 text-sm">
            <div className="flex justify-between text-slate-400">
              <span>Suscripción mensual</span>
              <span className="text-white font-mono">${plan.price.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Impuestos (IVA 0%)</span>
              <span className="text-white font-mono">$0.00</span>
            </div>
            <div className="flex justify-between font-bold text-base border-t border-slate-800 pt-4 text-white">
              <span>Total a pagar hoy</span>
              <span className="text-cyan-400 font-mono">${plan.price.toFixed(2)}</span>
            </div>
          </div>
        </div>

        <div className="mt-10 text-xs text-slate-500 flex flex-col gap-2">
          <p className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Transacciones cifradas de extremo a extremo SSL de 256 bits.</span>
          </p>
          <p>Powered by <strong>Stripe Checkout</strong>. RetroVision no almacena datos de tarjetas.</p>
        </div>
      </div>

      {/* Formulario de Pago de Stripe (Derecha) */}
      <div className="w-full lg:w-[55%] p-8 lg:p-16 flex items-center justify-center bg-[#07111e]">
        <div className="max-w-md w-full bg-[#0d1627] border border-slate-800 rounded-3xl p-6 lg:p-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 to-purple-500" />
          
          <h3 className="text-lg font-black text-white flex items-center gap-2 mb-2">
            <CreditCard className="w-5 h-5 text-cyan-400 animate-pulse" />
            Pagar con Tarjeta
          </h3>
          <p className="text-xs text-slate-400 mb-6">Ingresa tus datos bancarios para autorizar la transacción mensual.</p>

          {error && (
            <div className="mb-5 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handlePay} className="space-y-4">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Correo Electrónico
              </label>
              <input
                type="email"
                disabled
                value={userEmail}
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-[#060a12] px-4 py-3 text-sm text-slate-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 flex justify-between">
                <span>Información de la Tarjeta</span>
                <span className="text-[9px] text-cyan-400 font-mono tracking-widest uppercase">
                  {cardBrand === 'visa' && '💳 VISA'}
                  {cardBrand === 'mastercard' && '💳 MASTERCARD'}
                  {cardBrand === 'amex' && '💳 AMEX'}
                </span>
              </label>
              
              <div className="mt-2 rounded-2xl border border-slate-800 bg-[#060a12] focus-within:border-cyan-500 transition overflow-hidden">
                <input
                  required
                  type="text"
                  value={formData.cardNumber}
                  onChange={(e) => handleInputChange('cardNumber', e.target.value)}
                  className="w-full px-4 py-3 text-sm text-white bg-transparent outline-none border-b border-slate-900 font-mono"
                  placeholder="Card number (4242 4242 4242 4242)"
                />
                <div className="flex">
                  <input
                    required
                    type="text"
                    value={formData.cardExpiry}
                    onChange={(e) => handleInputChange('cardExpiry', e.target.value)}
                    className="w-1/2 px-4 py-3 text-sm text-white bg-transparent outline-none border-r border-slate-900 font-mono"
                    placeholder="MM / YY"
                  />
                  <input
                    required
                    type="password"
                    value={formData.cardCvc}
                    onChange={(e) => handleInputChange('cardCvc', e.target.value)}
                    className="w-1/2 px-4 py-3 text-sm text-white bg-transparent outline-none font-mono"
                    placeholder="CVC"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Nombre en la Tarjeta
              </label>
              <input
                required
                type="text"
                value={formData.cardName}
                onChange={(e) => handleInputChange('cardName', e.target.value)}
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-[#060a12] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
                placeholder="ej: Juan Pérez"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">
                País o Región
              </label>
              <div className="mt-2 grid grid-cols-2 gap-4">
                <select
                  className="rounded-2xl border border-slate-800 bg-[#060a12] px-4 py-3 text-sm text-white focus:outline-none"
                  defaultValue="BO"
                >
                  <option value="BO">Bolivia</option>
                  <option value="US">Estados Unidos</option>
                  <option value="ES">España</option>
                </select>
                <input
                  required
                  type="text"
                  value={formData.postalCode}
                  onChange={(e) => handleInputChange('postalCode', e.target.value)}
                  className="rounded-2xl border border-slate-800 bg-[#060a12] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
                  placeholder="ZIP / Postal"
                />
              </div>
            </div>

            {/* Test Card Warning Banner */}
            <div className="mt-4 p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-2xl text-[10px] text-cyan-300 leading-relaxed font-semibold">
              ⚠️ <strong>Modo pruebas de Stripe:</strong> Usa la tarjeta <code>4242 4242 4242 4242</code> con cualquier expiración futura y CVC <code>123</code> para autorizar el cargo simulado de forma exitosa.
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-6 rounded-2xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-4 py-3.5 text-xs font-black uppercase tracking-[0.2em] transition disabled:opacity-60 cursor-pointer flex justify-center items-center gap-2"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Procesando pago seguro...
                </>
              ) : (
                <>
                  <Lock className="w-3.5 h-3.5" />
                  Suscribirse e Iniciar - ${plan.price.toFixed(2)}
                </>
              )}
            </button>
          </form>
        </div>
      </div>

    </div>
  );
}
