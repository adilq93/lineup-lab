import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from ingestion.models import Game, PBPEvent, Player, PlayerSeasonStats
from ingestion import nba_client
from ingestion.management.commands.fetch_players import _parse_height


class PlayerModelTest(TestCase):
    def test_create_minimal(self):
        p = Player.objects.create(player_id=2544, full_name="LeBron James")
        self.assertEqual(p.player_id, 2544)
        self.assertTrue(p.is_active)
        self.assertIsNone(p.team_id)
        self.assertIsNone(p.height_inches)
        self.assertIsNone(p.position)

    def test_primary_key(self):
        Player.objects.create(player_id=2544, full_name="LeBron James")
        with self.assertRaises(Exception):
            Player.objects.create(player_id=2544, full_name="Duplicate")

    def test_full_fields(self):
        p = Player.objects.create(
            player_id=1,
            full_name="Anthony Davis",
            team_id=1610612747,
            height_inches=82,
            position="C",
            is_active=True,
        )
        self.assertEqual(p.height_inches, 82)
        self.assertEqual(p.position, "C")


class PlayerSeasonStatsModelTest(TestCase):
    def setUp(self):
        self.player = Player.objects.create(player_id=2544, full_name="LeBron James")

    def test_create(self):
        s = PlayerSeasonStats.objects.create(
            player=self.player,
            season="2025-26",
            three_point_pct=Decimal("0.380"),
            three_point_att=200,
        )
        self.assertEqual(s.season, "2025-26")
        self.assertEqual(s.three_point_att, 200)

    def test_unique_together(self):
        PlayerSeasonStats.objects.create(player=self.player, season="2025-26")
        with self.assertRaises(Exception):
            PlayerSeasonStats.objects.create(player=self.player, season="2025-26")

    def test_nullable_stats(self):
        s = PlayerSeasonStats.objects.create(player=self.player, season="2024-25")
        self.assertIsNone(s.three_point_pct)
        self.assertIsNone(s.three_point_att)


class GameModelTest(TestCase):
    def test_create(self):
        g = Game.objects.create(
            game_id="0022401001",
            game_date="2025-01-15",
            home_team_id=1610612747,
            away_team_id=1610612738,
            season="2024-25",
        )
        self.assertFalse(g.low_confidence_reconstruction)
        self.assertIsNone(g.pace)
        self.assertIsNotNone(g.ingested_at)

    def test_primary_key(self):
        Game.objects.create(
            game_id="0022401001",
            game_date="2025-01-15",
            home_team_id=1,
            away_team_id=2,
            season="2024-25",
        )
        with self.assertRaises(Exception):
            Game.objects.create(
                game_id="0022401001",
                game_date="2025-01-15",
                home_team_id=1,
                away_team_id=2,
                season="2024-25",
            )


class PBPEventModelTest(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            game_id="0022401001",
            game_date="2025-01-15",
            home_team_id=1610612747,
            away_team_id=1610612738,
            season="2024-25",
        )

    def test_create_minimal(self):
        e = PBPEvent.objects.create(
            game=self.game,
            period=1,
            clock_seconds=600,
            event_type="SHOT",
            event_msg_type=1,
        )
        self.assertEqual(e.points_scored, 0)
        self.assertIsNone(e.team_id)
        self.assertIsNone(e.home_lineup)
        self.assertIsNone(e.opp_is_big_lineup)

    def test_lineup_json(self):
        lineup = [2544, 1627742, 1629029, 1628384, 203076]
        e = PBPEvent.objects.create(
            game=self.game,
            period=2,
            clock_seconds=300,
            event_type="REBOUND",
            event_msg_type=4,
            home_lineup=lineup,
            away_lineup=lineup,
        )
        self.assertEqual(e.home_lineup, lineup)
        self.assertEqual(e.away_lineup, lineup)

    def test_bool_flags(self):
        e = PBPEvent.objects.create(
            game=self.game,
            period=4,
            clock_seconds=60,
            event_type="SHOT",
            event_msg_type=1,
            opp_is_big_lineup=True,
            opp_is_shooter_lineup=False,
            opp_is_smallball=None,
            is_clutch=True,
            is_fast_game=False,
            is_slow_game=None,
        )
        self.assertTrue(e.opp_is_big_lineup)
        self.assertFalse(e.opp_is_shooter_lineup)
        self.assertIsNone(e.opp_is_smallball)
        self.assertTrue(e.is_clutch)

    def test_score_fields(self):
        e = PBPEvent.objects.create(
            game=self.game,
            period=3,
            clock_seconds=120,
            event_type="FT",
            event_msg_type=3,
            score_home=85,
            score_away=82,
            score_margin=3,
            points_scored=1,
        )
        self.assertEqual(e.score_margin, 3)


class NbaClientTest(TestCase):
    @patch("ingestion.nba_client.commonteamroster", create=True)
    def test_get_roster_returns_list_on_success(self, _mock):
        result = nba_client.get_roster(1610612747)
        self.assertIsInstance(result, list)

    @patch("ingestion.nba_client.playergamelog", create=True)
    def test_get_player_game_log_returns_list_on_success(self, _mock):
        result = nba_client.get_player_game_log(2544)
        self.assertIsInstance(result, list)

    def test_get_roster_handles_import_error(self):
        result = nba_client.get_roster(1610612747)
        self.assertEqual(result, [])

    def test_get_player_game_log_handles_import_error(self):
        result = nba_client.get_player_game_log(2544)
        self.assertEqual(result, [])


class FetchTest(TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_cache_root = nba_client._CACHE_ROOT
        nba_client._CACHE_ROOT = Path(self._tmpdir.name)

    def tearDown(self):
        nba_client._CACHE_ROOT = self._orig_cache_root
        self._tmpdir.cleanup()

    def _make_callable(self, data: dict):
        mock_result = MagicMock()
        mock_result.get_normalized_dict.return_value = data
        return MagicMock(return_value=mock_result)

    @patch("ingestion.nba_client.time.sleep")
    @patch("ingestion.nba_client._inject_headers")
    def test_fetch_calls_api_and_caches(self, _mock_headers, mock_sleep):
        data = {"players": [{"id": 1}]}
        callable_ = self._make_callable(data)

        result = nba_client.fetch("roster", 123, callable_, team_id=123)

        self.assertEqual(result, data)
        callable_.assert_called_once_with(team_id=123)
        mock_sleep.assert_called_once_with(nba_client._SLEEP)
        cache_file = nba_client._CACHE_ROOT / "roster" / "123.json"
        self.assertTrue(cache_file.exists())

    @patch("ingestion.nba_client.time.sleep")
    @patch("ingestion.nba_client._inject_headers")
    def test_fetch_reads_from_cache_on_second_call(self, _mock_headers, mock_sleep):
        data = {"cached": True}
        callable_ = self._make_callable(data)

        nba_client.fetch("gamelog", 99, callable_, player_id=99)
        callable_.reset_mock()
        mock_sleep.reset_mock()

        result = nba_client.fetch("gamelog", 99, callable_, player_id=99)
        self.assertEqual(result, data)
        callable_.assert_not_called()
        mock_sleep.assert_not_called()

    @patch("ingestion.nba_client.time.sleep")
    @patch("ingestion.nba_client._inject_headers")
    def test_fetch_retries_on_failure_then_succeeds(self, _mock_headers, mock_sleep):
        data = {"ok": True}
        good_result = MagicMock()
        good_result.get_normalized_dict.return_value = data
        callable_ = MagicMock(side_effect=[RuntimeError("err"), good_result])

        result = nba_client.fetch("pbp", 7, callable_)

        self.assertEqual(result, data)
        self.assertEqual(callable_.call_count, 2)
        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertIn(2.0, sleep_calls)
        self.assertIn(5, sleep_calls)

    @patch("ingestion.nba_client.time.sleep")
    @patch("ingestion.nba_client._inject_headers")
    def test_fetch_raises_after_all_retries(self, _mock_headers, mock_sleep):
        callable_ = MagicMock(side_effect=RuntimeError("always fails"))

        with self.assertRaises(RuntimeError):
            nba_client.fetch("endpoint", 1, callable_)

        self.assertEqual(callable_.call_count, 4)  # 1 try + 3 retries

    @patch("ingestion.nba_client.time.sleep")
    @patch("ingestion.nba_client._inject_headers")
    def test_fetch_retry_sleep_sequence(self, _mock_headers, mock_sleep):
        callable_ = MagicMock(side_effect=RuntimeError("fail"))

        with self.assertRaises(RuntimeError):
            nba_client.fetch("endpoint", 2, callable_)

        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        # initial 2.0s sleep + retry delays 5, 15, 60
        self.assertEqual(sleep_args, [2.0, 5, 15, 60])

    def test_fetch_uses_cache_file_from_disk(self):
        cached_data = {"from": "disk"}
        cache_file = nba_client._CACHE_ROOT / "test_ep" / "42.json"
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text(json.dumps(cached_data))

        callable_ = MagicMock()
        result = nba_client.fetch("test_ep", 42, callable_)

        self.assertEqual(result, cached_data)
        callable_.assert_not_called()


class ParseHeightTest(TestCase):
    def test_standard_height(self):
        self.assertEqual(_parse_height("6-10"), 82)

    def test_six_foot(self):
        self.assertEqual(_parse_height("6-0"), 72)

    def test_five_eleven(self):
        self.assertEqual(_parse_height("5-11"), 71)

    def test_empty_string(self):
        self.assertIsNone(_parse_height(""))

    def test_none_input(self):
        self.assertIsNone(_parse_height(None))

    def test_malformed_input(self):
        self.assertIsNone(_parse_height("tall"))


class FetchPlayersCommandTest(TestCase):
    def _make_fetch_side_effect(self, roster_data, player_info_data, dashboard_data):
        """Return a side_effect function that dispatches on endpoint_name."""
        def side_effect(endpoint_name, id_, callable_, **kwargs):
            if endpoint_name == "common_team_roster":
                return roster_data
            if endpoint_name == "common_player_info":
                return player_info_data
            if endpoint_name == "player_dashboard_general":
                return dashboard_data
            return {}
        return side_effect

    @patch("ingestion.management.commands.fetch_players.nba_client.fetch")
    def test_creates_player_and_stats(self, mock_fetch):
        mock_fetch.side_effect = self._make_fetch_side_effect(
            roster_data={"CommonTeamRoster": [{"PLAYER_ID": 2544, "PLAYER": "LeBron James"}]},
            player_info_data={"CommonPlayerInfo": [{"HEIGHT": "6-9", "POSITION": "F"}]},
            dashboard_data={"OverallPlayerDashboard": [{"FG3_PCT": 0.380, "FG3A": 200}]},
        )

        call_command("fetch_players")

        self.assertTrue(Player.objects.filter(player_id=2544).exists())
        p = Player.objects.get(player_id=2544)
        self.assertEqual(p.full_name, "LeBron James")
        self.assertEqual(p.height_inches, 81)
        self.assertEqual(p.position, "F")

        stats = PlayerSeasonStats.objects.get(player_id=2544, season="2025-26")
        self.assertAlmostEqual(float(stats.three_point_pct), 0.380, places=3)
        self.assertEqual(stats.three_point_att, 200)

    @patch("ingestion.management.commands.fetch_players.nba_client.fetch")
    def test_idempotent(self, mock_fetch):
        mock_fetch.side_effect = self._make_fetch_side_effect(
            roster_data={"CommonTeamRoster": [{"PLAYER_ID": 2544, "PLAYER": "LeBron James"}]},
            player_info_data={"CommonPlayerInfo": [{"HEIGHT": "6-9", "POSITION": "F"}]},
            dashboard_data={"OverallPlayerDashboard": [{"FG3_PCT": 0.380, "FG3A": 200}]},
        )

        call_command("fetch_players")
        call_command("fetch_players")

        self.assertEqual(Player.objects.filter(player_id=2544).count(), 1)
        self.assertEqual(
            PlayerSeasonStats.objects.filter(player_id=2544, season="2025-26").count(), 1
        )

    @patch("ingestion.management.commands.fetch_players.nba_client.fetch")
    def test_handles_missing_player_info(self, mock_fetch):
        mock_fetch.side_effect = self._make_fetch_side_effect(
            roster_data={"CommonTeamRoster": [{"PLAYER_ID": 9999, "PLAYER": "Unknown Player"}]},
            player_info_data={"CommonPlayerInfo": []},
            dashboard_data={"OverallPlayerDashboard": []},
        )

        call_command("fetch_players")

        p = Player.objects.get(player_id=9999)
        self.assertIsNone(p.height_inches)
        self.assertIsNone(p.position)
        stats = PlayerSeasonStats.objects.get(player_id=9999, season="2025-26")
        self.assertIsNone(stats.three_point_pct)
        self.assertIsNone(stats.three_point_att)

    @patch("ingestion.management.commands.fetch_players.nba_client.fetch")
    def test_prints_team_progress(self, mock_fetch):
        mock_fetch.return_value = {"CommonTeamRoster": [], "OverallPlayerDashboard": [], "CommonPlayerInfo": []}

        from io import StringIO
        out = StringIO()
        call_command("fetch_players", stdout=out)

        output = out.getvalue()
        self.assertIn("Fetching roster for Denver Nuggets...", output)
        self.assertIn("Fetching roster for LA Lakers...", output)

    @patch("ingestion.management.commands.fetch_players.nba_client.fetch")
    def test_processes_all_six_teams(self, mock_fetch):
        mock_fetch.return_value = {"CommonTeamRoster": [], "OverallPlayerDashboard": [], "CommonPlayerInfo": []}

        call_command("fetch_players")

        # 6 roster fetches, no player fetches since rosters are empty
        roster_calls = [
            c for c in mock_fetch.call_args_list if c.args[0] == "common_team_roster"
        ]
        self.assertEqual(len(roster_calls), 6)

    @patch("ingestion.management.commands.fetch_players.nba_client.fetch")
    def test_updates_existing_player(self, mock_fetch):
        Player.objects.create(player_id=2544, full_name="Old Name", height_inches=80)

        mock_fetch.side_effect = self._make_fetch_side_effect(
            roster_data={"CommonTeamRoster": [{"PLAYER_ID": 2544, "PLAYER": "LeBron James"}]},
            player_info_data={"CommonPlayerInfo": [{"HEIGHT": "6-9", "POSITION": "F"}]},
            dashboard_data={"OverallPlayerDashboard": [{"FG3_PCT": 0.350, "FG3A": 150}]},
        )

        call_command("fetch_players")

        p = Player.objects.get(player_id=2544)
        self.assertEqual(p.full_name, "LeBron James")
        self.assertEqual(p.height_inches, 81)
