from django.db import models


class PlayerPerformance(models.Model):
    player = models.ForeignKey(
        'players.Player',
        on_delete=models.CASCADE,
        related_name='performance_records'
    )

    average_kills = models.FloatField(default=0)
    average_deaths = models.FloatField(default=0)
    average_assists = models.FloatField(default=0)
    average_adr = models.FloatField(default=0)
    average_rating = models.FloatField(default=0)
    average_impact = models.FloatField(default=0)
    average_hs_rate = models.FloatField(default=0)

    total_maps = models.PositiveIntegerField(default=0)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-average_rating']

    def __str__(self):
        return f"{self.player.username} - Performance"