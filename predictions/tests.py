
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from players.models import Player


class PredictionAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.player1 = Player.objects.create(
            steam_id="76561198000000001",
            username="TestPlayer1",
        )

        cls.player2 = Player.objects.create(
            steam_id="76561198000000002",
            username="TestPlayer2",
        )

    def test_dashboard_returns_200(self):
        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(response.status_code, 200)

    def test_prediction_requires_parameters(self):
        response = self.client.get(
            reverse("predict-rating")
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_prediction_rejects_invalid_player_id(self):
        response = self.client.get(
            reverse("predict-rating"),
            {
                "player_id": "invalid",
                "map_name": "de_dust2",
            },
        )

        self.assertEqual(response.status_code, 400)

    @patch("predictions.views.predict_player_rating")
    def test_prediction_success(self, mock_predict):
        mock_predict.return_value = {
            "player_id": self.player1.id,
            "username": self.player1.username,
            "map_name": "de_dust2",
            "predicted_rating": 1.05,
            "history_maps_count": 20,
            "model_name": "Random Forest",
            "feature_count": 45,
        }

        response = self.client.get(
            reverse("predict-rating"),
            {
                "player_id": self.player1.id,
                "map_name": "de_dust2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(
            response.json()["prediction"]["predicted_rating"],
            1.05,
        )

    def test_player_overview_success(self):
        response = self.client.get(
            reverse(
                "player-overview",
                kwargs={"player_id": self.player1.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(
            response.json()["player"]["username"],
            self.player1.username,
        )

    def test_player_overview_not_found(self):
        response = self.client.get(
            reverse(
                "player-overview",
                kwargs={"player_id": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_compare_players_success(self):
        response = self.client.get(
            reverse("compare-players"),
            {
                "player1_id": self.player1.id,
                "player2_id": self.player2.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_compare_rejects_same_player(self):
        response = self.client.get(
            reverse("compare-players"),
            {
                "player1_id": self.player1.id,
                "player2_id": self.player1.id,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_compare_requires_two_players(self):
        response = self.client.get(
            reverse("compare-players"),
            {
                "player1_id": self.player1.id,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_compare_player_not_found(self):
        response = self.client.get(
            reverse("compare-players"),
            {
                "player1_id": self.player1.id,
                "player2_id": 999999,
            },
        )

        self.assertEqual(response.status_code, 404)
