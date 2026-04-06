from django.core.management.base import BaseCommand
from nba_api.stats.endpoints import leaguegamefinder

from ingestion import nba_client
from ingestion.models import Game

OPPONENT_TEAMS = [
    (1610612743, "Denver Nuggets"),
    (1610612760, "OKC Thunder"),
    (1610612759, "San Antonio Spurs"),
    (1610612750, "Minnesota Timberwolves"),
    (1610612745, "Houston Rockets"),
]

SEASON = "2025-26"


class Command(BaseCommand):
    help = "Fetch 2025-26 regular season game IDs for all 5 opponent teams"

    def handle(self, *args, **options):
        for team_id, team_name in OPPONENT_TEAMS:
            self._fetch_team_games(team_id, team_name)

    def _fetch_team_games(self, team_id: int, team_name: str) -> None:
        # Incremental: only fetch games after the latest we already have
        latest = (
            Game.objects.filter(home_team_id=team_id) |
            Game.objects.filter(away_team_id=team_id)
        ).order_by('-game_date').values_list('game_date', flat=True).first()

        data = nba_client.fetch(
            "league_game_finder",
            f"{team_id}_{SEASON}",
            leaguegamefinder.LeagueGameFinder,
            team_id_nullable=team_id,
            season_nullable=SEASON,
            season_type_nullable="Regular Season",
        )

        rows = data.get("LeagueGameFinderResults", [])
        new_count = 0

        for row in rows:
            game_id = row.get("GAME_ID")
            game_date_str = row.get("GAME_DATE")  # "2025-10-22"
            if not game_id or not game_date_str:
                continue

            # Skip games already in DB
            if latest and game_date_str <= str(latest):
                continue

            home_team_id, away_team_id = _parse_matchup(row.get("MATCHUP", ""), team_id)

            _, created = Game.objects.get_or_create(
                game_id=game_id,
                defaults={
                    "game_date": game_date_str,
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "season": SEASON,
                },
            )
            if created:
                new_count += 1

        latest_date = rows[0].get("GAME_DATE", "?") if rows else "?"
        self.stdout.write(
            f"Fetched {new_count} new games for {team_name} (latest: {latest_date})"
        )


def _parse_matchup(matchup: str, team_id: int) -> tuple[int, int]:
    """
    MATCHUP looks like 'DEN vs. LAL' (home) or 'DEN @ LAL' (away).
    Since we only have team_id, not the opponent's id from this row,
    we store team_id in the correct home/away slot and 0 as placeholder.
    The opponent id will be filled when that team's games are fetched,
    or left as 0 (acceptable for Phase 1 — trio engine only needs game_id).
    """
    if " vs. " in matchup:
        return team_id, 0   # team is home
    return 0, team_id       # team is away
