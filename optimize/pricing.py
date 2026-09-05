"""Dynamic selling price with FPL's 50% sell-on fee.

When a player's price rises, you only bank 50% of the profit, rounded DOWN to the
nearest £0.1 (equivalently: every £0.2 rise gives £0.1 of sellable profit). Price
falls are borne in full. This governs how much cash a sale frees up.
"""
from __future__ import annotations


def selling_price(purchase: float, current: float) -> float:
    """Return the amount freed by selling a player bought at `purchase`.

    >>> selling_price(5.0, 5.0)   # no change
    5.0
    >>> selling_price(5.0, 5.4)   # +0.4 rise -> keep +0.2
    5.2
    >>> selling_price(5.0, 5.3)   # +0.3 rise -> keep +0.1 (rounded down)
    5.1
    >>> selling_price(5.0, 4.6)   # fall -> full loss
    4.6
    """
    if current <= purchase:
        return round(current, 1)
    rise_steps = round((current - purchase) * 10)      # number of £0.1 rises
    kept = (rise_steps // 2) * 0.1                       # 50%, rounded down to 0.1
    return round(purchase + kept, 1)
