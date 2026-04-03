from typing import Optional

from django.core.management.base import BaseCommand
from nba_api.stats.endpoints import (
    commonteamroster,
    commonplayerinfo,
    playerdashboardbygeneralsplits,
)

from ingestion import nba_client
from ingestion.models import Player, PlayerSeasonStats

TEAMS = [
    (1610612743, "Denver Nuggets"),
    (1610612760, "OKC Thunder"),
    (1610612759, "San Antonio Spurs"),
    (1610612750, "Minnesota Timberwolves"),
    (1610612745, "Houston Rockets"),
    (1610612747, "LA Lakers"),
]

SEASON = "2025-26"


def _parse_height(height_str: str) -> Optional[int]:
    """Parse '6-10' → 82 inches, '5-11' → 71 inches."""
    if not height_str:
        return None
    try:
        feet, inches = height_str.split("-")
        return int(feet) * 12 + int(inches)
    except (ValueError, AttributeError):
        return None


class Command(BaseCommand):
    help = "Fetch height and 3P% for all players on tracked team rosters"

    def handle(self, *args, **options):
        for team_id, team_name in TEAMS:
            self.stdout.write(f"Fetching roster for {team_name}...")
            self._process_team(team_id)

    def _process_team(self, team_id: int) -> None:
        data = nba_client.fetch(
            "common_team_roster",
            team_id,
            commonteamroster.CommonTeamRoster,
            team_id=team_id,
        )
        for row in data.get("CommonTeamRoster", []):
            self._process_player(row["PLAYER_ID"], row["PLAYER"], team_id)

    def _process_player(
        self, player_id: int, full_name: str, team_id: int
    ) -> None:
        info_data = nba_client.fetch(
            "common_player_info",
            player_id,
            commonplayerinfo.CommonPlayerInfo,
            player_id=player_id,
        )
        info_rows = info_data.get("CommonPlayerInfo", [])
        if info_rows:
            row = info_rows[0]
            height_inches = _parse_height(row.get("HEIGHT", ""))
            position = row.get("POSITION") or None
        else:
            height_inches = None
            position = None

        Player.objects.update_or_create(
            player_id=player_id,
            defaults={
                "full_name": full_name,
                "team_id": team_id,
                "height_inches": height_inches,
                "position": position,
                "is_active": True,
            },
        )

        stats_data = nba_client.fetch(
            "player_dashboard_general",
            f"{player_id}_{SEASON}",
            playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits,
            player_id=player_id,
            season=SEASON,
        )
        dashboard = stats_data.get("OverallPlayerDashboard", [])
        if dashboard:
            row = dashboard[0]
            three_pct = row.get("FG3_PCT")
            three_att = row.get("FG3A")
        else:
            three_pct = None
            three_att = None

        PlayerSeasonStats.objects.update_or_create(
            player_id=player_id,
            season=SEASON,
            defaults={
                "three_point_pct": three_pct,
                "three_point_att": three_att,
            },
        )
