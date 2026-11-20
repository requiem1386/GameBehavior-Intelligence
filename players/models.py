
from django.db import models


class Player(models.Model):

    steam_id = models.CharField(
        max_length=20,
        unique=True,
        db_index=True
    )

    username = models.CharField(
        max_length=100
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    location = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    avatar_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )
    steam_sync_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("rate_limited", "Rate Limited"),
        ],
        default="pending",
        db_index=True
    )

    steam_last_sync = models.DateTimeField(
        null=True,
        blank=True
    )

    steam_sync_error = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    @property
    def steam_profile_url(self):
        return f"https://steamcommunity.com/profiles/{self.steam_id}/"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Player'
        verbose_name_plural = 'Players'

    def __str__(self):
        return self.username


class PlayerActivity(models.Model):

    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='activities'
    )

    activity_date = models.DateField()

    sessions = models.PositiveIntegerField(
        default=0
    )

    matches_played = models.PositiveIntegerField(
        default=0
    )

    minutes_played = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        ordering = ['-activity_date']

        constraints = [
            models.UniqueConstraint(
                fields=['player', 'activity_date'],
                name='unique_player_activity_day'
            )
        ]

    def __str__(self):
        return f"{self.player.username} - {self.activity_date}"
