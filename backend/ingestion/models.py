from django.db import models


class Player(models.Model):
    player_id = models.IntegerField(primary_key=True)
    full_name = models.TextField()
    team_id = models.IntegerField(null=True)
    height_inches = models.IntegerField(null=True)
    position = models.TextField(null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'players'


class PlayerSeasonStats(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='season_stats')
    season = models.CharField(max_length=10)
    three_point_pct = models.DecimalField(max_digits=5, decimal_places=3, null=True)
    three_point_att = models.IntegerField(null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'player_season_stats'
        unique_together = ('player', 'season')


class Game(models.Model):
    game_id = models.CharField(max_length=20, primary_key=True)
    game_date = models.DateField()
    home_team_id = models.IntegerField()
    away_team_id = models.IntegerField()
    season = models.CharField(max_length=10)
    pace = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    low_confidence_reconstruction = models.BooleanField(default=False)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'games'


class PBPEvent(models.Model):
    event_id = models.BigAutoField(primary_key=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='pbp_events')
    period = models.IntegerField()
    clock_seconds = models.IntegerField()
    event_type = models.CharField(max_length=30)
    event_msg_type = models.IntegerField()
    team_id = models.IntegerField(null=True)
    player_id = models.IntegerField(null=True)
    points_scored = models.IntegerField(default=0)
    score_home = models.IntegerField(null=True)
    score_away = models.IntegerField(null=True)
    score_margin = models.IntegerField(null=True)
    home_lineup = models.JSONField(null=True)
    away_lineup = models.JSONField(null=True)
    opp_is_big_lineup = models.BooleanField(null=True)
    opp_is_shooter_lineup = models.BooleanField(null=True)
    opp_is_smallball = models.BooleanField(null=True)
    is_clutch = models.BooleanField(null=True)
    is_fast_game = models.BooleanField(null=True)
    is_slow_game = models.BooleanField(null=True)

    class Meta:
        db_table = 'pbp_events'
