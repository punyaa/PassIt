"""Bundled, fictional school-demo content and photo provenance."""

import json
from pathlib import Path
from typing import Literal, TypedDict, cast

DEMO_ROOT = Path(__file__).with_name("demo")


class DemoPhoto(TypedDict):
    file: str
    source_url: str


class DemoItem(TypedDict):
    slug: str
    title: str
    description: str
    category: str
    condition: str
    price_day: str
    price_week: str | None
    price_month: str | None
    deposit: str
    owner: int
    mrt_station: str
    check: str
    status: Literal["active", "paused"]
    photos: list[DemoPhoto]
    source_page: str


class DemoPerson(TypedDict):
    name: str
    bio: str
    mrt_station: str


class DemoScenario(TypedDict):
    item: str
    borrower: int
    state: Literal["confirmed", "handed_over", "returned", "settled", "damaged", "cancelled"]
    start: int
    end: int
    severity: Literal["minor", "moderate"] | None
    damage: str | None
    review: str | None
    lender_review: str | None


# title, category, condition, prices and deposit now live with each item's copy and photos.
ITEMS = cast(list[DemoItem], json.loads((DEMO_ROOT / "catalogue.json").read_text()))
PEOPLE = cast(list[DemoPerson], json.loads((DEMO_ROOT / "people.json").read_text()))
# Final state for each of the 15 bookings, with dates relative to the seed day.
BOOKING_PLAN = cast(list[DemoScenario], json.loads((DEMO_ROOT / "scenarios.json").read_text()))
