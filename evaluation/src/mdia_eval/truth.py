"""Reading ``ground_truth.json`` and translating it into MDIA's own vocabulary.

The generator names things from the simulation's point of view — a Meta "channel"
can be ``instagram``, a landing-page break targets a campaign the web export only
knows by source. Everything the harness needs to bridge that gap lives here, so the
rest of the evaluation compares like with like.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mdia.domain.periods import Period

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from mdia.domain.kpi import Metric
    from mdia.domain.signals import Detector

# Which entities may legitimately carry a scenario's signal. A creative going tired
# also moves its ad set, and web data stops at the channel, so a funnel break can only
# surface above the campaign it was injected on.
_ANCESTORS_ALLOWED = frozenset({"creative_fatigue", "audience_mismatch"})
_WEB_ONLY = frozenset({"landing_page_break"})

# Metrics a scenario is allowed to show up on, beyond the ones ground truth lists.
_EXTRA_METRICS: dict[str, tuple[Metric, ...]] = {
    "creative_fatigue": ("roas", "cvr"),
    "audience_mismatch": ("roas",),
    "channel_opportunity": ("mer", "store_revenue"),
    "cpc_spike": ("roas",),
    "landing_page_break": ("bounce_rate", "atc_rate", "checkout_rate", "purchase_rate", "web_cvr"),
    "budget_overpace": (),
    "tracking_break": (),
}
# Scenarios judged by their detector rather than by which metric moved.
_DETECTORS: dict[str, tuple[Detector, ...]] = {
    "tracking_break": ("tracking_break",),
    "budget_overpace": ("goal_breach",),
}
# Ground truth reports what the platform stopped counting; MDIA reports the break itself.
_UNTRACKED_METRICS = frozenset({"platform_conversions", "platform_roas", "platform_revenue"})
# Whether the scenario should surface as something wrong or something to buy more of.
# A tired creative that happens to sit in a campaign having a good week is not detected
# by that good week, so the alert has to be of the right kind to count.
_KINDS: dict[str, str] = {"channel_opportunity": "win"}


@dataclass(frozen=True, slots=True)
class Event:
    """One injected scenario, with everything needed to recognise MDIA's version of it."""

    id: str
    kind: str
    window: Period
    onset: str
    # Entity IDs that may carry the signal; empty for an account-wide scenario.
    entities: frozenset[str]
    metrics: frozenset[str]
    detectors: frozenset[str]
    # The opportunity kind an alert must have to count as this scenario.
    kind_expected: str
    expected_signal_type: str | None
    expected_action: str | None

    @property
    def injected(self) -> bool:
        return self.kind != "no_issue"


def load(path: Path, lineage: Mapping[str, Sequence[str]] | None = None) -> list[Event]:
    """Parse a ground-truth file; ``lineage`` widens creative-level targets to their parents."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [_event(raw, lineage or {}) for raw in payload["events"]]


def _event(raw: dict[str, Any], lineage: Mapping[str, Sequence[str]]) -> Event:
    kind = str(raw["type"])
    entities = _entities(kind, raw["target"], lineage)
    listed = {str(m["metric"]) for m in raw["affected_metrics"]} - _UNTRACKED_METRICS
    return Event(
        id=str(raw["id"]),
        kind=kind,
        window=Period(dt.date.fromisoformat(raw["start"]), dt.date.fromisoformat(raw["end"])),
        onset=str(raw["onset"]),
        entities=frozenset(entities),
        metrics=frozenset(listed | set(_EXTRA_METRICS.get(kind, ()))),
        detectors=frozenset(_DETECTORS.get(kind, ())),
        kind_expected=_KINDS.get(kind, "issue"),
        expected_signal_type=raw["expected_signal_type"],
        expected_action=raw["expected_action"],
    )


def _entities(
    kind: str, target: Mapping[str, Any], lineage: Mapping[str, Sequence[str]]
) -> set[str]:
    """The entity IDs MDIA could raise this scenario on."""
    source, platform_id = target.get("source"), target.get("platform_id")
    channel = f"channel:{source}" if source else None
    if kind in _WEB_ONLY:
        # Sessions are only attributed to a source, never to the campaign that bought them.
        return {channel} if channel else set()
    level = str(target["level"])
    if level in {"account", "source"} or platform_id is None:
        # A Meta "channel" of instagram is still meta_ads as far as the exports go.
        return {channel} if channel and level != "account" else set()
    entity = f"{level}:{platform_id}"
    found = {entity}
    if level == "ad_set" and target.get("age_group"):
        # An age-group mismatch is reported on the segment inside the ad set.
        found.add(f"age_group:{platform_id}|{target['age_group']}")
    if kind in _ANCESTORS_ALLOWED:
        # Only within the campaign: a whole channel moving is a different finding.
        found.update(a for a in lineage.get(entity, ()) if a.startswith(("campaign:", "ad_set:")))
    return found
