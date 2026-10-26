import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from pydantic import ValidationError

from backend import monitoring
from backend.main import SendMessageRequest, app


class MonitoringTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_api_key_is_reported_without_network_request(self):
        with patch.object(monitoring, "OPENROUTER_API_KEY", None):
            with patch.object(monitoring.httpx, "AsyncClient") as client:
                result = await monitoring.check_openrouter()

        self.assertEqual(result["status"], "not_configured")
        client.assert_not_called()

    async def test_openrouter_success_reports_latency(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=response)

        with patch.object(monitoring, "OPENROUTER_API_KEY", "test-key"):
            with patch.object(monitoring.httpx, "AsyncClient", return_value=client):
                result = await monitoring.check_openrouter()

        self.assertEqual(result["status"], "healthy")
        self.assertGreaterEqual(result["latency_ms"], 0)
        client.get.assert_awaited_once_with(
            monitoring.OPENROUTER_MODELS_URL,
            headers={"Authorization": "Bearer test-key"},
        )

    async def test_openrouter_connection_failure_is_reported(self):
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(
            side_effect=httpx.ConnectError(
                "connection failed",
                request=httpx.Request("GET", monitoring.OPENROUTER_MODELS_URL),
            )
        )

        with patch.object(monitoring, "OPENROUTER_API_KEY", "test-key"):
            with patch.object(monitoring.httpx, "AsyncClient", return_value=client):
                result = await monitoring.check_openrouter()

        self.assertEqual(result["status"], "unhealthy")
        self.assertEqual(result["message"], "OpenRouter could not be reached")

    async def test_health_route_reports_api_and_dependency(self):
        health = {
            "status": "degraded",
            "checked_at": "2026-01-01T00:00:00+00:00",
            "checks": {
                "api": {"status": "healthy", "message": "API is responding"},
                "openrouter": {"status": "not_configured"},
            },
        }
        transport = httpx.ASGITransport(app=app)

        with patch("backend.main.get_health_status", new=AsyncMock(return_value=health)):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), health)

    async def test_health_is_degraded_when_openrouter_is_unavailable(self):
        openrouter = {
            "status": "unhealthy",
            "latency_ms": 30,
            "message": "OpenRouter could not be reached",
        }
        with patch(
            "backend.monitoring.check_openrouter",
            new=AsyncMock(return_value=openrouter),
        ):
            result = await monitoring.get_health_status()

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["checks"]["api"]["status"], "healthy")
        self.assertEqual(result["checks"]["openrouter"], openrouter)

    async def test_message_validation_trims_and_rejects_invalid_lengths(self):
        self.assertEqual(SendMessageRequest(content="  hello  ").content, "hello")
        with self.assertRaises(ValidationError):
            SendMessageRequest(content=" \n ")
        with self.assertRaises(ValidationError):
            SendMessageRequest(content="x" * 20001)

    async def test_invalid_message_is_rejected_by_api(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            blank_response = await client.post(
                "/api/conversations/not-a-real-id/message",
                json={"content": "   "},
            )
            long_response = await client.post(
                "/api/conversations/not-a-real-id/message",
                json={"content": "x" * 20001},
            )

        self.assertEqual(blank_response.status_code, 422)
        self.assertEqual(long_response.status_code, 422)

if __name__ == "__main__":
    unittest.main()
