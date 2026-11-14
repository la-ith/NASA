"""Fetch daily rainfall from the NASA POWER Daily API (sections 6 and 16)."""
import asyncio
from datetime import date

import httpx

from app.services.validation import PARAMETER

POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
COMMUNITY = "AG"
ADAPTER_VERSION = "1.0.0"
ATTEMPT_TIMEOUT_S = 10.0
RETRY_DELAY_S = 2.0


class ProviderError(Exception):
    """POWER could not supply the record. The UI shows the provider-error state."""


def power_query(lat: float, lon: float, start: date, end: date) -> dict[str, str]:
    return {
        "parameters": PARAMETER,
        "community": COMMUNITY,
        "latitude": f"{lat:.1f}",
        "longitude": f"{lon:.1f}",
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }


async def fetch_power_daily(
    client: httpx.AsyncClient, lat: float, lon: float, start: date, end: date
) -> dict:
    """Return the raw POWER JSON. Retry once after 2 s on a timeout, network error, 429 or 5xx."""
    query = power_query(lat, lon, start, end)
    for attempt in (1, 2):
        try:
            async with asyncio.timeout(ATTEMPT_TIMEOUT_S):  # whole attempt, not per socket read
                response = await client.get(POWER_DAILY_URL, params=query, timeout=ATTEMPT_TIMEOUT_S)
        except (TimeoutError, httpx.TransportError) as exc:
            problem, retryable = f"no response from NASA POWER ({exc!r})", True
        else:
            if response.status_code == 200:
                return response.json()
            problem = f"NASA POWER returned HTTP {response.status_code}"
            retryable = response.status_code == 429 or response.status_code >= 500
        if attempt == 1 and retryable:
            await asyncio.sleep(RETRY_DELAY_S)
            continue
        raise ProviderError(problem)
