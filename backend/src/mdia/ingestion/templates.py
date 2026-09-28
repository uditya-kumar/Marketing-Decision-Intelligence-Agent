"""Per-source CSV templates: how each platform export maps onto MDIA's canonical records."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from mdia.domain.sources import SOURCE_LABELS
from mdia.ingestion.parsers import (
    AMOUNT,
    COMPACT_DATE,
    COUNT,
    DEDUCTION,
    IDENTIFIER,
    ISO_DATE,
    SIGNED_AMOUNT,
    TEXT,
    choice,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from mdia.domain.sources import Source
    from mdia.ingestion.parsers import Parser

# A parsed row keyed by canonical field name. Values are heterogeneous (dates, ints,
# decimals, text), which is why this is not a TypedDict.
type Record = dict[str, Any]
# Cross-field rule: returns a rejection reason, or None when the row is fine.
type RowCheck = Callable[[Record], str | None]
type RecordKind = Literal["ad", "web", "store"]


@dataclass(frozen=True, slots=True)
class Column:
    header: str
    field: str
    parser: Parser
    # False for columns that are only validated (e.g. currency), never stored.
    stored: bool = True


@dataclass(frozen=True, slots=True)
class SourceTemplate:
    source: Source
    label: str
    kind: RecordKind
    columns: tuple[Column, ...]
    # Fields identifying a row; a repeat within one file is rejected as a duplicate.
    key: tuple[str, ...]
    checks: tuple[RowCheck, ...] = ()
    derive: Callable[[Record], Record] | None = None
    constants: Mapping[str, Any] = field(default_factory=dict)

    @property
    def headers(self) -> tuple[str, ...]:
        return tuple(column.header for column in self.columns)


def at_most(small: str, large: str) -> RowCheck:
    """Reject rows where ``small`` exceeds ``large`` (e.g. clicks > impressions)."""

    def check(record: Record) -> str | None:
        if record[small] > record[large]:
            return f"{small} ({record[small]}) exceeds {large} ({record[large]})"
        return None

    return check


# Within-file identity of an ad row; mirrors the fact_ad_daily key before the platform
# IDs are resolved to dimension rows.
_AD_KEY = (
    "date",
    "campaign_external_id",
    "ad_set_external_id",
    "creative_external_id",
    "age_group",
    "device",
    "region",
)
_clicks_within_impressions = at_most("clicks", "impressions")

GOOGLE_ADS = SourceTemplate(
    source="google_ads",
    label=SOURCE_LABELS["google_ads"],
    kind="ad",
    columns=(
        Column("Day", "date", ISO_DATE),
        Column("Campaign", "campaign_name", TEXT),
        Column("Campaign ID", "campaign_external_id", IDENTIFIER),
        Column("Ad group", "ad_set_name", TEXT),
        Column("Ad group ID", "ad_set_external_id", IDENTIFIER),
        Column("Ad ID", "creative_external_id", IDENTIFIER),
        Column("Ad name", "creative_name", TEXT),
        Column("Age", "age_group", TEXT),
        Column(
            "Device",
            "device",
            choice({"Mobile phones": "mobile", "Computers": "desktop", "Tablets": "tablet"}),
        ),
        Column("Region", "region", TEXT),
        Column("Currency code", "currency", choice({"INR": "INR"}), stored=False),
        Column("Cost", "spend", AMOUNT),
        Column("Impr.", "impressions", COUNT),
        Column("Clicks", "clicks", COUNT),
        Column("Conversions", "platform_conversions", AMOUNT),
        Column("Conv. value", "platform_revenue", AMOUNT),
    ),
    key=_AD_KEY,
    checks=(_clicks_within_impressions,),
    # Google reports no reach, and campaigns have no publisher platform.
    constants={"channel_id": "google_ads", "reach": None, "platform": None},
)


def _daily_breakdown(record: Record) -> str | None:
    # Meta can export multi-day totals; only a one-day breakdown maps onto daily facts.
    if record["date_end"] != record["date"]:
        return "Reporting starts and Reporting ends differ; export with a daily breakdown"
    return None


META_ADS = SourceTemplate(
    source="meta_ads",
    label=SOURCE_LABELS["meta_ads"],
    kind="ad",
    columns=(
        Column("Reporting starts", "date", ISO_DATE),
        Column("Reporting ends", "date_end", ISO_DATE, stored=False),
        Column("Campaign name", "campaign_name", TEXT),
        Column("Campaign ID", "campaign_external_id", IDENTIFIER),
        Column("Ad set name", "ad_set_name", TEXT),
        Column("Ad set ID", "ad_set_external_id", IDENTIFIER),
        Column("Ad name", "creative_name", TEXT),
        Column("Ad ID", "creative_external_id", IDENTIFIER),
        Column(
            "Platform",
            "platform",
            choice({p: p for p in ("facebook", "instagram", "audience_network", "messenger")}),
        ),
        Column("Age", "age_group", TEXT),
        Column("Device platform", "device", choice({"Mobile app": "mobile", "Desktop": "desktop"})),
        Column("Region", "region", TEXT),
        Column("Amount spent (INR)", "spend", AMOUNT),
        Column("Impressions", "impressions", COUNT),
        Column("Reach", "reach", COUNT),
        Column("Link clicks", "clicks", COUNT),
        Column("Purchases", "platform_conversions", AMOUNT),
        Column("Purchases conversion value", "platform_revenue", AMOUNT),
    ),
    key=_AD_KEY,
    checks=(_daily_breakdown, _clicks_within_impressions, at_most("reach", "impressions")),
    constants={"channel_id": "meta_ads"},
)


def _with_bounces(record: Record) -> Record:
    # GA4 defines bounce rate as 1 - engagement rate, so bounces = non-engaged sessions.
    return {**record, "bounces": record["sessions"] - record["engaged_sessions"]}


WEB_ANALYTICS = SourceTemplate(
    source="web_analytics",
    label=SOURCE_LABELS["web_analytics"],
    kind="web",
    columns=(
        Column("Date", "date", COMPACT_DATE),
        Column("Session source / medium", "source", TEXT),
        Column(
            "Device category", "device", choice({d: d for d in ("mobile", "desktop", "tablet")})
        ),
        Column("Sessions", "sessions", COUNT),
        Column("Engaged sessions", "engaged_sessions", COUNT, stored=False),
        Column("Add to carts", "add_to_cart", COUNT),
        Column("Checkouts", "checkout", COUNT),
        Column("Ecommerce purchases", "purchases", COUNT),
        Column("Purchase revenue", "revenue", AMOUNT),
    ),
    key=("date", "source", "device"),
    checks=(at_most("engaged_sessions", "sessions"),),
    derive=_with_bounces,
)

# Shopify rounds each column separately, so the identity can be off by a few paise.
_ROUNDING_TOLERANCE = Decimal("0.05")


def _net_sales_reconcile(record: Record) -> str | None:
    expected = record["gross_sales"] - record["discounts"] - record["refunds"]
    if abs(expected - record["revenue"]) > _ROUNDING_TOLERANCE:
        return f"Net sales ({record['revenue']}) != gross sales - discounts - returns ({expected})"
    return None


STORE_ORDERS = SourceTemplate(
    source="store_orders",
    label=SOURCE_LABELS["store_orders"],
    kind="store",
    columns=(
        Column("Day", "date", ISO_DATE),
        Column("Orders", "orders", COUNT),
        Column("Gross sales", "gross_sales", AMOUNT, stored=False),
        Column("Discounts", "discounts", DEDUCTION),
        Column("Returns", "refunds", DEDUCTION),
        Column("Net sales", "revenue", SIGNED_AMOUNT),
        Column("New customers", "new_customers", COUNT),
    ),
    key=("date",),
    checks=(at_most("new_customers", "orders"), _net_sales_reconcile),
)

TEMPLATES: tuple[SourceTemplate, ...] = (GOOGLE_ADS, META_ADS, WEB_ANALYTICS, STORE_ORDERS)
