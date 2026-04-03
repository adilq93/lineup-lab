import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from decimal import Decimal

from django.test import TestCase

from ingestion.models import Game, PBPEvent, Player, PlayerSeasonStats
from ingestion import nba_client


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
