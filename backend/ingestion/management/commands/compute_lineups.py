import json
from pathlib import Path
from statistics import median

from django.core.management.base import BaseCommand
from django.db import transaction

from ingestion.models import Game, PBPEvent, Player, PlayerSeasonStats

STARTERS_CACHE = Path('data/raw/starters')

SEASON = "2025-26"
MIN_HEIGHT_BIG = 82        # 6'10"
MIN_HEIGHT_SMALLBALL = 81  # 6'9" — smallball means NO player >= this
MIN_SHOOTERS = 3
SHOOTER_PCT_THRESHOLD = 0.350
SHOOTER_ATT_THRESHOLD = 82
CLUTCH_SECONDS = 300       # 5 minutes
CLUTCH_MARGIN = 5
LOW_CONF_THRESHOLD = 0.02  # 2% of events

UPDATE_FIELDS = [
    'home_lineup', 'away_lineup',
    'opp_is_big_lineup', 'opp_is_shooter_lineup', 'opp_is_smallball',
    'is_clutch', 'is_fast_game', 'is_slow_game',
    'home_is_big', 'away_is_big',
    'home_is_shooter', 'away_is_shooter',
    'home_is_smallball', 'away_is_smallball',
]


class Command(BaseCommand):
    help = "Reconstruct lineup state and tag boolean filter flags for all games"

    def handle(self, *args, **options):
        # Pre-load all player heights and 3P stats into memory once
        heights = dict(Player.objects.values_list('player_id', 'height_inches'))
        shooter_ids = set(
            PlayerSeasonStats.objects.filter(
                season=SEASON,
                three_point_pct__gte=SHOOTER_PCT_THRESHOLD,
                three_point_att__gte=SHOOTER_ATT_THRESHOLD,
            ).values_list('player_id', flat=True)
        )

        # Compute season-median pace per team
        team_median_pace = _compute_team_median_pace()

        games = Game.objects.filter(pbp_fetched=True, lineups_computed=False).order_by('game_date')
        total = games.count()
        self.stdout.write(f"Found {total} games needing lineup reconstruction.")

        for i, game in enumerate(games, 1):
            self.stdout.write(
                f"[{i}/{total}] Reconstructing lineups for {game.game_id} ({game.game_date})..."
            )
            try:
                self._process_game(game, heights, shooter_ids, team_median_pace)
            except Exception as exc:
                self.stderr.write(f"  ERROR on {game.game_id}: {exc}")

    def _process_game(
        self,
        game: Game,
        heights: dict,
        shooter_ids: set,
        team_median_pace: dict,
    ) -> None:
        events = list(
            game.pbp_events
            .order_by('period', '-clock_seconds', 'event_id')
            .values(
                'event_id', 'period', 'clock_seconds', 'event_type',
                'event_msg_type', 'sub_type', 'team_id', 'player_id',
                'score_margin',
            )
        )

        if not events:
            game.lineups_computed = True
            game.save(update_fields=['lineups_computed'])
            return

        home_id = game.home_team_id
        away_id = game.away_team_id

        box_starters = _load_box_starters(game.game_id)
        home_lineup: set = set(box_starters.get(str(home_id), [])) or _infer_starters(events, home_id)
        away_lineup: set = set(box_starters.get(str(away_id), [])) or _infer_starters(events, away_id)

        game_pace = float(game.pace) if game.pace else None

        low_conf_count = 0
        updates = []

        for event in events:
            # Period start: re-infer starters if confidence is low
            if event['event_msg_type'] == 12:
                if len(home_lineup) != 5 or len(away_lineup) != 5:
                    home_lineup = _infer_starters_from_period(events, home_id, event['period'])
                    away_lineup = _infer_starters_from_period(events, away_id, event['period'])

            # Substitution: update lineup using sub_type (in/out)
            if event['event_msg_type'] == 8 and event['team_id'] and event['player_id']:
                lineup = home_lineup if event['team_id'] == home_id else away_lineup
                if event['sub_type'] == 'out':
                    lineup.discard(event['player_id'])
                elif event['sub_type'] == 'in':
                    lineup.add(event['player_id'])

            # Don't count confidence during substitution events — out/in pairs
            # briefly leave the lineup at 4 between the two events
            is_sub_event = event['event_msg_type'] == 8
            valid = len(home_lineup) == 5 and len(away_lineup) == 5
            if not valid and not is_sub_event:
                low_conf_count += 1

            home_snap = sorted(home_lineup)
            away_snap = sorted(away_lineup)

            # Determine opponent lineup from the perspective of the event's team
            if event['team_id'] == home_id:
                opp_lineup = away_snap
            else:
                opp_lineup = home_snap

            # Team-relative flags (kept for backwards compat)
            opp_is_big = _count_bigs(opp_lineup, heights) >= 2
            opp_is_shooter = _count_shooters(opp_lineup, shooter_ids) >= MIN_SHOOTERS
            opp_is_small = _max_height(opp_lineup, heights) < MIN_HEIGHT_SMALLBALL if opp_lineup else False
            is_clutch = (
                event['period'] >= 4
                and event['clock_seconds'] <= CLUTCH_SECONDS
                and event['score_margin'] is not None
                and abs(event['score_margin']) <= CLUTCH_MARGIN
            )

            # Pace flags
            tracked_team = home_id if event['team_id'] == home_id else away_id
            team_median = team_median_pace.get(tracked_team)
            is_fast = bool(game_pace and team_median and game_pace > team_median)
            is_slow = bool(game_pace and team_median and game_pace < team_median)

            # Absolute flags — same value on ALL events in this moment
            h_big = _count_bigs(home_snap, heights) >= 2
            a_big = _count_bigs(away_snap, heights) >= 2
            h_shooter = _count_shooters(home_snap, shooter_ids) >= MIN_SHOOTERS
            a_shooter = _count_shooters(away_snap, shooter_ids) >= MIN_SHOOTERS
            h_small = _max_height(home_snap, heights) < MIN_HEIGHT_SMALLBALL if home_snap else False
            a_small = _max_height(away_snap, heights) < MIN_HEIGHT_SMALLBALL if away_snap else False

            updates.append({
                'event_id': event['event_id'],
                'home_lineup': home_snap,
                'away_lineup': away_snap,
                'opp_is_big_lineup': opp_is_big,
                'opp_is_shooter_lineup': opp_is_shooter,
                'opp_is_smallball': opp_is_small,
                'is_clutch': is_clutch,
                'is_fast_game': is_fast,
                'is_slow_game': is_slow,
                'home_is_big': h_big,
                'away_is_big': a_big,
                'home_is_shooter': h_shooter,
                'away_is_shooter': a_shooter,
                'home_is_smallball': h_small,
                'away_is_smallball': a_small,
            })

        low_conf_pct = low_conf_count / len(events) if events else 0
        self.stdout.write(
            f"  {game.game_id}: {100*(1-low_conf_pct):.1f}% confidence "
            f"({low_conf_count} low-conf events out of {len(events)})"
        )

        if low_conf_pct > LOW_CONF_THRESHOLD:
            game.low_confidence_reconstruction = True
            self.stdout.write(f"  WARNING: {game.game_id} flagged low confidence — skipping flag tagging")
            game.lineups_computed = True
            game.save(update_fields=['low_confidence_reconstruction', 'lineups_computed'])
            return

        # Bulk update all events
        with transaction.atomic():
            for chunk in _chunks(updates, 500):
                event_ids = [u['event_id'] for u in chunk]
                events_qs = PBPEvent.objects.filter(event_id__in=event_ids)
                event_map = {e.event_id: e for e in events_qs}
                for u in chunk:
                    obj = event_map.get(u['event_id'])
                    if obj:
                        for field in UPDATE_FIELDS:
                            setattr(obj, field, u[field])
                PBPEvent.objects.bulk_update(
                    list(event_map.values()),
                    fields=UPDATE_FIELDS,
                    batch_size=500,
                )

        game.lineups_computed = True
        game.save(update_fields=['lineups_computed'])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_box_starters(game_id: str) -> dict:
    """Load starters dict {team_id_str: [player_id, ...]} from box score cache."""
    cache_file = STARTERS_CACHE / f'{game_id}.json'
    if cache_file.exists():
        with cache_file.open() as f:
            return json.load(f)
    return {}


def _infer_starters(events: list, team_id: int) -> set:
    """Infer starting 5 from first period-1 events before first SUB."""
    return _infer_starters_from_period(events, team_id, period=1)


def _infer_starters_from_period(events: list, team_id: int, period: int) -> set:
    """
    Collect the first 5 distinct player_ids for a team in the given period.
    Scans non-substitution events only (subs change the lineup, so we want
    the players who were already on the floor before any sub).
    If fewer than 5 found before first sub, fall back to scanning all events
    until 5 are collected.
    """
    players: set = set()

    # Pass 1: only non-sub events before first sub
    for event in events:
        if event['period'] != period:
            continue
        if event['team_id'] != team_id:
            continue
        if event['event_msg_type'] == 8:
            break
        if event['player_id']:
            players.add(event['player_id'])
        if len(players) == 5:
            return players

    # Pass 2: fallback — scan all events in period ignoring subs
    if len(players) < 5:
        for event in events:
            if event['period'] != period:
                continue
            if event['team_id'] != team_id:
                continue
            if event['event_msg_type'] == 8:
                continue
            if event['player_id']:
                players.add(event['player_id'])
            if len(players) == 5:
                break

    return players



def _compute_team_median_pace() -> dict:
    """Return {team_id: median_pace} for all teams with game data."""
    from django.db.models import Q
    all_games = Game.objects.filter(pace__isnull=False, season=SEASON)
    team_paces: dict = {}
    for game in all_games:
        pace = float(game.pace)
        for tid in [game.home_team_id, game.away_team_id]:
            if tid not in team_paces:
                team_paces[tid] = []
            team_paces[tid].append(pace)
    return {tid: median(paces) for tid, paces in team_paces.items() if paces}


def _count_bigs(lineup: list, heights: dict) -> int:
    return sum(1 for pid in lineup if (heights.get(pid) or 0) >= MIN_HEIGHT_BIG)


def _count_shooters(lineup: list, shooter_ids: set) -> int:
    return sum(1 for pid in lineup if pid in shooter_ids)


def _max_height(lineup: list, heights: dict) -> int:
    vals = [heights.get(pid) or 0 for pid in lineup]
    return max(vals) if vals else 0


def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
