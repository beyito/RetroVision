from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import User
from .models import Tenant, Store, EdgeNode, Camera, SecurityAlert, Telemetria_Afluencia

class RetroVisionApiTests(APITestCase):

    def setUp(self):
        # 1. Create Tenants
        self.tenant_a = Tenant.objects.create(name="Empresa A", slug="empresa-a", max_cameras=3)
        self.tenant_b = Tenant.objects.create(name="Empresa B", slug="empresa-b", max_cameras=2)

        # 2. Create Stores
        self.store_a1 = Store.objects.create(tenant=self.tenant_a, name="Tienda A1", code="tienda-a1")
        self.store_a2 = Store.objects.create(tenant=self.tenant_a, name="Tienda A2", code="tienda-a2")
        self.store_b1 = Store.objects.create(tenant=self.tenant_b, name="Tienda B1", code="tienda-b1")

        # 3. Create Edge Nodes
        self.edge_node = EdgeNode.objects.create(
            store=self.store_a1,
            node_id="node_a1",
            display_name="Edge Node A1",
            api_key="tWYLdkt9Y2YLrzd6YZCgVhUrzhx1gw0BrznJuShpX14"
        )

        # 4. Create Cameras
        self.camera_a1 = Camera.objects.create(store=self.store_a1, edge_node=self.edge_node, camera_id="cam-a1", display_name="Camara A1")
        self.camera_a2 = Camera.objects.create(store=self.store_a2, camera_id="cam-a2", display_name="Camara A2")
        self.camera_b1 = Camera.objects.create(store=self.store_b1, camera_id="cam-b1", display_name="Camara B1")

        # 5. Create Users for Roles
        self.admin_software = User.objects.create_user(
            username="admin_soft", password="password123", role=User.ADMIN_SOFTWARE
        )
        self.admin_empresa_a = User.objects.create_user(
            username="admin_emp_a", password="password123", role=User.ADMIN_EMPRESA, tenant=self.tenant_a
        )
        self.guard_a1 = User.objects.create_user(
            username="guard_a1", password="password123", role=User.SEGURIDAD, tenant=self.tenant_a, store=self.store_a1
        )

    def test_camera_list_scoping_by_role(self):
        """Test multi-tenant camera visibility filters based on authenticated user role."""
        url = reverse("camera-list")

        # Admin Software should see all 3 cameras
        self.client.force_authenticate(user=self.admin_software)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        # Admin Empresa A should only see Empresa A's 2 cameras
        self.client.force_authenticate(user=self.admin_empresa_a)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        camera_ids = [cam["camera_id"] for cam in response.data]
        self.assertIn("cam-a1", camera_ids)
        self.assertIn("cam-a2", camera_ids)
        self.assertNotIn("cam-b1", camera_ids)

        # Security Guard A1 should only see Tienda A1's camera
        self.client.force_authenticate(user=self.guard_a1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["camera_id"], "cam-a1")

    def test_historical_telemetry_with_security_metrics(self):
        """Test the consolidated historical telemetry report containing security_metrics."""
        now = timezone.now()
        
        # Telemetry
        Telemetria_Afluencia.objects.create(
            timestamp=now - timedelta(hours=2),
            camera_id="cam-a1",
            personas_entrantes=10,
            personas_salientes=5,
            personas_en_cola=2
        )
        # Security Alert
        SecurityAlert.objects.create(
            timestamp=now - timedelta(hours=1),
            camera_id="cam-a1",
            risk_score=0.9,
            rules_triggered=["arma", "mascarilla"]
        )

        url = reverse("telemetry-historical")
        self.client.force_authenticate(user=self.admin_empresa_a)
        
        # Request for tenant A scope
        response = self.client.get(url, {"tenant": self.tenant_a.id, "range": "7days"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check standard fields
        self.assertIn("total_records_analyzed", response.data)
        self.assertIn("security_metrics", response.data)
        
        # Verify custom security metrics aggregated
        sec_metrics = response.data["security_metrics"]
        self.assertEqual(sec_metrics["total_alerts"], 1)
        self.assertIn("arma", sec_metrics["rule_breakdown"])
        self.assertIn("mascarilla", sec_metrics["rule_breakdown"])
        self.assertEqual(sec_metrics["rule_breakdown"]["arma"], 1)
        self.assertEqual(sec_metrics["rule_breakdown"]["mascarilla"], 1)
        
        # Verify weekly day mapping exists
        alerts_by_day = sec_metrics["alerts_by_day"]
        self.assertTrue(len(alerts_by_day) > 0)
        current_day_name = now.strftime("%A")
        day_mapping = {
            "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
            "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
        }
        translated_day = day_mapping[current_day_name]
        
        day_info = next((d for d in alerts_by_day if d["day"] == translated_day), None)
        self.assertIsNotNone(day_info)
        self.assertEqual(day_info["alerts"], 1)

    def test_presigned_url_generation_structure(self):
        """Test that requesting an upload pre-signed URL generates the expected structure."""
        url = reverse("securityalert-presigned-url")
        self.client.force_authenticate(user=self.edge_node)

        payload = {
            "camera_id": "cam-a1",
            "risk_score": 0.85,
            "rules_triggered": ["mascarilla"],
            "filename": "alert_20260623.mp4",
            "timestamp": timezone.now().isoformat()
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("presigned_url", data)
        self.assertIn("s3_url", data)

    def test_dynamic_report_validation(self):
        """Test validation and error handling on dynamic reports view."""
        url = reverse("dynamic-report")
        
        # 1. Missing prompt
        self.client.force_authenticate(user=self.admin_empresa_a)
        response = self.client.post(url, {"format": "json"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prompt", response.json()["error"])
        
        # 2. Scoped cameras constraint (user with no accessible cameras)
        user_no_cameras = User.objects.create_user(
            username="no_cams", password="password123", role=User.SEGURIDAD, tenant=self.tenant_b
        )
        self.client.force_authenticate(user=user_no_cameras)
        response = self.client.post(url, {"prompt": "Quiero ver las alertas"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.json())

    def test_predictive_analysis_endpoint(self):
        """Test the predictive analysis endpoint returns correct data structure."""
        url = reverse("telemetry-predictive")
        self.client.force_authenticate(user=self.admin_empresa_a)
        
        # Call GET
        response = self.client.get(url, {"camera_id": "cam-a1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["camera_id"], "cam-a1")
        self.assertIn("predictions", data)
        self.assertEqual(len(data["predictions"]), 12)
        
        # Verify prediction keys
        pred = data["predictions"][0]
        self.assertIn("timestamp", pred)
        self.assertIn("hour", pred)
        self.assertIn("predicted_inflow", pred)
        self.assertIn("predicted_wait_seconds", pred)
        self.assertIn("predicted_queue", pred)
        self.assertIn("alert_probability", pred)

    @patch("requests.post")
    def test_chatbot_assistant_creation(self, mock_post):
        """Test Chatbot assistant creates resources and enforces tenant scope."""
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "candidates": [{
                "content": {
                    "role": "model",
                    "parts": [{
                        "functionCall": {
                            "name": "crear_tienda",
                            "args": {
                                "nombre": "Tienda Chatbot",
                                "direccion": "Calle Falsa 123"
                            }
                        }
                    }]
                }
            }]
        }

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "candidates": [{
                "content": {
                    "role": "model",
                    "parts": [{
                        "text": "He creado la tienda 'Tienda Chatbot' exitosamente."
                    }]
                }
            }]
        }

        mock_post.side_effect = [mock_response_1, mock_response_2]

        url = reverse("chatbot-chat")
        self.client.force_authenticate(user=self.admin_empresa_a)

        payload = {
            "message": "Crea una tienda llamada Tienda Chatbot en Calle Falsa 123",
            "history": []
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("He creado la tienda", data["text"])
        self.assertEqual(len(data["actions"]), 1)
        self.assertEqual(data["actions"][0]["type"], "store_created")
        self.assertEqual(data["actions"][0]["name"], "Tienda Chatbot")

        # Verify Store is created and owned by tenant_a
        created_store = Store.objects.filter(name="Tienda Chatbot").first()
        self.assertIsNotNone(created_store)
        self.assertEqual(created_store.tenant, self.tenant_a)

    @patch("requests.post")
    def test_chatbot_assistant_camera_limit(self, mock_post):
        """Test Chatbot assistant checks camera limit before creation."""
        # Límite de Empresa A es 3, ya tiene 2. Creamos una más para llegar al tope.
        Camera.objects.create(store=self.store_a1, camera_id="cam-a3", display_name="Camara A3")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "role": "model",
                    "parts": [{
                        "functionCall": {
                            "name": "crear_camara",
                            "args": {
                                "tienda_id": self.store_a1.id,
                                "camera_id": "cam-a4",
                                "nombre_mostrar": "Camara A4"
                            }
                        }
                    }]
                }
            }]
        }

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "candidates": [{
                "content": {
                    "role": "model",
                    "parts": [{
                        "text": "Lamentablemente he fallado porque se superó el límite."
                    }]
                }
            }]
        }
        mock_post.side_effect = [mock_response, mock_response_2]

        url = reverse("chatbot-chat")
        self.client.force_authenticate(user=self.admin_empresa_a)

        payload = {
            "message": "Registra una cámara cam-a4",
            "history": []
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Camera was NOT created in DB due to limit violation
        self.assertFalse(Camera.objects.filter(camera_id="cam-a4").exists())
