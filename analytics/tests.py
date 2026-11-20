
from datetime import timedelta
from unittest.mock import patch

import numpy as np
import pandas as pd

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from players.models import Player
from matches.models import Match, Map, PlayerMapStats

from analytics.ml.advanced_features import (
    to_records,
    extract_advanced_features,
)

from analytics.ml.dataset import (
    ADVANCED_FEATURES,
    MAP_FEATURES,
    FEATURES,
    safe_number,
    average,
    standard_deviation,
    kd_ratio,
    load_advanced_features,
    build_training_dataset,
)


# ============================================================
# TO RECORDS TESTS
# ============================================================

class ToRecordsTests(SimpleTestCase):

    def test_none_returns_empty_list(self):
        self.assertEqual(to_records(None), [])

    def test_list_is_returned(self):
        data = [{"name": "PlayerA"}]
        self.assertEqual(to_records(data), data)

    def test_numpy_array_is_converted_to_list(self):
        data = np.array([1, 2, 3])
        self.assertEqual(to_records(data), [1, 2, 3])


# ============================================================
# ADVANCED FEATURE TESTS
# ============================================================

class AdvancedFeatureTests(SimpleTestCase):

    def setUp(self):

        self.raw_df = pd.DataFrame([{
            "match_id": "match_001",
            "map_index": 0,
            "map_name": "de_dust2",

            "players": [
    {
        "name": "PlayerA",
        "steamid": 76561198000000001,
        "side": "all",
    },
    {
        "name": "PlayerB",
        "steamid": 76561198000000002,
        "side": "all",
    },
    {
        "name": "PlayerA",
        "steamid": 76561198000000001,
        "side": "ct",
    },
],

            "kills": [
                {
                    "attacker_name": "PlayerA",
                    "victim_name": "PlayerB",
                    "assister_name": None,
                    "round_num": 1,
                    "tick": 100,
                    "weapon": "awp",
                    "headshot": True,
                    "thrusmoke": False,
                    "noscope": True,
                    "attackerblind": False,
                    "penetrated": 0,
                    "distance": 100.0,
                    "dmg_health": 100,
                },
                {
                    "attacker_name": "PlayerA",
                    "victim_name": "PlayerB",
                    "assister_name": None,
                    "round_num": 1,
                    "tick": 200,
                    "weapon": "ak47",
                    "headshot": False,
                    "thrusmoke": True,
                    "noscope": False,
                    "attackerblind": True,
                    "penetrated": 1,
                    "distance": 50.0,
                    "dmg_health": 80,
                },
                {
                    "attacker_name": "PlayerB",
                    "victim_name": "PlayerA",
                    "assister_name": "PlayerA",
                    "round_num": 2,
                    "tick": 300,
                    "weapon": "glock",
                    "headshot": False,
                    "thrusmoke": False,
                    "noscope": False,
                    "attackerblind": False,
                    "penetrated": 0,
                    "distance": 20.0,
                    "dmg_health": 30,
                },
            ],

            "rounds": [],
        }])

    def test_extracts_one_record_per_all_player(self):

        result = extract_advanced_features(self.raw_df)

        self.assertEqual(len(result), 2)

        self.assertEqual(
            set(result["player_name"]),
            {"PlayerA", "PlayerB"},
        )

    def test_extracts_player_kill_statistics(self):

        result = extract_advanced_features(self.raw_df)

        player = result.set_index("player_name").loc["PlayerA"]

        self.assertEqual(player["advanced_kills"], 2)
        self.assertEqual(player["advanced_deaths"], 1)
        self.assertEqual(player["advanced_assists"], 1)
        self.assertEqual(player["advanced_headshots"], 1)

        self.assertAlmostEqual(
            player["advanced_hs_rate"],
            0.5,
        )

    def test_extracts_multikill_statistics(self):

        result = extract_advanced_features(self.raw_df)

        player = result.set_index("player_name").loc["PlayerA"]

        self.assertEqual(player["advanced_double_kills"], 1)
        self.assertEqual(player["advanced_triple_kills"], 0)
        self.assertEqual(player["advanced_four_kills"], 0)
        self.assertEqual(player["advanced_aces"], 0)

    def test_extracts_opening_duels(self):

        result = extract_advanced_features(self.raw_df)

        player = result.set_index("player_name").loc["PlayerA"]

        self.assertEqual(player["advanced_opening_kills"], 1)
        self.assertEqual(player["advanced_opening_deaths"], 1)

    def test_extracts_weapon_and_special_kill_features(self):

        result = extract_advanced_features(self.raw_df)

        player = result.set_index("player_name").loc["PlayerA"]

        self.assertEqual(player["advanced_awp_kills"], 1)
        self.assertEqual(player["advanced_rifle_kills"], 1)
        self.assertEqual(player["advanced_pistol_kills"], 0)

        self.assertEqual(player["advanced_smoke_kills"], 1)
        self.assertEqual(player["advanced_noscope_kills"], 1)
        self.assertEqual(player["advanced_blind_kills"], 1)
        self.assertEqual(player["advanced_wallbang_kills"], 1)

    def test_extracts_distance_and_damage_features(self):

        result = extract_advanced_features(self.raw_df)

        player = result.set_index("player_name").loc["PlayerA"]

        self.assertAlmostEqual(
            player["advanced_avg_kill_distance"],
            75.0,
        )

        self.assertEqual(
            player["advanced_max_kill_distance"],
            100.0,
        )

        self.assertEqual(
            player["advanced_total_kill_damage"],
            180,
        )

        self.assertAlmostEqual(
            player["advanced_damage_per_kill"],
            90.0,
        )

    def test_player_without_kills_has_zero_kill_rate(self):

        result = extract_advanced_features(self.raw_df)

        player = result.set_index("player_name").loc["PlayerB"]

        self.assertEqual(player["advanced_hs_rate"], 0)

        self.assertAlmostEqual(
            player["advanced_avg_kill_distance"],
            20.0,
        )

    def test_player_without_name_is_ignored(self):

        self.raw_df.at[0, "players"] = [
            {"name": None, "side": "all"}
        ]

        result = extract_advanced_features(self.raw_df)

        self.assertEqual(len(result), 0)


# ============================================================
# DATASET HELPER TESTS
# ============================================================

class DatasetHelperTests(SimpleTestCase):

    def test_safe_number_converts_integer(self):
        self.assertEqual(safe_number(10), 10.0)

    def test_safe_number_converts_float(self):
        self.assertEqual(safe_number(2.5), 2.5)

    def test_safe_number_returns_none_for_none(self):
        self.assertIsNone(safe_number(None))

    def test_safe_number_returns_none_for_nan(self):
        self.assertIsNone(safe_number(np.nan))

    def test_average_calculates_mean(self):

        items = [
            {"rating": 1.0},
            {"rating": 2.0},
            {"rating": 3.0},
        ]

        self.assertEqual(average(items, "rating"), 2.0)

    def test_average_ignores_none(self):

        items = [
            {"rating": 1.0},
            {"rating": None},
            {"rating": 3.0},
        ]

        self.assertEqual(average(items, "rating"), 2.0)

    def test_average_returns_zero_for_empty_values(self):
        self.assertEqual(average([], "rating"), 0.0)

    def test_standard_deviation_calculates_population_std(self):

        items = [
            {"rating": 1.0},
            {"rating": 2.0},
            {"rating": 3.0},
        ]

        self.assertAlmostEqual(
            standard_deviation(items, "rating"),
            np.std([1.0, 2.0, 3.0]),
        )

    def test_standard_deviation_returns_zero_for_one_value(self):

        self.assertEqual(
            standard_deviation(
                [{"rating": 1.0}],
                "rating",
            ),
            0.0,
        )

    def test_kd_ratio_calculates_correctly(self):

        items = [
            {"kills": 20, "deaths": 10},
            {"kills": 10, "deaths": 5},
        ]

        self.assertEqual(kd_ratio(items), 2.0)

    def test_kd_ratio_returns_zero_when_deaths_are_zero(self):

        items = [
            {"kills": 10, "deaths": 0},
        ]

        self.assertEqual(kd_ratio(items), 0.0)


# ============================================================
# DATASET STRUCTURE TESTS
# ============================================================

class DatasetStructureTests(SimpleTestCase):

    def test_feature_count_is_45(self):
        self.assertEqual(len(FEATURES), 45)

    def test_feature_names_are_unique(self):
        self.assertEqual(len(FEATURES), len(set(FEATURES)))

    def test_advanced_features_count_is_22(self):
        self.assertEqual(len(ADVANCED_FEATURES), 22)

    def test_map_features_count_is_5(self):
        self.assertEqual(len(MAP_FEATURES), 5)

    def test_all_advanced_features_have_history_columns(self):

        for feature in ADVANCED_FEATURES:

            self.assertIn(
                f"prior_avg_{feature}",
                FEATURES,
            )

    def test_map_features_are_in_model_features(self):

        for feature in MAP_FEATURES:
            self.assertIn(feature, FEATURES)


# ============================================================
# LOAD ADVANCED FEATURES TESTS
# ============================================================

class LoadAdvancedFeaturesTests(SimpleTestCase):

    @patch("analytics.ml.dataset.pd.read_parquet")
    @patch("analytics.ml.dataset.os.path.exists")
    def test_loads_and_indexes_advanced_features(
        self,
        mock_exists,
        mock_read_parquet,
    ):

        mock_exists.return_value = True

        mock_read_parquet.return_value = pd.DataFrame([
    {
        "match_id": 123,
        "map_index": 0,
        "steam_id": "76561198000000001",
        "player_name": "PlayerA",
        "advanced_kills": 10,
    }
])

        result = load_advanced_features()

        key = ("123", 0, "76561198000000001")

        self.assertIn(key, result)

        self.assertEqual(
            result[key]["advanced_kills"],
            10,
        )

    @patch("analytics.ml.dataset.os.path.exists")
    def test_raises_error_when_file_does_not_exist(self, mock_exists):

        mock_exists.return_value = False

        with self.assertRaises(FileNotFoundError):
            load_advanced_features()


# ============================================================
# BUILD TRAINING DATASET TESTS
# ============================================================

class BuildTrainingDatasetTests(TestCase):

    def setUp(self):

        self.player = Player.objects.create(
            steam_id="76561198000000001",
            username="DatasetTester",
        )

        self.base_date = timezone.now()

        self.matches = []

        for index in range(2):

            match = Match.objects.create(
                match_id=f"dataset_match_{index}",
                team1="Team A",
                team2="Team B",
                match_date=self.base_date + timedelta(days=index),
            )

            game_map = Map.objects.create(
                match=match,
                map_index=0,
                map_name="de_dust2",
            )

            self.matches.append(match)

            PlayerMapStats.objects.create(
                player=self.player,
                map=game_map,
                side="all",
                kills=10,
                deaths=5,
                assists=3,
                headshots=4,
                adr=70 + index * 10,
                rating=1.0 + index * 0.2,
                impact=1.0,
                kast=75,
            )

            PlayerMapStats.objects.create(
                player=self.player,
                map=game_map,
                side="ct",
                kills=5,
                deaths=2,
                assists=1,
                headshots=2,
            )

            PlayerMapStats.objects.create(
                player=self.player,
                map=game_map,
                side="t",
                kills=7,
                deaths=3,
                assists=2,
                headshots=3,
            )

    @patch("analytics.ml.dataset.load_advanced_features", return_value={})
    def test_builds_samples_from_previous_history(self, mock_features):

        df = build_training_dataset(min_history=1)

        self.assertEqual(len(df), 1)

        sample = df.iloc[0]

        self.assertEqual(
            sample["match_id"],
            self.matches[1].id,
        )

        self.assertEqual(
            sample["prior_maps_count"],
            1,
        )

        self.assertAlmostEqual(
            sample["prior_avg_rating"],
            1.0,
        )

    @patch("analytics.ml.dataset.load_advanced_features", return_value={})
    def test_current_match_does_not_leak_into_history(self, mock_features):

        df = build_training_dataset(min_history=1)

        sample = df.iloc[0]

        self.assertAlmostEqual(
            sample["prior_avg_rating"],
            1.0,
        )

        self.assertNotEqual(
            sample["prior_avg_rating"],
            1.2,
        )

    @patch("analytics.ml.dataset.load_advanced_features", return_value={})
    def test_maps_in_same_match_do_not_leak_into_each_other(
        self,
         mock_features,
    ):
        current_match = Match.objects.create(
            match_id="dataset_current_series",
            team1="Team A",
            team2="Team B",
            match_date=self.base_date + timedelta(days=2),
        )

        map1 = Map.objects.create(
            match=current_match,
            map_index=0,
            map_name="de_mirage",
        )

        map2 = Map.objects.create(
            match=current_match,
            map_index=1,
            map_name="de_inferno",
        )

        PlayerMapStats.objects.create(
            player=self.player,
            map=map1,
            side="all",
            kills=30,
            deaths=10,
            assists=5,
            headshots=15,
            adr=150,
            rating=2.0,
            impact=2.0,
            kast=90,
        )

        PlayerMapStats.objects.create(
            player=self.player,
            map=map2,
            side="all",
            kills=5,
            deaths=15,
            assists=2,
            headshots=2,
            adr=40,
            rating=0.5,
            impact=0.5,
            kast=50,
        )

        df = build_training_dataset(min_history=1)

        current_samples = df[
            df["match_id"] == current_match.id
        ]

        self.assertEqual(len(current_samples), 2)

        for _, sample in current_samples.iterrows():

            self.assertEqual(
                sample["prior_maps_count"],
                2,
            )

            self.assertAlmostEqual(
                sample["prior_avg_rating"],
                1.1,
            )

            self.assertEqual(
                sample["prior_map_matches_count"],
                0,
            )

    @patch("analytics.ml.dataset.load_advanced_features", return_value={})
    def test_combines_ct_and_t_combat_statistics(self, mock_features):

        df = build_training_dataset(min_history=1)

        sample = df.iloc[0]

        self.assertEqual(sample["prior_avg_kills"], 12)
        self.assertEqual(sample["prior_avg_deaths"], 5)
        self.assertEqual(sample["prior_avg_assists"], 3)
        self.assertEqual(sample["prior_avg_headshots"], 5)

    @patch("analytics.ml.dataset.load_advanced_features", return_value={})
    def test_calculates_map_specific_history(self, mock_features):

        df = build_training_dataset(min_history=1)

        sample = df.iloc[0]

        self.assertEqual(
            sample["prior_map_matches_count"],
            1,
        )

        self.assertAlmostEqual(
            sample["prior_map_avg_rating"],
            1.0,
        )

        self.assertAlmostEqual(
            sample["prior_map_avg_adr"],
            70.0,
        )

    @patch("analytics.ml.dataset.load_advanced_features", return_value={})
    def test_respects_minimum_history(self, mock_features):

        with self.assertRaises(ValueError):
            build_training_dataset(min_history=2)
