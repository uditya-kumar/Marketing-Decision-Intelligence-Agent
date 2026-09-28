"""The data sources MDIA ingests, shared by ingestion, storage and trust checks.

Every source is needed for a complete day: blended metrics join ads, web and store.
"""

from __future__ import annotations

from typing import Literal, get_args

Source = Literal["google_ads", "meta_ads", "web_analytics", "store_orders"]
SOURCES: tuple[Source, ...] = get_args(Source)

# Ad sources double as channels: each fact_ad_daily row belongs to one of them.
Channel = Literal["google_ads", "meta_ads"]
CHANNELS: tuple[Channel, ...] = get_args(Channel)

SOURCE_LABELS: dict[Source, str] = {
    "google_ads": "Google Ads",
    "meta_ads": "Meta Ads",
    "web_analytics": "Web analytics (GA4)",
    "store_orders": "Store orders (Shopify)",
}
