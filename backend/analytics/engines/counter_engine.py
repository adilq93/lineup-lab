"""
Counter-lineup recommendation engine.

Finds the single worst-performing filter context for a trio and returns
the corresponding archetype label. Used in the detail modal.
"""

from __future__ import annotations

from analytics.engines.filter_engine import FILTER_MAP, build_filter_kwargs
from analytics.engines.trio_engine import compute_trio_stats, MIN_FILTERED_POSSESSIONS

ARCHETYPE_LABELS = {
    'big':       'BIG LINEUP',
    'shooters':  'SHOOTING LINEUP',
    'smallball': 'SMALL-BALL LINEUP',
    'clutch':    'CLUTCH LINEUP',
    'fast':      'FAST-PACE LINEUP',
    'slow':      'HALF-COURT LINEUP',
}

MIN_DELTA = -2.0  # must drop by at least 2 Net Rating points to surface a recommendation


def get_counter_recommendation(
    team_id: int,
    trio_player_ids: list[int],
    baseline_net: float,
) -> Optional[dict]:
    """
    Returns the worst-delta filter context as a recommendation dict, or None
    if no filter clears the minimum threshold.

    Return shape:
    {
        'archetype': 'BIG LINEUP',
        'filter': 'big',
        'delta': -13.8,
        'filtered_net': -5.6,
        'possessions': 312,
    }
    """
    worst_delta = 0.0
    worst_filter = None
    worst_result = None

    for filter_name in FILTER_MAP:
        kwargs = build_filter_kwargs([filter_name])
        result = compute_trio_stats(team_id, trio_player_ids, kwargs)

        if result is None:
            continue
        if result['possessions'] < MIN_FILTERED_POSSESSIONS:
            continue
        if result['net'] is None:
            continue

        delta = result['net'] - baseline_net
        if delta < worst_delta:
            worst_delta = delta
            worst_filter = filter_name
            worst_result = result

    if worst_filter is None or worst_delta > MIN_DELTA:
        return None

    return {
        'archetype': ARCHETYPE_LABELS[worst_filter],
        'filter': worst_filter,
        'delta': round(worst_delta, 1),
        'filtered_net': worst_result['net'],
        'possessions': worst_result['possessions'],
    }
