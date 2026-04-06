"""
Trio analytics engine.

Computes ORtg / DRtg / Net Rating for a 3-man combination under optional
filter conditions. Uses the Hollinger possession formula:
    Possessions ≈ FGA − OREB + TOV + 0.44 × FTA
"""

from __future__ import annotations

from itertools import combinations

from django.db.models import Sum, Q

from ingestion.models import Game, PBPEvent

# NBA event message type constants
MSG_SHOT_MADE    = 1
MSG_SHOT_MISSED  = 2
MSG_FREE_THROW   = 3
MSG_REBOUND      = 4
MSG_TURNOVER     = 5
MSG_SUBSTITUTION = 8

MIN_TRIO_POSSESSIONS = 100
MIN_FILTERED_POSSESSIONS = 50  # below this → low_confidence


def get_team_trios(team_id: int) -> list:
    """
    Return all 3-man combinations for team_id that have >= MIN_TRIO_POSSESSIONS
    together (baseline, no filters).
    """
    # Get all games involving this team
    game_ids = list(
        Game.objects.filter(
            Q(home_team_id=team_id) | Q(away_team_id=team_id),
            lineups_computed=True,
        ).values_list('game_id', flat=True)
    )

    if not game_ids:
        return []

    # Collect all unique player IDs that appeared in lineups for this team
    home_events = PBPEvent.objects.filter(
        game_id__in=game_ids,
        game__home_team_id=team_id,
        home_lineup__isnull=False,
    ).values_list('home_lineup', flat=True)[:5000]

    away_events = PBPEvent.objects.filter(
        game_id__in=game_ids,
        game__away_team_id=team_id,
        away_lineup__isnull=False,
    ).values_list('away_lineup', flat=True)[:5000]

    player_ids: set = set()
    for lineup in list(home_events) + list(away_events):
        if lineup:
            player_ids.update(lineup)

    # Test every 3-man combo for minimum possessions
    valid_trios = []
    for trio in combinations(sorted(player_ids), 3):
        stats = compute_trio_stats(team_id, list(trio), {})
        if stats and stats['possessions'] >= MIN_TRIO_POSSESSIONS:
            valid_trios.append(trio)

    return valid_trios


def compute_trio_stats(
    team_id: int,
    trio_player_ids: list[int],
    filter_kwargs: dict,
) -> Optional[dict]:
    """
    Returns ORtg, DRtg, Net Rating for a trio under optional filter conditions.

    filter_kwargs is empty for baseline, or contains boolean flag conditions
    from filter_engine.build_filter_kwargs().

    Returns None if no events found.
    """
    # Find games where this team played and lineups were computed
    home_game_ids = set(
        Game.objects.filter(home_team_id=team_id, lineups_computed=True)
        .values_list('game_id', flat=True)
    )
    away_game_ids = set(
        Game.objects.filter(away_team_id=team_id, lineups_computed=True)
        .values_list('game_id', flat=True)
    )

    # Offensive events: trio is on court for this team
    off_events_home = PBPEvent.objects.filter(
        game_id__in=home_game_ids,
        home_lineup__contains=trio_player_ids,
        **filter_kwargs,
    )
    off_events_away = PBPEvent.objects.filter(
        game_id__in=away_game_ids,
        away_lineup__contains=trio_player_ids,
        **filter_kwargs,
    )

    off_stats_home = _aggregate_hollinger(off_events_home, team_id, offensive=True)
    off_stats_away = _aggregate_hollinger(off_events_away, team_id, offensive=True)

    fga  = off_stats_home['fga']  + off_stats_away['fga']
    fgm  = off_stats_home['fgm']  + off_stats_away['fgm']
    fg3m = off_stats_home['fg3m'] + off_stats_away['fg3m']
    oreb = off_stats_home['oreb'] + off_stats_away['oreb']
    tov  = off_stats_home['tov']  + off_stats_away['tov']
    fta  = off_stats_home['fta']  + off_stats_away['fta']
    pts  = off_stats_home['pts']  + off_stats_away['pts']

    poss = fga - oreb + tov + (0.44 * fta)

    if poss <= 0:
        return None

    ortg = round((pts / poss) * 100, 1)
    fg_pct = round((fgm / fga) * 100, 1) if fga > 0 else 0

    # Defensive events
    def_stats_home = _aggregate_hollinger(off_events_home, team_id, offensive=False)
    def_stats_away = _aggregate_hollinger(off_events_away, team_id, offensive=False)

    d_fga  = def_stats_home['fga']  + def_stats_away['fga']
    d_oreb = def_stats_home['oreb'] + def_stats_away['oreb']
    d_tov  = def_stats_home['tov']  + def_stats_away['tov']
    d_fta  = def_stats_home['fta']  + def_stats_away['fta']
    d_pts  = def_stats_home['pts']  + def_stats_away['pts']

    d_poss = d_fga - d_oreb + d_tov + (0.44 * d_fta)

    drtg = round((d_pts / d_poss) * 100, 1) if d_poss > 0 else None
    net  = round(ortg - drtg, 1) if drtg is not None else None

    return {
        'ortg': ortg,
        'drtg': drtg,
        'net': net,
        'possessions': int(poss),
        'pts': pts,
        'fga': fga,
        'fgPct': fg_pct,
        'fg3m': fg3m,
        'fta': fta,
        'oreb': oreb,
        'tov': tov,
        'low_confidence': int(poss) < MIN_FILTERED_POSSESSIONS,
    }


def _aggregate_hollinger(events_qs, team_id: int, offensive: bool) -> dict:
    """
    Aggregate Hollinger components from a queryset of PBPEvents.

    offensive=True  → count events where team_id matches (team's own offense)
    offensive=False → count events where team_id does NOT match (opponent offense
                      while trio is on court)
    """
    if offensive:
        qs = events_qs.filter(team_id=team_id)
    else:
        qs = events_qs.filter(team_id__isnull=False).exclude(team_id=team_id)

    # All shots (made and missed) are stored as MSG_SHOT_MADE=1 from the live API
    fga  = qs.filter(event_msg_type=MSG_SHOT_MADE).count()
    fgm  = qs.filter(event_msg_type=MSG_SHOT_MADE, points_scored__gt=0).count()
    fg3a = qs.filter(event_msg_type=MSG_SHOT_MADE, sub_type='Jump Shot', points_scored=3).count() + \
           qs.filter(event_msg_type=MSG_SHOT_MADE, sub_type__icontains='3pt').count()
    # Better 3PA: count all 3pt attempts (made + missed) from sub_type patterns
    fg3m = qs.filter(event_msg_type=MSG_SHOT_MADE, points_scored=3).count()
    oreb = qs.filter(event_msg_type=MSG_REBOUND, sub_type='offensive').count()
    tov  = qs.filter(event_msg_type=MSG_TURNOVER).count()
    fta  = qs.filter(event_msg_type=MSG_FREE_THROW).count()
    ftm  = qs.filter(event_msg_type=MSG_FREE_THROW, points_scored__gt=0).count()
    pts  = qs.aggregate(total=Sum('points_scored'))['total'] or 0

    return {
        'fga': fga, 'fgm': fgm, 'fg3m': fg3m,
        'oreb': oreb, 'tov': tov, 'fta': fta, 'ftm': ftm, 'pts': pts,
    }
