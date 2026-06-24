import logging
import uuid
import time
import stripe
from django.db import transaction
from django.utils.text import slugify
from django.core.cache import cache
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alerts_api.models import Tenant
from .models import User
from .serializers import UserProfileSerializer, UserRegistrationSerializer

logger = logging.getLogger("retrovision.billing")

class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        tenant = user.tenant
        if not tenant:
            return Response({"detail": "El usuario no tiene una empresa asociada."}, status=status.HTTP_400_BAD_REQUEST)
            
        plan_id = request.data.get('plan')
        if not plan_id:
            # Deducir del max_cameras
            if tenant.max_cameras <= 2:
                plan_id = 'basico'
            elif tenant.max_cameras <= 5:
                plan_id = 'estandar'
            else:
                plan_id = 'premium'
                
        prices_cents = {
            'basico': 1900,
            'estandar': 3900,
            'premium': 6900
        }
        amount = prices_cents.get(plan_id, 3900)
        
        stripe_secret = getattr(settings, "STRIPE_SECRET_KEY", "sk_test_mock")
        is_real_stripe = stripe_secret and stripe_secret.startswith("sk_") and stripe_secret != "sk_test_mock"
        
        session_id = f"cs_test_mock_{uuid.uuid4().hex}"
        
        if is_real_stripe:
            try:
                stripe.api_key = stripe_secret
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f"Suscripción RetroVision - Plan {plan_id.capitalize()}",
                            },
                            'unit_amount': amount,
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    client_reference_id=str(tenant.id),
                    success_url=request.build_absolute_uri(
                        f"/register/success?session_id={{CHECKOUT_SESSION_ID}}&tenant_id={tenant.id}&plan={plan_id}"
                    ),
                    cancel_url=request.build_absolute_uri("/"),
                )
                checkout_url = session.url
                session_id = session.id
            except Exception as stripe_error:
                is_real_stripe = False
                logger.error(f"Error al crear sesión real de Stripe para reintento: {stripe_error}. Fallback a simulación.")
                
        if not is_real_stripe:
            checkout_url = f"/stripe-checkout-mock?session_id={session_id}&tenant_id={tenant.id}&plan={plan_id}&email={user.email}"
            
        cache.set(f"stripe_session:{session_id}", {
            "tenant_id": tenant.id,
            "plan": plan_id,
            "email": user.email
        }, timeout=3600)
        
        return Response({
            "checkout_url": checkout_url,
            "session_id": session_id
        })



class UserRegistrationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Mapeo de límites de cámaras por plan
        plan_limits = {
            'basico': 2,
            'estandar': 5,
            'premium': 10
        }
        max_cameras = plan_limits.get(data['plan'], 5)
        
        try:
            with transaction.atomic():
                # Crear Tenant temporalmente como incomplete
                tenant = Tenant.objects.create(
                    name=data['tenant_name'],
                    slug=slugify(data['tenant_name']),
                    max_cameras=max_cameras,
                    subscription_status='incomplete',
                    is_active=False
                )
                
                # Crear User vinculado al Tenant con rol ADMIN_EMPRESA
                user = User.objects.create_user(
                    username=data['username'],
                    email=data.get('email', ''),
                    password=data['password'],
                    role=User.ADMIN_EMPRESA,
                    tenant=tenant
                )
        except Exception as exc:
            return Response(
                {"detail": f"Error al procesar el registro: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Crear Stripe Checkout Session (Simulada o Real)
        stripe_secret = getattr(settings, "STRIPE_SECRET_KEY", "sk_test_mock")
        stripe_pub = getattr(settings, "STRIPE_PUBLISHABLE_KEY", "pk_test_mock")
        
        prices_cents = {
            'basico': 1900,
            'estandar': 3900,
            'premium': 6900
        }
        amount = prices_cents.get(data['plan'], 1900)
        
        session_id = f"cs_test_mock_{uuid.uuid4().hex}"
        
        # Intentar flujo real de Stripe si la llave es válida
        is_real_stripe = stripe_secret and stripe_secret.startswith("sk_") and stripe_secret != "sk_test_mock"
        
        if is_real_stripe:
            try:
                stripe.api_key = stripe_secret
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f"Suscripción RetroVision - Plan {data['plan'].capitalize()}",
                            },
                            'unit_amount': amount,
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    client_reference_id=str(tenant.id),
                    success_url=request.build_absolute_uri(
                        f"/register/success?session_id={{CHECKOUT_SESSION_ID}}&tenant_id={tenant.id}&plan={data['plan']}"
                    ),
                    cancel_url=request.build_absolute_uri("/register"),
                )
                checkout_url = session.url
                session_id = session.id
            except Exception as stripe_error:
                # Si falla stripe real, hacemos fallback a simulación para no romper el flujo
                is_real_stripe = False
                logger.error(f"Error al crear sesión real de Stripe: {stripe_error}. Fallback a simulación.")
        
        if not is_real_stripe:
            # Flujo simulado local en React
            checkout_url = f"/stripe-checkout-mock?session_id={session_id}&tenant_id={tenant.id}&plan={data['plan']}&email={user.email}"
            
        # Guardar en cache para verificación posterior
        cache.set(f"stripe_session:{session_id}", {
            "tenant_id": tenant.id,
            "plan": data['plan'],
            "email": user.email
        }, timeout=3600)
            
        return Response({
            "message": "Registro guardado. Por favor complete el pago en Stripe para activar su cuenta.",
            "checkout_url": checkout_url,
            "session_id": session_id,
            "user": {
                "id": user.id,
                "username": user.username,
                "tenant_name": tenant.name,
                "role": user.role
            }
        }, status=status.HTTP_201_CREATED)


class CheckoutCompleteView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        session_id = request.data.get("session_id")
        card_number = request.data.get("card_number", "")
        card_expiry = request.data.get("card_expiry", "")
        card_cvc = request.data.get("card_cvc", "")
        
        if not session_id:
            return Response({"detail": "session_id es requerido."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Obtener de cache o usar fallback si expira
        session_data = cache.get(f"stripe_session:{session_id}")
        tenant_id = session_data.get("tenant_id") if session_data else request.data.get("tenant_id")
        plan_id = session_data.get("plan") if session_data else request.data.get("plan", "estandar")
        email = session_data.get("email") if session_data else request.data.get("email", "")
        
        if not tenant_id:
            return Response({"detail": "No se pudo identificar la empresa para la sesión dada."}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({"detail": "La empresa asociada no existe."}, status=status.HTTP_404_NOT_FOUND)
            
        if not email:
            user = User.objects.filter(tenant=tenant).first()
            email = user.email if user else "Desconocido"
            
        # Determinar si es simulación o real
        stripe_secret = getattr(settings, "STRIPE_SECRET_KEY", "sk_test_mock")
        is_real_stripe = stripe_secret and stripe_secret.startswith("sk_") and stripe_secret != "sk_test_mock" and not session_id.startswith("cs_test_mock_")
        
        if is_real_stripe:
            try:
                stripe.api_key = stripe_secret
                session = stripe.checkout.Session.retrieve(session_id)
                if session.payment_status == "paid":
                    tenant.subscription_status = 'active'
                    tenant.is_active = True
                    tenant.save()
                    logger.info(f"Intento de pago para usuario {email}. Plan: {plan_id}. Status: EXITOSO")
                    return Response({"status": "success", "message": "Suscripción activada exitosamente a través de Stripe."})
                else:
                    logger.info(f"Intento de pago para usuario {email}. Plan: {plan_id}. Status: DECLINADO (Sesión Stripe no pagada)")
                    return Response({"detail": "El pago no ha sido completado en Stripe."}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as stripe_error:
                logger.error(f"Error validando sesión real de Stripe: {stripe_error}")
                return Response({"detail": f"Error de validación con Stripe: {stripe_error}"}, status=status.HTTP_502_BAD_GATEWAY)
        else:
            # Validación Simulación (Mock Checkout)
            clean_card = "".join(card_number.split())
            
            # Validaciones básicas
            is_card_valid = len(clean_card) >= 15 and len(clean_card) <= 16 and clean_card.isdigit()
            is_test_card = clean_card.startswith("4242") or clean_card.startswith("4000") or clean_card.startswith("5555") or clean_card.startswith("37") or clean_card.startswith("34")
            
            # Validar CVC (3 o 4 dígitos)
            is_cvc_valid = card_cvc.isdigit() and len(card_cvc) in (3, 4)
            
            # Validar expiración (MM/YY o MM/YYYY)
            is_expiry_valid = False
            if "/" in card_expiry:
                try:
                    parts = card_expiry.split("/")
                    m = int(parts[0])
                    y = int(parts[1])
                    if m >= 1 and m <= 12:
                        is_expiry_valid = True
                except ValueError:
                    pass
            
            if not is_card_valid or not is_test_card or not is_cvc_valid or not is_expiry_valid:
                logger.info(f"Intento de pago para usuario {email}. Plan: {plan_id}. Status: DECLINADO")
                return Response({
                    "detail": "El pago de Stripe fue rechazado. Para simular el pago, use una tarjeta de prueba de Stripe válida (ej. 4242 4242 4242 4242, Expiración futura como 12/28, CVC de 3 dígitos)."
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Retardo artificial de red
            time.sleep(1.2)
            
            # Activar suscripción
            tenant.subscription_status = 'active'
            tenant.is_active = True
            tenant.save()
            
            logger.info(f"Intento de pago para usuario {email}. Plan: {plan_id}. Status: EXITOSO")
            return Response({
                "status": "success",
                "message": "Simulación de pago con Stripe completada. Suscripción activada."
            })
