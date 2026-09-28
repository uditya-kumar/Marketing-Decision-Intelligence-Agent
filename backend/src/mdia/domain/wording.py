"""How a computed number reads: the one place values become words.

Every sentence MDIA shows about a movement — a list headline, an observation, a stop
condition — is built from numbers that ``domain/`` computed, so the wording lives next
to them rather than in a React component or a prompt. The grounding guard also needs
:func:`as_shown` to tell a copied number from an invented one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mdia.domain.kpi import label

if TYPE_CHECKING:
    from mdia.domain.kpi import Metric
    from mdia.domain.opportunities import OpportunityKind

_PERCENT: frozenset[str] = frozenset(
    {"ctr", "cvr", "web_cvr", "bounce_rate", "atc_rate", "checkout_rate", "purchase_rate"}
)
_MULTIPLE: frozenset[str] = frozenset({"roas", "mer", "frequency"})
_COUNT: frozenset[str] = frozenset(
    {"impressions", "clicks", "platform_conversions", "store_orders"}
)

# What a metric moving the wrong way, and the right way, means for the business.
_PHRASES: dict[Metric, tuple[str, str]] = {
    "cpa": ("costs more per sale", "costs less per sale"),
    "cpc": ("is paying more per click", "is paying less per click"),
    "cpm": ("is paying more to be seen", "is paying less to be seen"),
    "ctr": ("is getting fewer clicks", "is getting more clicks"),
    "cvr": ("is converting fewer clicks", "is converting more clicks"),
    "roas": ("is earning less per rupee", "is earning more per rupee"),
    "mer": ("is returning less overall", "is returning more overall"),
    "aov": ("has smaller orders", "has larger orders"),
    "atc_rate": ("has fewer visitors adding to cart", "has more visitors adding to cart"),
    "web_cvr": ("has fewer visitors buying", "has more visitors buying"),
    "spend": ("is spending ahead of plan", "is spending behind plan"),
    "platform_conversions": ("is under-reporting sales", "is reporting more sales"),
}


def title(entity_name: str, metric: Metric, *, kind: OpportunityKind) -> str:
    """The headline a list row shows: whose it is, and what it means in plain words."""
    phrases = _PHRASES.get(metric)
    if phrases is None:
        way = "moved the wrong way" if kind == "issue" else "moved the right way"
        return f"{entity_name}: {label(metric)} {way}"
    adverse, favourable = phrases
    return f"{entity_name} {adverse if kind == 'issue' else favourable}"


def moved(change: float | None) -> str:
    """``rose 45%`` / ``fell 45%``, or just ``moved`` when there is no baseline."""
    if change is None:
        return "moved"
    return f"{'rose' if change > 0 else 'fell'} {abs(change):.0f}%"


def value_text(metric: Metric, value: float) -> str:
    """A metric's value in the unit it is read in: a rate, a multiple, a count or rupees."""
    if metric in _PERCENT:
        return f"{as_shown(metric, value):.2f}%"
    if metric in _MULTIPLE:
        return f"{value:.2f}x"
    # Orders and clicks are things, not money; only a money metric gets a ₹.
    if metric in _COUNT:
        return f"{value:,.0f}"
    return rupees(value)


def as_shown(metric: Metric, value: float) -> float:
    """The number a reader actually sees: a rate as a percentage, anything else as it is."""
    return value * 100 if metric in _PERCENT else value


def rupees(value: float) -> str:
    """Rupees in the unit an Indian operator reads them in."""
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:.2f} L"
    return f"₹{value:,.0f}"
