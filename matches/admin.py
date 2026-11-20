
from django.contrib import admin
from .models import Match, Map, PlayerMapStats


class MapInline(admin.TabularInline):
    model = Map
    extra = 0


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):

    list_display = (
        'match_id',
        'hltv_demo_id',
        'team1',
        'team2',
        'score1',
        'score2',
        'match_date',
    )

    search_fields = (
        'match_id',
        'hltv_demo_id',
        'team1',
        'team2',
        'event',
    )

    list_filter = (
        'match_date',
        'event',
        'format',
    )

    inlines = [MapInline]


@admin.register(Map)
class MapAdmin(admin.ModelAdmin):

    list_display = (
        'map_name',
        'match',
        'map_index',
        'rounds_played',
        'winner_side',
    )

    search_fields = (
        'map_name',
        'match__match_id',
    )

    list_filter = (
        'map_name',
        'winner_side',
    )


@admin.register(PlayerMapStats)
class PlayerMapStatsAdmin(admin.ModelAdmin):

    list_display = (
        'player',
        'map',
        'side',
        'kills',
        'deaths',
        'assists',
        'adr',
        'rating',
        'impact',
    )

    search_fields = (
        'player__username',
        'player__steam_id',
        'map__map_name',
        'map__match__match_id',
    )

    list_filter = (
        'side',
        'map__map_name',
    )
