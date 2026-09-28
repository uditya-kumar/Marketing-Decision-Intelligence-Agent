"""Store (Shopify-like) daily sales: every true purchase, paid or organic, is an order."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from novawear_sim.world.rng import FloatArray, IntArray, RandomStreams, binomial

if TYPE_CHECKING:
    from novawear_sim.config.models import Funnel
    from novawear_sim.world.festive import CalendarEffects
    from novawear_sim.world.funnel import FunnelCounts

_REFUND_NOISE = 0.25


@dataclass(frozen=True)
class StoreDaily:
    orders: IntArray
    gross_sales: FloatArray
    discounts: FloatArray
    returns: FloatArray
    net_sales: FloatArray
    shipping: FloatArray
    taxes: FloatArray
    total_sales: FloatArray
    new_customers: IntArray
    returning_customers: IntArray


def store_daily(
    paid: FunnelCounts,
    organic: FunnelCounts,
    festive: CalendarEffects,
    funnel: Funnel,
    streams: RandomStreams,
) -> StoreDaily:
    paid_orders = paid.purchases.sum(axis=1)
    organic_orders = organic.purchases.sum(axis=1)
    orders = paid_orders + organic_orders
    order_value = paid.revenue.sum(axis=1) + organic.revenue.sum(axis=1)

    gross = order_value / (1.0 - festive.discount_rate)
    discounts = gross - order_value
    lag = funnel.refund_lag_days
    refunded = funnel.refund_rate * streams.lognormal("refunds", 1, _REFUND_NOISE)[:, 0]
    returns = np.zeros_like(order_value)
    returns[lag:] = (refunded * order_value)[: order_value.size - lag]
    net = gross - discounts - returns

    shipped = binomial(
        orders, funnel.shipping.share_of_orders, streams.uniform("shipping", 1)[:, 0]
    )
    shipping = shipped * funnel.shipping.fee
    taxes = net * funnel.tax_rate
    new = binomial(
        paid_orders, funnel.new_customer_share.paid, streams.uniform("new_paid", 1)[:, 0]
    ) + binomial(
        organic_orders, funnel.new_customer_share.organic, streams.uniform("new_organic", 1)[:, 0]
    )

    def r(x: FloatArray) -> FloatArray:
        return np.round(x, 2)

    return StoreDaily(
        orders=orders.astype(np.int64),
        gross_sales=r(gross),
        discounts=r(discounts),
        returns=r(returns),
        net_sales=r(net),
        shipping=r(shipping.astype(np.float64)),
        taxes=r(taxes),
        total_sales=r(net + shipping + taxes),
        new_customers=new,
        returning_customers=(orders - new).astype(np.int64),
    )
