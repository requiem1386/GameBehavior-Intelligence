from django.contrib import admin
from .models import Player, PlayerActivity


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'steam_id',
        'username',
        'country',
        'is_active',
        'created_at',
    )

    search_fields = (
        'username',
        'steam_id',
    )

    list_filter = (
        'is_active',
        'country',
    )

    ordering = ('-created_at',)


@admin.register(PlayerActivity)
class PlayerActivityAdmin(admin.ModelAdmin):

    list_display = (
        'player',
        'activity_date',
        'sessions',
        'matches_played',
        'minutes_played',
    )

    list_filter = (
        'activity_date',
    )

    search_fields = (
        'player__username',
        'player__steam_id',
    )