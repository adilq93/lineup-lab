import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from ingestion.models import Game, PBPEvent

# Map live API actionType → our event_type string and a numeric msg_type
# msg_type mirrors the old NBA stats codes so downstream logic still works
ACTION_MAP = {
    '2pt':          ('SHOT',         1),
    '3pt':          ('SHOT',         1),
    'freethrow':    ('FREE_THROW',   3),
    'rebound':      ('REBOUND',      4),
    'turnover':     ('TURNOVER',     5),
    'foul':         ('FOUL',         6),
    'substitution': ('SUBSTITUTION', 8),
    'period':       ('PERIOD_START', 12),
}

CACHE_ROOT = Path('data/raw/play_by_play_live')


class Command(BaseCommand):
    help = 'Fetch play-by-play for all games not yet processed (live API)'

    def handle(self, *args, **options):
        games = Game.objects.filter(pbp_fetched=False).order_by('game_date')
        total = games.count()
        self.stdout.write(f'Found {total} games needing PBP fetch.')

        for i, game in enumerate(games, 1):
            self.stdout.write(
                f'[{i}/{total}] Processing PBP for game {game.game_id} ({game.game_date})...'
            )
            try:
                self._fetch_game(game)
            except Exception as exc:
                self.stderr.write(f'  ERROR on {game.game_id}: {exc}')

    def _fetch_game(self, game: Game) -> None:
        import time
        actions = self._get_actions(game.game_id)
        events = []

        for action in actions:
            action_type = action.get('actionType', '')
            event_type, msg_type = ACTION_MAP.get(action_type, ('OTHER', 0))

            clock_seconds = _parse_clock(action.get('clock', ''))
            score_home = _parse_score_int(action.get('scoreHome'))
            score_away = _parse_score_int(action.get('scoreAway'))
            score_margin = (score_home - score_away) if (score_home is not None and score_away is not None) else None
            points = _derive_points(action_type, action)
            team_id = action.get('teamId') or None
            player_id = action.get('personId') or None
            if player_id == 0:
                player_id = None

            events.append(PBPEvent(
                game=game,
                period=action.get('period', 0),
                clock_seconds=clock_seconds,
                event_type=event_type,
                sub_type=action.get('subType') or None,
                event_msg_type=msg_type,
                team_id=team_id,
                player_id=player_id,
                points_scored=points,
                score_home=score_home,
                score_away=score_away,
                score_margin=score_margin,
            ))

        PBPEvent.objects.bulk_create(events, batch_size=500)
        game.pbp_fetched = True
        game.save(update_fields=['pbp_fetched'])

    def _get_actions(self, game_id: str) -> list:
        cache_file = CACHE_ROOT / f'{game_id}.json'

        if cache_file.exists():
            with cache_file.open() as f:
                return json.load(f)

        import time
        from nba_api.live.nba.endpoints import playbyplay
        time.sleep(1.0)  # live API is more lenient — 1s is sufficient

        r = playbyplay.PlayByPlay(game_id=game_id, timeout=60)
        actions = r.get_dict().get('game', {}).get('actions', [])

        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with cache_file.open('w') as f:
            json.dump(actions, f)

        return actions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_clock(clock_str: str) -> int:
    """Parse ISO 8601 duration 'PT12M00.00S' → total seconds remaining."""
    if not clock_str:
        return 0
    m = re.match(r'PT(\d+)M([\d.]+)S', clock_str)
    if not m:
        return 0
    minutes = int(m.group(1))
    seconds = int(float(m.group(2)))
    return minutes * 60 + seconds


def _parse_score_int(val):
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _derive_points(action_type: str, action: dict) -> int:
    if action_type == '3pt':
        desc = action.get('description', '').upper()
        if 'MISS' not in desc:
            return 3
    if action_type == '2pt':
        desc = action.get('description', '').upper()
        if 'MISS' not in desc:
            return 2
    if action_type == 'freethrow':
        desc = action.get('description', '').upper()
        if 'MISS' not in desc:
            return 1
    return 0
