
import joblib
import pandas as pd

from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError

from players.models import Player
from matches.models import PlayerMapStats
from analytics.ml.dataset import (
    FEATURES,
    ADVANCED_FEATURES,
    average,
    standard_deviation,
    kd_ratio,
    safe_number,
    load_advanced_features,
)


MODEL_PATH = (
    Path(settings.BASE_DIR)
    / "analytics"
    / "ml"
    / "best_player_rating_model.joblib"
)


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Trained model file not found.")

    model_data = joblib.load(MODEL_PATH)

    if not isinstance(model_data, dict) or "model" not in model_data:
        raise ValueError("Invalid model file format. Retrain the model.")

    if model_data.get("features") != FEATURES:
        raise ValueError("Model features do not match current dataset features.")

    return model_data


def build_player_history(player):
    advanced_lookup = load_advanced_features()

    stats = list(
        PlayerMapStats.objects
        .filter(player=player, side="all")
        .select_related("map", "map__match")
        .order_by(
            "map__match__match_date",
            "map__match_id",
            "map__map_index",
        )
    )

    history = []
    map_history = {}

    for stat in stats:
        combat_stats = PlayerMapStats.objects.filter(
            player=player,
            map=stat.map,
            side__in=["ct", "t"],
        )

        combat = {
            "kills": 0.0,
            "deaths": 0.0,
            "assists": 0.0,
            "headshots": 0.0,
        }

        for combat_stat in combat_stats:
            for field in combat:
                value = safe_number(getattr(combat_stat, field))
                if value is not None:
                    combat[field] += value

        advanced_key = (
    str(stat.map.match.match_id),
    int(stat.map.map_index),
    str(player.steam_id),
)

        advanced_record = advanced_lookup.get(advanced_key, {})

        current = {
            **combat,
            "adr": safe_number(stat.adr) or 0.0,
            "rating": safe_number(stat.rating) or 0.0,
            "impact": safe_number(stat.impact) or 0.0,
            "kast": safe_number(stat.kast) or 0.0,
        }

        for feature in ADVANCED_FEATURES:
            current[feature] = (
                safe_number(advanced_record.get(feature)) or 0.0
            )

        history.append(current)

        map_history.setdefault(stat.map.map_name, []).append(current)

    return history, map_history


def build_prediction_features(player, map_name):
    history, map_history = build_player_history(player)

    if len(history) < 3:
        raise ValidationError(
            "Player needs at least 3 previous maps for prediction."
        )

    recent = history[-5:]
    recent_three = history[-3:]
    previous_three = history[-6:-3]

    avg_kills = average(recent, "kills")
    avg_deaths = average(recent, "deaths")

    current_kd = (
        avg_kills / avg_deaths if avg_deaths > 0 else 0.0
    )

    recent_rating = average(recent_three, "rating")
    recent_adr = average(recent_three, "adr")

    rating_trend = 0.0
    kd_trend = 0.0

    if len(previous_three) == 3:
        previous_rating = average(previous_three, "rating")
        previous_kd = kd_ratio(previous_three)

        rating_trend = recent_rating - previous_rating
        kd_trend = kd_ratio(recent_three) - previous_kd

    map_history_recent = map_history.get(map_name, [])[-5:]

    features = {
        "prior_avg_adr": average(recent, "adr"),
        "prior_avg_rating": average(recent, "rating"),
        "prior_avg_impact": average(recent, "impact"),
        "prior_avg_kast": average(recent, "kast"),
        "prior_last_rating": history[-1]["rating"],
        "prior_last_adr": history[-1]["adr"],
        "prior_maps_count": len(history),
        "prior_avg_kills": avg_kills,
        "prior_avg_deaths": avg_deaths,
        "prior_avg_assists": average(recent, "assists"),
        "prior_avg_headshots": average(recent, "headshots"),
        "prior_kd_ratio": current_kd,
        "prior_rating_std": standard_deviation(recent, "rating"),
        "prior_recent_avg_rating": recent_rating,
        "prior_rating_trend": rating_trend,
        "prior_adr_std": standard_deviation(recent, "adr"),
        "prior_recent_avg_adr": recent_adr,
        "prior_kd_trend": kd_trend,

        "prior_map_avg_rating": average(
            map_history_recent, "rating"
        ),
        "prior_map_avg_adr": average(
            map_history_recent, "adr"
        ),
        "prior_map_avg_kills": average(
            map_history_recent, "kills"
        ),
        "prior_map_avg_impact": average(
            map_history_recent, "impact"
        ),
        "prior_map_matches_count": len(
            map_history.get(map_name, [])
        ),
    }

    for feature in ADVANCED_FEATURES:
        features[f"prior_avg_{feature}"] = average(
            recent, feature
        )

    return features


def predict_player_rating(player_id, map_name):
    try:
        player = Player.objects.get(pk=player_id, is_active=True)
    except Player.DoesNotExist:
        raise ValidationError("Player not found or inactive.")

    if not map_name or not map_name.strip():
        raise ValidationError("Map name is required.")

    features = build_prediction_features(player, map_name.strip())

    model_data = load_model()
    model = model_data["model"]

    input_df = pd.DataFrame(
        [[features[name] for name in FEATURES]],
        columns=FEATURES,
    )

    prediction = float(model.predict(input_df)[0])

    return {
        "player_id": player.id,
        "username": player.username,
        "map_name": map_name.strip(),
        "predicted_rating": round(prediction, 4),
        "history_maps_count": len(
            PlayerMapStats.objects.filter(
                player=player,
                side="all",
            )
        ),
        "model_name": model_data.get("model_name", "Unknown"),
        "feature_count": len(FEATURES),
    }
