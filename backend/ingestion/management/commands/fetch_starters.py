"""
Fetches box score starters for all games and caches them locally.
Used by compute_lineups to get accurate starting lineups.
"""
import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from ingestion.models import Game

CACHE_ROOT = Path('data/raw/starters')


class Command(BaseCommand):
    help = 'Fetch starting lineups from box scores for all games'

    def handle(self, *args, **options):
        games = Game.objects.filter(pbp_fetched=True).order_by('game_date')
        total = games.count()
        self.stdout.write(f'Fetching starters for {total} games...')

        for i, game in enumerate(games, 1):
            cache_file = CACHE_ROOT / f'{game.game_id}.json'
            if cache_file.exists():
                continue

            try:
                from nba_api.live.nba.endpoints import boxscore
                time.sleep(0.5)
                r = boxscore.BoxScore(game_id=game.game_id, timeout=60)
                data = r.get_dict().get('game', {})

                starters = {}
                for side in ['homeTeam', 'awayTeam']:
                    team = data.get(side, {})
                    team_id = team.get('teamId')
                    if team_id:
                        starter_ids = [
                            p['personId']
                            for p in team.get('players', [])
                            if str(p.get('starter')) == '1'
                        ]
                        starters[str(team_id)] = starter_ids

                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with cache_file.open('w') as f:
                    json.dump(starters, f)

                if i % 20 == 0:
                    self.stdout.write(f'  [{i}/{total}] done')

            except Exception as exc:
                self.stderr.write(f'  ERROR on {game.game_id}: {exc}')

        self.stdout.write('Done fetching starters.')
