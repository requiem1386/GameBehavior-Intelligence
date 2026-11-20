from django.urls import path

from predictions.views import (
    dashboard_view,
    predict_rating_view,
    player_overview_view,
    compare_players_view,
)

urlpatterns = [
    path(
        "predict/",
        predict_rating_view,
        name="predict-rating",
    ),
    path(
        "players/<int:player_id>/overview/",
        player_overview_view,
        name="player-overview",
    ),
    path(
        "compare/",
        compare_players_view,
        name="compare-players",
    ),
    path(
    "",
    dashboard_view,
    name="dashboard",
),
]
