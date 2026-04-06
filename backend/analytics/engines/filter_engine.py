"""
Translates a list of active filter names into Django ORM kwargs.
All active filters are ANDed together.
"""

FILTER_MAP = {
    'big':       {'opp_is_big_lineup': True},
    'shooters':  {'opp_is_shooter_lineup': True},
    'smallball': {'opp_is_smallball': True},
    'clutch':    {'is_clutch': True},
    'fast':      {'is_fast_game': True},
    'slow':      {'is_slow_game': True},
}

VALID_FILTERS = set(FILTER_MAP.keys())


def build_filter_kwargs(active_filters: list[str]) -> dict:
    """
    Given a list of active filter names, return merged ORM kwargs.
    Unknown filter names are silently ignored.
    """
    kwargs = {}
    for f in active_filters:
        if f in FILTER_MAP:
            kwargs.update(FILTER_MAP[f])
    return kwargs
