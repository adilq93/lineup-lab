"""
Pre-compute trio stats using raw SQL for performance.
One pass per team × filter context, aggregating all trios in a single query.
"""
from itertools import combinations

from django.core.management.base import BaseCommand
from django.db.models import Q

from ingestion.models import Game, PBPEvent, TrioStat
from analytics.engines.filter_engine import FILTER_MAP  # noqa: kept for reference

OPPONENT_TEAMS = [
    (1610612743, "Denver Nuggets"),
    (1610612760, "OKC Thunder"),
    (1610612759, "San Antonio Spurs"),
    (1610612750, "Minnesota Timberwolves"),
    (1610612745, "Houston Rockets"),
]

MIN_TRIO_POSSESSIONS = 100
# For each filter, define the absolute flag to use when team is home vs away.
# "big" = opponent has 2+ bigs. If trio is home, opponent is away → away_is_big.
ABSOLUTE_FILTERS = {
    'big':       {'home': {'away_is_big': True},       'away': {'home_is_big': True}},
    'shooters':  {'home': {'away_is_shooter': True},   'away': {'home_is_shooter': True}},
    'smallball': {'home': {'away_is_smallball': True},  'away': {'home_is_smallball': True}},
    'clutch':    {'home': {'is_clutch': True},          'away': {'is_clutch': True}},
}
FILTER_NAMES = ['baseline'] + list(ABSOLUTE_FILTERS.keys())


class Command(BaseCommand):
    help = "Pre-compute all trio stats using fast SQL aggregation"

    def handle(self, *args, **options):
        for team_id, team_name in OPPONENT_TEAMS:
            self.stdout.write(f"\n=== {team_name} ({team_id}) ===")
            self._compute_team(team_id, team_name)

        total = TrioStat.objects.count()
        self.stdout.write(f"\nDone. {total} total trio_stat rows.")

    def _compute_team(self, team_id, team_name):
        # Get all game IDs for this team
        game_ids = list(
            Game.objects.filter(
                Q(home_team_id=team_id) | Q(away_team_id=team_id),
                lineups_computed=True,
            ).values_list('game_id', flat=True)
        )
        if not game_ids:
            self.stdout.write(f"  No games.")
            return

        # Separate home/away game IDs
        home_ids = set(Game.objects.filter(game_id__in=game_ids, home_team_id=team_id).values_list('game_id', flat=True))
        away_ids = set(Game.objects.filter(game_id__in=game_ids, away_team_id=team_id).values_list('game_id', flat=True))

        # Collect all unique player IDs from lineups
        player_ids = set()
        for lineup in PBPEvent.objects.filter(game_id__in=home_ids, home_lineup__isnull=False).values_list('home_lineup', flat=True).distinct()[:5000]:
            if lineup:
                player_ids.update(lineup)
        for lineup in PBPEvent.objects.filter(game_id__in=away_ids, away_lineup__isnull=False).values_list('away_lineup', flat=True).distinct()[:5000]:
            if lineup:
                player_ids.update(lineup)

        combos = list(combinations(sorted(player_ids), 3))
        self.stdout.write(f"  {len(player_ids)} players → {len(combos)} combos")

        # Clear old data
        TrioStat.objects.filter(team_id=team_id).delete()

        # For each filter context, aggregate all trios
        for filter_name in FILTER_NAMES:
            self.stdout.write(f"  Computing {filter_name}...")

            if filter_name == 'baseline':
                home_kwargs = {}
                away_kwargs = {}
            else:
                home_kwargs = ABSOLUTE_FILTERS[filter_name]['home']
                away_kwargs = ABSOLUTE_FILTERS[filter_name]['away']

            rows = []
            for trio in combos:
                stats = self._compute_fast(trio, team_id, home_ids, away_ids, home_kwargs, away_kwargs)
                if stats is None:
                    continue

                poss_threshold = MIN_TRIO_POSSESSIONS if filter_name == 'baseline' else 0
                if stats['possessions'] < poss_threshold:
                    continue

                trio_key = '_'.join(str(pid) for pid in trio)
                rows.append(TrioStat(
                    trio_key=trio_key,
                    team_id=team_id,
                    filter_name=filter_name,
                    player1_id=trio[0],
                    player2_id=trio[1],
                    player3_id=trio[2],
                    possessions=stats['possessions'],
                    ortg=stats['ortg'],
                    drtg=stats['drtg'],
                    net=stats['net'],
                    pts=stats['pts'],
                    fga=stats['fga'],
                    fgm=stats['fgm'],
                    fg_pct=stats['fgPct'],
                    fg3m=stats['fg3m'],
                    fta=stats['fta'],
                    oreb=stats['oreb'],
                    tov=stats['tov'],
                ))

            if filter_name != 'baseline':
                baseline_keys = set(
                    TrioStat.objects.filter(team_id=team_id, filter_name='baseline')
                    .values_list('trio_key', flat=True)
                )
                rows = [r for r in rows if r.trio_key in baseline_keys]

            TrioStat.objects.bulk_create(rows, batch_size=500)
            self.stdout.write(f"    → {len(rows)} rows")

    def _compute_fast(self, trio, team_id, home_ids, away_ids, home_kwargs, away_kwargs):
        """Single-trio aggregation using absolute flags for both offense and defense."""
        trio_list = list(trio)

        # Absolute flags apply to ALL events in a moment — both teams see same flags
        home_qs = PBPEvent.objects.filter(
            game_id__in=home_ids,
            home_lineup__contains=trio_list,
            **home_kwargs,
        )
        away_qs = PBPEvent.objects.filter(
            game_id__in=away_ids,
            away_lineup__contains=trio_list,
            **away_kwargs,
        )

        # Offensive aggregation (team's own events)
        off = _sum_tuples(self._agg(home_qs.filter(team_id=team_id)), self._agg(away_qs.filter(team_id=team_id)))

        fga  = off[0]
        fgm  = off[1]
        fg3m = off[2]
        oreb = off[3]
        tov  = off[4]
        fta  = off[5]
        pts  = off[6]

        poss = fga - oreb + tov + (0.44 * fta)
        if poss <= 0:
            return None

        ortg = round((pts / poss) * 100, 1)
        fg_pct = round((fgm / fga) * 100, 1) if fga > 0 else 0

        # Defensive aggregation — absolute flags apply to all events in a moment,
        # so both teams' events match the same filter. Use the same filtered qs.
        d = _sum_tuples(
            self._agg(home_qs.filter(team_id__isnull=False).exclude(team_id=team_id)),
            self._agg(away_qs.filter(team_id__isnull=False).exclude(team_id=team_id)),
        )

        d_poss = d[0] - d[3] + d[4] + (0.44 * d[5])
        drtg = round((d[6] / d_poss) * 100, 1) if d_poss > 0 else None
        net = round(ortg - drtg, 1) if drtg is not None else None

        return {
            'possessions': int(poss),
            'ortg': ortg, 'drtg': drtg, 'net': net,
            'pts': pts, 'fga': fga, 'fgm': fgm,
            'fgPct': fg_pct, 'fg3m': fg3m,
            'fta': fta, 'oreb': oreb, 'tov': tov,
        }

    def _agg(self, qs):
        """Return (fga, fgm, fg3m, oreb, tov, fta, pts) as a tuple for summing."""
        from django.db.models import Sum, Count, Q as DQ

        r = qs.aggregate(
            fga=Count('event_id', filter=DQ(event_msg_type=1)),
            fgm=Count('event_id', filter=DQ(event_msg_type=1, points_scored__gt=0)),
            fg3m=Count('event_id', filter=DQ(event_msg_type=1, points_scored=3)),
            oreb=Count('event_id', filter=DQ(event_msg_type=4, sub_type='offensive')),
            tov=Count('event_id', filter=DQ(event_msg_type=5)),
            fta=Count('event_id', filter=DQ(event_msg_type=3)),
            pts=Sum('points_scored'),
        )
        return (
            r['fga'] or 0,
            r['fgm'] or 0,
            r['fg3m'] or 0,
            r['oreb'] or 0,
            r['tov'] or 0,
            r['fta'] or 0,
            r['pts'] or 0,
        )


def _sum_tuples(a, b):
    return tuple(x + y for x, y in zip(a, b))
