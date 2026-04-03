"""
Thin client for fetching NBA stats from the nba_api package.
All methods return plain Python dicts/lists — no Django models here.
"""

import logging

logger = logging.getLogger(__name__)


def get_roster(team_id: int) -> list[dict]:
    """Return current roster for a team as a list of player dicts."""
    try:
        from nba_api.stats.endpoints import commonteamroster  # type: ignore
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        return roster.get_normalized_dict()["CommonTeamRoster"]
    except Exception as exc:
        logger.error("Failed to fetch roster for team %s: %s", team_id, exc)
        return []


def get_player_game_log(player_id: int, season: str = "2024-25") -> list[dict]:
    """Return game log entries for a player in the given season."""
    try:
        from nba_api.stats.endpoints import playergamelog  # type: ignore
        log = playergamelog.PlayerGameLog(player_id=player_id, season=season)
        return log.get_normalized_dict()["PlayerGameLog"]
    except Exception as exc:
        logger.error("Failed to fetch game log for player %s: %s", player_id, exc)
        return []
