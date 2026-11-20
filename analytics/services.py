
from collections import defaultdict

from django.db.models import Avg

from players.models import Player
from matches.models import PlayerMapStats
from .models import PlayerPerformance


def calculate_player_performance():
    players = Player.objects.all()

    for player in players:
        # آمار کلی بازیکن در هر نقشه
        all_stats = PlayerMapStats.objects.filter(
            player=player,
            side="all"
        )

        # آمار تعداد کیل، دث و اسیست از دو سمت CT و T
        side_stats = PlayerMapStats.objects.filter(
            player=player,
            side__in=["ct", "t"]
        )

        kills_by_map = defaultdict(float)
        deaths_by_map = defaultdict(float)
        assists_by_map = defaultdict(float)
        headshots_by_map = defaultdict(float)

        for stat in side_stats:
            map_id = stat.map_id

            kills_by_map[map_id] += stat.kills or 0
            deaths_by_map[map_id] += stat.deaths or 0
            assists_by_map[map_id] += stat.assists or 0
            headshots_by_map[map_id] += stat.headshots or 0

        total_kills = sum(kills_by_map.values())
        total_headshots = sum(headshots_by_map.values())

        total_maps = len(kills_by_map)

        if total_maps == 0:
            continue

        average_kills = total_kills / total_maps
        average_deaths = sum(deaths_by_map.values()) / total_maps
        average_assists = sum(assists_by_map.values()) / total_maps

        # شاخص‌هایی که از رکوردهای all محاسبه می‌شوند
        metrics = all_stats.aggregate(
            avg_adr=Avg("adr"),
            avg_rating=Avg("rating"),
            avg_impact=Avg("impact"),
            avg_hs_rate=Avg("hs_rate"),
        )

        average_hs_rate = (
            (total_headshots / total_kills) * 100
            if total_kills > 0 else 0
        )

        # ذخیره یا به‌روزرسانی اطلاعات عملکرد
        PlayerPerformance.objects.update_or_create(
            player=player,
            defaults={
                "average_kills": average_kills,
                "average_deaths": average_deaths,
                "average_assists": average_assists,
                "average_adr": metrics["avg_adr"] or 0,
                "average_rating": metrics["avg_rating"] or 0,
                "average_impact": metrics["avg_impact"] or 0,
                "average_hs_rate": (
                    metrics["avg_hs_rate"]
                    if metrics["avg_hs_rate"] is not None
                    else average_hs_rate
                ),
                "total_maps": total_maps,
            }
        )

    return PlayerPerformance.objects.count()
