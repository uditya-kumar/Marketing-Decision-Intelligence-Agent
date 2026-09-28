"""The data sources MDIA ingests, shared by ingestion, storage and trust checks.

Every source is needed for a complete day: blended metrics join ads, web and store.
"""

from __future__ import annotations

from typing import Literal, get_args

Source = Literal["google_ads", "meta_ads", "web_analytics", "store_orders"]
SOURCES: tuple[Source, ...] = get_args(Source)
