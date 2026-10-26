"""Price suggestions: LLM first, median-based heuristic always available as fallback."""

import json
import logging
import re
import time
from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm import get_llm_client
from app.models import Listing

logger = logging.getLogger(__name__)

PROMPT = """You price peer-to-peer rentals in Singapore, in SGD.
Item: {title}
Category: {category}
Condition: {condition}
Comparable listings (daily prices): {comparables}

STRICT PRICING RULES:
- Longer rental periods must receive a bundle discount.
- For EACH of min, recommended, and max:
  - weekly price MUST be strictly less than 7 times the corresponding daily price
  - monthly price MUST be strictly less than 4 times the corresponding weekly price
- Aim for weekly pricing around 5 times daily pricing.
- Aim for monthly pricing around 3 times weekly pricing.
- NEVER calculate monthly pricing as 4 or more weeks.
- Before answering, verify the inequalities above.

Return ONLY JSON, no prose:
{{"day": {{"min": 0, "recommended": 0, "max": 0}},
 "week": {{"min": 0, "recommended": 0, "max": 0}},
 "month": {{"min": 0, "recommended": 0, "max": 0}}}}"""

# Used when a category has no comparable listings yet.
CATEGORY_DEFAULT_DAY = Decimal("10.00")
CONDITION_FACTOR = {
    "new": Decimal("1.15"),
    "like new": Decimal("1.10"),
    "good": Decimal("1.00"),
    "fair": Decimal("0.85"),
    "worn": Decimal("0.70"),
}
CACHE_TTL_SECONDS = 6 * 3600
_cache: dict[tuple[str, str, str], tuple[float, dict]] = {}

Prices = dict[str, dict[str, Decimal]]


class InvalidSuggestion(ValueError):
    pass


async def comparable_prices(db: AsyncSession, category: str, limit: int = 20) -> list[Decimal]:
    rows = await db.scalars(
        select(Listing.price_day)
        .where(Listing.category == category, Listing.status == "active")
        .order_by(Listing.created_at.desc())
        .limit(limit)
    )
    return list(rows)


def _band(value: Decimal) -> dict[str, Decimal]:
    cent = Decimal("0.01")
    return {
        "min": (value * Decimal("0.8")).quantize(cent),
        "recommended": value.quantize(cent),
        "max": (value * Decimal("1.2")).quantize(cent),
    }


def heuristic_prices(comparables: list[Decimal], condition: str) -> Prices:
    base = Decimal(median(comparables)) if comparables else CATEGORY_DEFAULT_DAY
    day = base * CONDITION_FACTOR.get(condition.strip().lower(), Decimal("1.00"))
    week = day * 5  # one week costs about five days
    month = week * 3  # one month costs about three weeks
    return {"day": _band(day), "week": _band(week), "month": _band(month)}


def strip_fences(raw: str) -> str:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    return match.group(0) if match else raw


def validate_price_shape(data: object) -> Prices:
    if not isinstance(data, dict):
        raise InvalidSuggestion("not an object")
    prices: Prices = {}
    for period in ("day", "week", "month"):
        band = data.get(period)
        if not isinstance(band, dict):
            raise InvalidSuggestion(f"missing {period}")
        try:
            values = {
                k: Decimal(str(band[k])).quantize(Decimal("0.01"))
                for k in ("min", "recommended", "max")
            }
        except (KeyError, ArithmeticError) as error:
            raise InvalidSuggestion(f"bad {period} band") from error
        if not (Decimal("0") < values["min"] <= values["recommended"] <= values["max"]):
            raise InvalidSuggestion(f"{period} band out of order")
        prices[period] = values
    if prices["week"]["recommended"] >= 7 * prices["day"]["recommended"]:
        raise InvalidSuggestion("weekly not below 7x daily")
    if prices["month"]["recommended"] >= 4 * prices["week"]["recommended"]:
        raise InvalidSuggestion("monthly not below 4x weekly")
    return prices


async def suggest_price(
    db: AsyncSession, title: str, category: str, condition: str
) -> tuple[Prices, str]:
    """Return (prices, source). Never raises because of the model."""
    cache_key = (title.strip().lower(), category, condition.strip().lower())
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1], "cache"

    comparables = await comparable_prices(db, category)
    started = time.perf_counter()
    try:
        client = get_llm_client()
        if client is None:
            return heuristic_prices(comparables, condition), "heuristic"
        raw = await client.complete(
            PROMPT.format(
                title=title,
                category=category,
                condition=condition,
                comparables=", ".join(str(p) for p in comparables) or "none yet",
            )
        )
        prices = validate_price_shape(json.loads(strip_fences(raw)))
    except Exception as error:  # timeouts, throttling, bad JSON, missing SDK: all fall back
        logger.warning(
            "price suggestion fell back to heuristic after %.0f ms: %r",
            (time.perf_counter() - started) * 1000,
            error,
        )
        return heuristic_prices(comparables, condition), "heuristic"

    logger.info(
        "price suggestion from %s in %.0f ms", client.name, (time.perf_counter() - started) * 1000
    )
    _cache[cache_key] = (time.monotonic(), prices)
    return prices, "llm"
