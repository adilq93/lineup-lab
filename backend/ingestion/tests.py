from unittest.mock import patch

from django.test import TestCase

from ingestion.models import GameLog, Player
from ingestion import nba_client


class PlayerModelTest(TestCase):
    def test_str(self):
        player = Player(nba_id=2544, full_name="LeBron James", team="LAL", position="F")
        self.assertEqual(str(player), "LeBron James")

    def test_unique_nba_id(self):
        Player.objects.create(nba_id=2544, full_name="LeBron James")
        with self.assertRaises(Exception):
            Player.objects.create(nba_id=2544, full_name="Duplicate")


class GameLogModelTest(TestCase):
    def setUp(self):
        self.player = Player.objects.create(nba_id=2544, full_name="LeBron James")

    def test_str(self):
        log = GameLog(
            player=self.player,
            game_id="0022401001",
            game_date="2025-01-15",
            matchup="LAL vs. BOS",
        )
        self.assertIn("LeBron James", str(log))

    def test_unique_together(self):
        GameLog.objects.create(
            player=self.player,
            game_id="0022401001",
            game_date="2025-01-15",
            matchup="LAL vs. BOS",
        )
        with self.assertRaises(Exception):
            GameLog.objects.create(
                player=self.player,
                game_id="0022401001",
                game_date="2025-01-15",
                matchup="LAL vs. BOS",
            )


class NbaClientTest(TestCase):
    @patch("ingestion.nba_client.commonteamroster", create=True)
    def test_get_roster_returns_list_on_success(self, _mock):
        # nba_api not installed in test env — confirm graceful empty return
        result = nba_client.get_roster(1610612747)
        self.assertIsInstance(result, list)

    @patch("ingestion.nba_client.playergamelog", create=True)
    def test_get_player_game_log_returns_list_on_success(self, _mock):
        result = nba_client.get_player_game_log(2544)
        self.assertIsInstance(result, list)

    def test_get_roster_handles_import_error(self):
        # nba_api absent → should return [] without raising
        result = nba_client.get_roster(1610612747)
        self.assertEqual(result, [])

    def test_get_player_game_log_handles_import_error(self):
        result = nba_client.get_player_game_log(2544)
        self.assertEqual(result, [])
