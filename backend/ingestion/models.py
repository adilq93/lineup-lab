from django.db import models


class Player(models.Model):
    nba_id = models.IntegerField(unique=True)
    full_name = models.CharField(max_length=100)
    team = models.CharField(max_length=50, blank=True)
    position = models.CharField(max_length=10, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class GameLog(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='game_logs')
    game_id = models.CharField(max_length=20)
    game_date = models.DateField()
    matchup = models.CharField(max_length=20)
    minutes = models.FloatField(default=0)
    points = models.IntegerField(default=0)
    rebounds = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)

    class Meta:
        unique_together = ('player', 'game_id')

    def __str__(self):
        return f"{self.player} - {self.game_date} vs {self.matchup}"
