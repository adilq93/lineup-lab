from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ingestion.models import Game, Player, TrioStat

TEAMS = {
    1610612743: {'name': 'Denver Nuggets',          'abbreviation': 'DEN'},
    1610612760: {'name': 'OKC Thunder',             'abbreviation': 'OKC'},
    1610612759: {'name': 'San Antonio Spurs',        'abbreviation': 'SAS'},
    1610612750: {'name': 'Minnesota Timberwolves',   'abbreviation': 'MIN'},
    1610612745: {'name': 'Houston Rockets',          'abbreviation': 'HOU'},
}


def _headshot_url(player_id: int) -> str:
    return f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png"


def _player_names():
    """Cache player names in memory."""
    if not hasattr(_player_names, '_cache'):
        _player_names._cache = dict(Player.objects.values_list('player_id', 'full_name'))
    return _player_names._cache


def _build_player_dicts(trio_stat):
    names = _player_names()
    ids = [trio_stat.player1_id, trio_stat.player2_id, trio_stat.player3_id]
    return [{
        'player_id': pid,
        'name': names.get(pid, str(pid)),
        'headshot_url': _headshot_url(pid),
    } for pid in ids]


def _stat_dict(row):
    return {
        'ortg': float(row.ortg) if row.ortg else None,
        'drtg': float(row.drtg) if row.drtg else None,
        'net': float(row.net) if row.net else None,
        'possessions': row.possessions,
        'pts': row.pts,
        'fga': row.fga,
        'fgm': row.fgm,
        'fgPct': float(row.fg_pct) if row.fg_pct else None,
        'fg3m': row.fg3m,
        'fta': row.fta,
        'oreb': row.oreb,
        'tov': row.tov,
        'low_confidence': row.possessions < 50,
    }


@api_view(['GET'])
def teams_list(request):
    data = [
        {'team_id': tid, 'name': info['name'], 'abbreviation': info['abbreviation']}
        for tid, info in TEAMS.items()
    ]
    return Response(data)


@api_view(['GET'])
def team_trios(request, team_id: int):
    if team_id not in TEAMS:
        return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)

    filters_param = request.query_params.get('filters', '')
    active_filters = [f.strip() for f in filters_param.split(',') if f.strip()] if filters_param else []

    baselines = TrioStat.objects.filter(
        team_id=team_id, filter_name='baseline', possessions__gte=300
    ).order_by('-net')[:10]

    # Pre-load filtered rows if a single filter is active
    filtered_map = {}
    if len(active_filters) == 1:
        for row in TrioStat.objects.filter(team_id=team_id, filter_name=active_filters[0]):
            filtered_map[row.trio_key] = row

    result = []
    for row in baselines:
        entry = {
            'trio_key': row.trio_key,
            'players': _build_player_dicts(row),
            'baseline': _stat_dict(row),
        }
        if row.trio_key in filtered_map:
            f_stats = _stat_dict(filtered_map[row.trio_key])
            entry['filtered'] = f_stats
            entry['delta'] = _compute_delta(entry['baseline'], f_stats)
        result.append(entry)

    return Response(result)


@api_view(['GET'])
def trio_detail(request, trio_key: str):
    team_id = request.query_params.get('team_id')
    if team_id:
        try:
            team_id = int(team_id)
        except ValueError:
            return Response({'error': 'Invalid team_id'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        row = TrioStat.objects.filter(trio_key=trio_key).first()
        if not row:
            return Response({'error': 'Trio not found'}, status=status.HTTP_404_NOT_FOUND)
        team_id = row.team_id

    all_rows = {
        r.filter_name: r
        for r in TrioStat.objects.filter(trio_key=trio_key, team_id=team_id)
    }

    baseline_row = all_rows.get('baseline')
    if not baseline_row:
        return Response({'error': 'No baseline data'}, status=status.HTTP_404_NOT_FOUND)

    baseline = _stat_dict(baseline_row)

    # Active filters from query string
    filters_param = request.query_params.get('filters', '')
    active_filters = [f.strip() for f in filters_param.split(',') if f.strip()] if filters_param else []

    # Filtered stats — if single filter, use pre-computed; if combo, would need live calc
    filtered = None
    delta = None
    if len(active_filters) == 1 and active_filters[0] in all_rows:
        f_row = all_rows[active_filters[0]]
        filtered = _stat_dict(f_row)
        delta = _compute_delta(baseline, filtered)

    # All 6 filter contexts
    all_filters = {}
    for fname in ['big', 'shooters', 'smallball', 'clutch', 'fast', 'slow']:
        if fname in all_rows:
            f_stats = _stat_dict(all_rows[fname])
            all_filters[fname] = {
                'stats': f_stats,
                'delta': _compute_delta(baseline, f_stats),
            }
        else:
            all_filters[fname] = {'stats': None, 'delta': None}

    # Counter recommendation: worst single-filter delta
    counter = _get_counter(baseline, all_rows)

    data = {
        'trio_key': trio_key,
        'players': _build_player_dicts(baseline_row),
        'baseline': baseline,
        'filtered': filtered,
        'delta': delta,
        'all_filters': all_filters,
        'active_filters': active_filters,
        'counter': counter,
    }

    return Response(data)


@api_view(['GET'])
def meta_freshness(request):
    latest_game = Game.objects.order_by('-game_date').first()
    latest_ingested = Game.objects.order_by('-ingested_at').first()

    data = {
        'last_game_date': latest_game.game_date if latest_game else None,
        'ingested_at': latest_ingested.ingested_at if latest_ingested else None,
    }
    return Response(data)


def _compute_delta(baseline, filtered):
    if not baseline or not filtered:
        return None
    return {
        'ortg': round(filtered['ortg'] - baseline['ortg'], 1) if filtered.get('ortg') and baseline.get('ortg') else None,
        'drtg': round(filtered['drtg'] - baseline['drtg'], 1) if filtered.get('drtg') and baseline.get('drtg') else None,
        'net': round(filtered['net'] - baseline['net'], 1) if filtered.get('net') and baseline.get('net') else None,
    }


ARCHETYPE_LABELS = {
    'big': 'BIG LINEUP', 'shooters': 'SHOOTING LINEUP', 'smallball': 'SMALL-BALL LINEUP',
}


def _get_counter(baseline, all_rows):
    if not baseline.get('net'):
        return None

    worst_delta = 0.0
    worst_filter = None
    worst_row = None

    for fname in ['big', 'shooters', 'smallball']:
        row = all_rows.get(fname)
        if not row or row.possessions < 50 or row.net is None:
            continue
        delta = float(row.net) - baseline['net']
        if delta < worst_delta:
            worst_delta = delta
            worst_filter = fname
            worst_row = row

    if worst_filter is None or worst_delta > -2:
        return None

    return {
        'archetype': ARCHETYPE_LABELS[worst_filter],
        'filter': worst_filter,
        'delta': round(worst_delta, 1),
        'filtered_net': float(worst_row.net),
        'possessions': worst_row.possessions,
    }
