
from django.db import IntegrityError, transaction
from django.test import TestCase

from players.models import Player
from matches.models import Match, Map, PlayerMapStats


class MatchModelTests(TestCase):

    def setUp(self):
        self.match = Match.objects.create(
            match_id="test_match_001",
            team1="Team Alpha",
            team2="Team Bravo",
            score1=13,
            score2=9,
            winner="Team Alpha",
            event="Test Championship",
            format="BO3",
        )

    def test_match_creation(self):
        self.assertEqual(self.match.match_id, "test_match_001")
        self.assertEqual(self.match.score1, 13)
        self.assertEqual(self.match.winner, "Team Alpha")

    def test_match_string_representation(self):
        self.assertEqual(
            str(self.match),
            "Team Alpha vs Team Bravo",
        )

    def test_match_id_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Match.objects.create(
                    match_id="test_match_001",
                )

    def test_hltv_demo_id_must_be_unique(self):
        Match.objects.create(
            match_id="test_match_002",
            hltv_demo_id="demo_123",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Match.objects.create(
                    match_id="test_match_003",
                    hltv_demo_id="demo_123",
                )


class MapModelTests(TestCase):

    def setUp(self):
        self.match = Match.objects.create(
            match_id="test_match_100",
            team1="Team Alpha",
            team2="Team Bravo",
        )

        self.map = Map.objects.create(
            match=self.match,
            map_index=0,
            map_name="de_dust2",
            rounds_played=24,
            winner_side="ct",
        )

    def test_map_creation(self):
        self.assertEqual(self.map.map_name, "de_dust2")
        self.assertEqual(self.map.rounds_played, 24)

    def test_map_string_representation(self):
        self.assertEqual(
            str(self.map),
            "test_match_100 - de_dust2",
        )

    def test_map_index_must_be_unique_per_match(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Map.objects.create(
                    match=self.match,
                    map_index=0,
                    map_name="de_mirage",
                )

    def test_same_map_index_allowed_for_different_matches(self):
        another_match = Match.objects.create(
            match_id="test_match_101",
        )

        another_map = Map.objects.create(
            match=another_match,
            map_index=0,
            map_name="de_mirage",
        )

        self.assertEqual(another_map.map_index, 0)

    def test_deleting_match_deletes_maps(self):
        match_id = self.match.id

        self.match.delete()

        self.assertFalse(
            Map.objects.filter(match_id=match_id).exists()
        )


class PlayerMapStatsModelTests(TestCase):

    def setUp(self):
        self.player = Player.objects.create(
            steam_id="76561198000000100",
            username="TestPlayer",
        )

        self.match = Match.objects.create(
            match_id="test_match_200",
        )

        self.map = Map.objects.create(
            match=self.match,
            map_index=0,
            map_name="de_inferno",
        )

        self.stats = PlayerMapStats.objects.create(
            player=self.player,
            map=self.map,
            side="all",
            kills=25,
            deaths=15,
            assists=7,
            adr=95.5,
            rating=1.35,
            impact=1.40,
        )

    def test_player_map_stats_creation(self):
        self.assertEqual(self.stats.player, self.player)
        self.assertEqual(self.stats.map, self.map)
        self.assertEqual(self.stats.kills, 25)
        self.assertEqual(self.stats.rating, 1.35)

    def test_player_map_stats_string_representation(self):
        self.assertEqual(
            str(self.stats),
            "TestPlayer - de_inferno - all",
        )

    def test_player_map_side_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerMapStats.objects.create(
                    player=self.player,
                    map=self.map,
                    side="all",
                )

    def test_different_sides_allowed_for_same_player_and_map(self):
        ct_stats = PlayerMapStats.objects.create(
            player=self.player,
            map=self.map,
            side="ct",
        )

        t_stats = PlayerMapStats.objects.create(
            player=self.player,
            map=self.map,
            side="t",
        )

        self.assertEqual(ct_stats.side, "ct")
        self.assertEqual(t_stats.side, "t")

    def test_deleting_player_deletes_statistics(self):
        self.player.delete()

        self.assertFalse(
            PlayerMapStats.objects.filter(
                player_id=self.player.id
            ).exists()
        )
