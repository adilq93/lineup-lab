"""
Thin client for fetching NBA stats from the nba_api package.
All methods return plain Python dicts/lists — no Django models here.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
}
_RETRY_DELAYS = [5, 15, 60]
_SLEEP = 2.0
_CACHE_ROOT = Path("data/raw")


def fetch(endpoint_name: str, id, nba_api_callable, **kwargs) -> dict:
    """
    Fetch an NBA API endpoint with caching, rate-limiting, and retry logic.

    - Reads from data/raw/{endpoint_name}/{id}.json if it exists.
    - Sleeps 2s before every live API call.
    - Retries on any exception at 5s → 15s → 60s, then raises.
    - Spoof User-Agent and Referer via nba_api's header config.
    """
    cache_path = _CACHE_ROOT / endpoint_name / f"{id}.json"

    if cache_path.exists():
        logger.debug("Cache hit: %s", cache_path)
        with cache_path.open() as fh:
            return json.load(fh)

    _inject_headers()

    time.sleep(_SLEEP)

    # 4 attempts: after each failure sleep 5s, 15s, 60s; then raise on the 4th failure
    retry_delays = _RETRY_DELAYS + [None]
    last_exc: Exception | None = None
    for attempt_num, sleep_after in enumerate(retry_delays, start=1):
        try:
            result = nba_api_callable(**kwargs)
            data: dict = result.get_normalized_dict()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with cache_path.open("w") as fh:
                json.dump(data, fh)
            return data
        except Exception as exc:
            last_exc = exc
            logger.error("Attempt %d failed for %s/%s: %s", attempt_num, endpoint_name, id, exc)
            if sleep_after is None:
                break
            time.sleep(sleep_after)

    raise last_exc  # type: ignore[misc]


def _inject_headers() -> None:
    """Push spoofed headers into nba_api's HTTP layer if available."""
    try:
        from nba_api.library import http as nba_http  # type: ignore
        nba_http.STATS_HEADERS.update(_HEADERS)
    except Exception:
        pass


def get_roster(team_id: int) -> list[dict]:
    """Return current roster for a team as a list of player dicts."""
    try:
        from nba_api.stats.endpoints import commonteamroster  # type: ignore
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        return roster.get_normalized_dict()["CommonTeamRoster"]
    except Exception as exc:
        logger.error("Failed to fetch roster for team %s: %s", team_id, exc)
        return []


def get_player_game_log(player_id: int, season: str = "2025-26") -> list[dict]:
    """Return game log entries for a player in the given season."""
    try:
        from nba_api.stats.endpoints import playergamelog  # type: ignore
        log = playergamelog.PlayerGameLog(player_id=player_id, season=season)
        return log.get_normalized_dict()["PlayerGameLog"]
    except Exception as exc:
        logger.error("Failed to fetch game log for player %s: %s", player_id, exc)
        return []
