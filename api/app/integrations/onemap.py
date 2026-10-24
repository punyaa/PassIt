"""OneMap geocoding: postal code -> coordinates and URA planning area.

Called once at listing creation, never during search. Results are cached in-process by
postal code. The planning-area lookup needs PASSIT_ONEMAP_TOKEN; without it the caller
falls back to the planning area of the nearest MRT station.
"""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeocodeResult:
    latitude: float
    longitude: float
    planning_area: str | None


_cache: dict[str, GeocodeResult | None] = {}


async def geocode_postal_code(postal_code: str) -> GeocodeResult | None:
    """Return None when OneMap is unreachable or the postal code is unknown."""
    if postal_code in _cache:
        return _cache[postal_code]

    settings = get_settings()
    base = settings.onemap_api_url.rstrip("/")
    headers = {"authorization": settings.onemap_token} if settings.onemap_token else {}
    result: GeocodeResult | None = None
    try:
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            search = await client.get(
                f"{base}/common/elastic/search",
                params={
                    "searchVal": postal_code,
                    "returnGeom": "Y",
                    "getAddrDetails": "Y",
                    "pageNum": 1,
                },
            )
            search.raise_for_status()
            hits = search.json().get("results") or []
            if hits:
                latitude, longitude = float(hits[0]["LATITUDE"]), float(hits[0]["LONGITUDE"])
                planning_area = None
                if settings.onemap_token:
                    area = await client.get(
                        f"{base}/public/popapi/getPlanningarea",
                        params={"latitude": latitude, "longitude": longitude},
                    )
                    if area.is_success and area.json():
                        planning_area = str(area.json()[0]["pln_area_n"]).title()
                result = GeocodeResult(latitude, longitude, planning_area)
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as error:
        logger.warning("OneMap geocoding failed for %s: %s", postal_code, error)
        return None  # do not cache transient failures

    _cache[postal_code] = result
    return result
