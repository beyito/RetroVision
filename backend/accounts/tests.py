from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from alerts_api.models import Tenant
from accounts.models import User

class RetroVisionBillingTests(APITestCase):

    def setUp(self):
        cache.clear()

    def test_user_registration_creates_incomplete_tenant(self):
        """Test that user registration creates a tenant with incomplete status and inactive state."""
        url = reverse("user-registration")
        data = {
            "username": "test_merchant",
            "password": "SecurePassword123!",
            "email": "merchant@test.com",
            "tenant_name": "Test SaaS Business",
            "plan": "estandar"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("checkout_url", response.data)
        self.assertIn("session_id", response.data)

        # Check tenant created in incomplete state
        tenant = Tenant.objects.get(name="Test SaaS Business")
        self.assertEqual(tenant.subscription_status, 'incomplete')
        self.assertFalse(tenant.is_active)
        self.assertEqual(tenant.max_cameras, 5) # standard plan limit

        # Check user created
        user = User.objects.get(username="test_merchant")
        self.assertEqual(user.role, User.ADMIN_EMPRESA)
        self.assertEqual(user.tenant, tenant)

    def test_create_checkout_session_for_existing_tenant(self):
        """Test that an authenticated user with an incomplete subscription can generate a new checkout session."""
        tenant = Tenant.objects.create(
            name="Existing Tenant",
            slug="existing-tenant",
            max_cameras=2,
            subscription_status='incomplete',
            is_active=False
        )
        user = User.objects.create_user(
            username="existing_user",
            password="Password123!",
            email="existing@test.com",
            role=User.ADMIN_EMPRESA,
            tenant=tenant
        )

        url = reverse("create-checkout-session")
        self.client.force_authenticate(user=user)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("checkout_url", response.data)
        self.assertIn("session_id", response.data)

    def test_checkout_complete_success_mock(self):
        """Test that a successful mock card validation activates the tenant subscription."""
        tenant = Tenant.objects.create(
            name="SaaS Business Incomplete",
            slug="saas-business-incomplete",
            max_cameras=5,
            subscription_status='incomplete',
            is_active=False
        )
        session_id = "cs_test_mock_12345"
        
        # Pre-seed cache
        cache.set(f"stripe_session:{session_id}", {
            "tenant_id": tenant.id,
            "plan": "estandar",
            "email": "saas@test.com"
        }, timeout=3600)

        url = reverse("checkout-complete")
        data = {
            "session_id": session_id,
            "card_number": "4242 4242 4242 4242",
            "card_expiry": "12/30",
            "card_cvc": "123"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")

        # Verify tenant is activated
        tenant.refresh_from_db()
        self.assertEqual(tenant.subscription_status, 'active')
        self.assertTrue(tenant.is_active)

    def test_checkout_complete_failure_mock(self):
        """Test that an invalid mock card validation leaves the subscription inactive."""
        tenant = Tenant.objects.create(
            name="SaaS Business Incomplete 2",
            slug="saas-business-incomplete-2",
            max_cameras=5,
            subscription_status='incomplete',
            is_active=False
        )
        session_id = "cs_test_mock_abcde"
        
        # Pre-seed cache
        cache.set(f"stripe_session:{session_id}", {
            "tenant_id": tenant.id,
            "plan": "estandar",
            "email": "saas2@test.com"
        }, timeout=3600)

        url = reverse("checkout-complete")
        
        # Invalid card (not Stripe test card number)
        data = {
            "session_id": session_id,
            "card_number": "1111 2222 3333 4444",
            "card_expiry": "12/30",
            "card_cvc": "123"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

        # Verify tenant is NOT activated
        tenant.refresh_from_db()
        self.assertEqual(tenant.subscription_status, 'incomplete')
        self.assertFalse(tenant.is_active)

    def test_user_profile_contains_subscription_status(self):
        """Test that UserProfileSerializer outputs the tenant's subscription status."""
        tenant = Tenant.objects.create(
            name="SaaS Business Active",
            slug="saas-business-active",
            max_cameras=5,
            subscription_status='active',
            is_active=True
        )
        user = User.objects.create_user(
            username="active_user",
            password="Password123!",
            email="active@test.com",
            role=User.ADMIN_EMPRESA,
            tenant=tenant
        )

        url = reverse("current-user-profile")
        self.client.force_authenticate(user=user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tenant_subscription_status"], "active")
        self.assertEqual(response.data["tenant_is_active"], True)
