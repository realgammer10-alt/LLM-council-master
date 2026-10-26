"""Health checks for the API and its OpenRouter dependency."""

import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict

import httpx

from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL

logger = logging.getLogger(__name__)
OPENROUTER_MODELS_URL = OPENROUTER_API_URL.rsplit("/", 1)[0] + "/models"
HEALTH_CHECK_TIMEOUT = 3.0


async def check_openrouter() -> Dict[str, Any]:
    """Check OpenRouter connectivity without making a billable model request."""
    if not OPENROUTER_API_KEY:
        return {
            "status": "not_configured",
            "latency_ms": None,
            "message": "OpenRouter API key is not configured",
        }

    started_at = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
            response = await client.get(
                OPENROUTER_MODELS_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        latency_ms = round((perf_counter() - started_at) * 1000)
        logger.warning(
            "OpenRouter health check returned HTTP %s",
            error.response.status_code,
        )
        return {
            "status": "unhealthy",
            "latency_ms": latency_ms,
            "message": f"OpenRouter returned HTTP {error.response.status_code}",
        }
    except httpx.RequestError:
        latency_ms = round((perf_counter() - started_at) * 1000)
        logger.warning("OpenRouter health check could not reach the service")
        return {
            "status": "unhealthy",
            "latency_ms": latency_ms,
            "message": "OpenRouter could not be reached",
        }

    return {
        "status": "healthy",
        "latency_ms": round((perf_counter() - started_at) * 1000),
        "message": "OpenRouter is reachable",
    }


async def get_health_status() -> Dict[str, Any]:
    """Return current API and OpenRouter dependency health."""
    openrouter = await check_openrouter()
    api_status = "healthy"
    overall_status = "healthy" if openrouter["status"] == "healthy" else "degraded"
    return {
        "status": overall_status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "api": {
                "status": api_status,
                "message": "API is responding",
            },
            "openrouter": openrouter,
        },
    }
