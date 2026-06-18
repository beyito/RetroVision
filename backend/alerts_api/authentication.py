"""Authentication helpers for edge nodes."""

from __future__ import annotations

from rest_framework import authentication, exceptions

from .models import EdgeNode


class EdgeNodeAuthentication(authentication.BaseAuthentication):
    """Authenticates edge nodes using node_id + api_key headers."""

    node_id_header = "HTTP_X_EDGE_NODE_ID"
    api_key_header = "HTTP_X_EDGE_API_KEY"

    def authenticate(self, request):
        node_id = request.META.get(self.node_id_header, "").strip()
        api_key = request.META.get(self.api_key_header, "").strip()

        if not node_id and not api_key:
            return None

        if not node_id or not api_key:
            raise exceptions.AuthenticationFailed(
                "X-Edge-Node-Id y X-Edge-Api-Key son requeridos."
            )

        try:
            edge_node = EdgeNode.objects.select_related("store", "store__tenant").get(
                node_id=node_id,
                api_key=api_key,
                is_active=True,
                store__is_active=True,
                store__tenant__is_active=True,
            )
        except EdgeNode.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Credenciales de edge node inválidas.") from exc

        return (edge_node, edge_node)
