"""Stable platform-style IDs derived from entity keys (same key ⇒ same ID, every run)."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from novawear_sim.world.entities import Level

_GOOGLE_DIGITS = {"campaign": 11, "ad_set": 11, "creative": 12}
_META_PREFIX = 120_210_000_000_000_000


def platform_id(source: str, level: Level, key: str) -> str:
    digest = int(hashlib.sha256(f"{source}:{level}:{key}".encode()).hexdigest(), 16)
    if source == "meta_ads":
        return str(_META_PREFIX + digest % 10**14)
    digits = _GOOGLE_DIGITS.get(level, 11)
    low = 10 ** (digits - 1)
    return str(low + digest % (9 * low))
