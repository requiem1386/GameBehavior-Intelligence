from django.contrib import admin
from .models import PlayerPerformance


@admin.register(PlayerPerformance)
class PlayerPerformanceAdmin(admin.ModelAdmin):

    list_display = (
        'player',
        'average_kills',
        'average_deaths',
        'average_assists',
        'average_adr',
        'average_rating',
        'average_impact',
        'total_maps',
    )

    search_fields = (
        'player__username',
        'player__steam_id',
    )

    list_filter = (
        'total_maps',
    )

    ordering = ('-average_rating',)