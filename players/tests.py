
from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from players.models import Player, PlayerActivity


class PlayerModelTests(TestCase):

    def setUp(self):
        self.player = Player.objects.create(
            steam_id="76561198000000001",
            username="TestPlayer",
        )

    def test_player_creation(self):
        self.assertEqual(self.player.username, "TestPlayer")
        self.assertTrue(self.player.is_active)

    def test_steam_profile_url(self):
        self.assertEqual(
            self.player.steam_profile_url,
            "https://steamcommunity.com/profiles/76561198000000001/",
        )

    def test_player_string_representation(self):
        self.assertEqual(str(self.player), "TestPlayer")

    def test_steam_id_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Player.objects.create(
                    steam_id=self.player.steam_id,
                    username="AnotherPlayer",
                )


class PlayerActivityModelTests(TestCase):

    def setUp(self):
        self.player = Player.objects.create(
            steam_id="76561198000000002",
            username="ActivityPlayer",
        )

    def test_activity_creation(self):
        activity = PlayerActivity.objects.create(
            player=self.player,
            activity_date=date(2026, 11, 20),
            sessions=2,
            matches_played=5,
            minutes_played=120,
        )

        self.assertEqual(activity.player, self.player)
        self.assertEqual(activity.matches_played, 5)
        self.assertEqual(activity.minutes_played, 120)

    def test_activity_day_must_be_unique_per_player(self):
        PlayerActivity.objects.create(
            player=self.player,
            activity_date=date(2026, 11, 20),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerActivity.objects.create(
                    player=self.player,
                    activity_date=date(2026, 11, 20),
                )
