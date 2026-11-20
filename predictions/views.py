
import json
from django.shortcuts import render
from django.db.models import Avg, Count, Sum, StdDev
from matches.models import PlayerMapStats
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.exceptions import ValidationError

from players.models import Player
from predictions.services import predict_player_rating


@require_GET
def predict_rating_view(request):

    player_id = request.GET.get("player_id")
    map_name = request.GET.get("map_name")

    if not player_id or not map_name:
        return JsonResponse(
            {
                "success": False,
                "error": "player_id and map_name are required."
            },
            status=400
        )

    try:
        player_id = int(player_id)

        result = predict_player_rating(
            player_id=player_id,
            map_name=map_name
        )

        return JsonResponse({
            "success": True,
            "prediction": result
        })

    except ValueError:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid player_id."
            },
            status=400
        )

    except ValidationError as error:
        return JsonResponse(
            {
                "success": False,
                "error": error.messages
            },
            status=400
        )

    except Player.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "error": "Player not found."
            },
            status=404
        )

    except Exception:
        return JsonResponse(
            {
                "success": False,
                "error": "Prediction service error."
            },
            status=500
        )



@require_GET
def player_overview_view(request, player_id):

    player = Player.objects.filter(
        id=player_id,
        is_active=True
    ).first()

    if player is None:
        return JsonResponse({
            "success": False,
            "error": "Player not found."
        }, status=404)

    stats = PlayerMapStats.objects.filter(
        player=player,
        side="all"
    )

    summary = stats.aggregate(
        total_maps=Count("id"),
        avg_rating=Avg("rating"),
        avg_adr=Avg("adr"),
        avg_impact=Avg("impact"),
        avg_kast=Avg("kast"),
    )

    combat_totals = PlayerMapStats.objects.filter(
        player=player,
        side__in=["ct", "t"]
    ).aggregate(
        total_kills=Sum("kills"),
        total_deaths=Sum("deaths"),
        total_assists=Sum("assists"),
        total_headshots=Sum("headshots"),
    )

    map_performance = list(
        stats.values("map__map_name")
        .annotate(
            matches_count=Count("id"),
            avg_rating=Avg("rating"),
            avg_adr=Avg("adr"),
            avg_impact=Avg("impact"),
        )
        .order_by("-avg_rating")
    )

    recent_stats = (
        stats.select_related("map", "map__match")
        .order_by(
            "-map__match__match_date",
            "-map__match_id",
            "-map__map_index",
        )[:10]
    )

    rating_trend = []

    for stat in reversed(list(recent_stats)):
        rating_trend.append({
            "date": (
                stat.map.match.match_date.isoformat()
                if stat.map.match.match_date else None
            ),
            "map": stat.map.map_name,
            "rating": stat.rating,
            "adr": stat.adr,
            "impact": stat.impact,
        })

    recent_values = [item["rating"] for item in rating_trend if item["rating"] is not None]

    intelligence = {
        "sample_sufficient": summary["total_maps"] >= 10,
        "rating_stddev": stats.aggregate(
            rating_stddev=StdDev("rating")
        )["rating_stddev"],
        "trend": "insufficient_data",
        "recent_avg_rating": None,
        "previous_avg_rating": None,
        "rating_change": None,
    }

    if len(recent_values) >= 10:
        previous_values = recent_values[:5]
        latest_values = recent_values[-5:]

        previous_avg = sum(previous_values) / len(previous_values)
        latest_avg = sum(latest_values) / len(latest_values)
        change = latest_avg - previous_avg

        intelligence.update({
            "previous_avg_rating": round(previous_avg, 3),
            "recent_avg_rating": round(latest_avg, 3),
            "rating_change": round(change, 3),
            "trend": (
                "improving" if change > 0.03
                else "declining" if change < -0.03
                else "stable"
            ),
        })


    return JsonResponse({
        "success": True,

        "player": {
            "id": player.id,
            "username": player.username,
            "country": player.country,
        },

        "statistics": {
            **summary,
            **combat_totals,
        },

        "map_performance": map_performance,

        "rating_trend": rating_trend,
        "intelligence": intelligence,
    })



@require_GET
def compare_players_view(request):

    player1_id = request.GET.get("player1_id")
    player2_id = request.GET.get("player2_id")

    if not player1_id or not player2_id:
        return JsonResponse({
            "success": False,
            "error": "player1_id and player2_id are required."
        }, status=400)

    try:
        player1_id = int(player1_id)
        player2_id = int(player2_id)
    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Player IDs must be integers."
        }, status=400)

    if player1_id == player2_id:
        return JsonResponse({
            "success": False,
            "error": "Choose two different players."
        }, status=400)

    players = Player.objects.filter(
        id__in=[player1_id, player2_id],
        is_active=True
    )

    player_lookup = {player.id: player for player in players}

    if len(player_lookup) != 2:
        return JsonResponse({
            "success": False,
            "error": "One or both players were not found."
        }, status=404)

    def collect_stats(player_id):

        stats = PlayerMapStats.objects.filter(
            player_id=player_id,
            side="all"
        )

        combat = PlayerMapStats.objects.filter(
            player_id=player_id,
            side__in=["ct", "t"]
        )

        summary = stats.aggregate(
            total_maps=Count("id"),
            avg_rating=Avg("rating"),
            avg_adr=Avg("adr"),
            avg_impact=Avg("impact"),
            avg_kast=Avg("kast"),
        )

        combat_summary = combat.aggregate(
            total_kills=Sum("kills"),
            total_deaths=Sum("deaths"),
            total_assists=Sum("assists"),
            total_headshots=Sum("headshots"),
        )

        return {
            **summary,
            **combat_summary,
        }

    first = player_lookup[player1_id]
    second = player_lookup[player2_id]

    return JsonResponse({
        "success": True,
        "comparison": {
            "player1": {
                "id": first.id,
                "username": first.username,
                "statistics": collect_stats(first.id),
            },
            "player2": {
                "id": second.id,
                "username": second.username,
                "statistics": collect_stats(second.id),
            },
        },
    })

def dashboard_view(request):

    players = Player.objects.filter(
        is_active=True
    ).order_by("username").values(
        "id",
        "username"
    )

    return render(
        request,
        "predictions/dashboard.html",
        {
            "players": players,
        }
    ) 