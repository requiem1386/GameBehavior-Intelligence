
from django.db import models


class Match(models.Model):
    match_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )

    hltv_demo_id = models.CharField(
    max_length=100,
    unique=True,
    null=True,
    blank=True
)

    team1 = models.CharField(
    max_length=150,
    blank=True,
    default=""
)

    team2 = models.CharField(
    max_length=150,
    blank=True,
    default=""
)

    score1 = models.IntegerField(default=0)
    score2 = models.IntegerField(default=0)

    winner = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    event = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    match_date = models.DateTimeField(
        blank=True,
        null=True
    )

    format = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-match_date']

    def __str__(self):
        return f"{self.team1} vs {self.team2}"


class Map(models.Model):
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='maps'
    )

    map_index = models.PositiveIntegerField()

    map_name = models.CharField(max_length=50)

    patch_version = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    rounds_played = models.PositiveIntegerField(default=0)

    winner_side = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['map_index']

        constraints = [
            models.UniqueConstraint(
                fields=['match', 'map_index'],
                name='unique_match_map_index'
            )
        ]

    def __str__(self):
        return f"{self.match.match_id} - {self.map_name}"


class PlayerMapStats(models.Model):

    SIDE_CHOICES = [
        ('ct', 'Counter-Terrorist'),
        ('t', 'Terrorist'),
        ('all', 'All'),
    ]

    player = models.ForeignKey(
        'players.Player',
        on_delete=models.CASCADE,
        related_name='map_statistics'
    )

    map = models.ForeignKey(
        Map,
        on_delete=models.CASCADE,
        related_name='player_statistics'
    )

    side = models.CharField(
        max_length=10,
        choices=SIDE_CHOICES
    )

    n_rounds = models.FloatField(
        blank=True,
        null=True
    )

    kills = models.FloatField(
        blank=True,
        null=True
    )

    headshots = models.FloatField(
        blank=True,
        null=True
    )

    deaths = models.FloatField(
        blank=True,
        null=True
    )

    assists = models.FloatField(
        blank=True,
        null=True
    )

    hs_rate = models.FloatField(
        blank=True,
        null=True
    )

    adr = models.FloatField(default=0)

    damage = models.FloatField(default=0)

    kast = models.FloatField(
        blank=True,
        null=True
    )

    kast_rounds = models.FloatField(
        blank=True,
        null=True
    )

    rating = models.FloatField(
        blank=True,
        null=True
    )

    impact = models.FloatField(
        blank=True,
        null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['player', 'map', 'side'],
                name='unique_player_map_side'
            )
        ]

    def __str__(self):
        return (
            f"{self.player.username} - "
            f"{self.map.map_name} - {self.side}"
        )
