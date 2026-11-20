
import glob
import os

import pandas as pd

from django.core.management.base import BaseCommand
from django.db import transaction

from players.models import Player
from matches.models import Match, Map, PlayerMapStats


class Command(BaseCommand):

    help = "Import CS2 dataset into database"

    def handle(self, *args, **options):

        dataset_path = os.path.join(
            "dataset",
            "raw",
            "data",
            "*.parquet"
        )

        files = sorted(glob.glob(dataset_path))

        if not files:
            self.stdout.write(
                self.style.ERROR("No Parquet files found!")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(files)} files")
        )

        total_rows = 0
        total_players = 0
        total_maps = 0
        total_matches = 0
        total_stats = 0
        errors = 0

        for file_path in files:

            self.stdout.write(
                f"\nProcessing: {os.path.basename(file_path)}"
            )

            try:
                df = pd.read_parquet(file_path)

                with transaction.atomic():

                    for _, row in df.iterrows():

                        match_id = self.clean_string(
                            row.get("match_id")
                        )

                        if not match_id:
                            continue

                        hltv_demo_id = self.clean_string(
                            row.get("hltv_demo_id")
                        )

                        match_defaults = {
                            "team1": self.clean_string(
                                row.get("team1")
                            ) or "",
                            "team2": self.clean_string(
                                row.get("team2")
                            ) or "",
                            "score1": self.clean_int(
                                row.get("score1")
                            ),
                            "score2": self.clean_int(
                                row.get("score2")
                            ),
                            "winner": self.clean_string(
                                row.get("winner")
                            ),
                            "event": self.clean_string(
                                row.get("event")
                            ),
                            "match_date": self.clean_date(
                                row.get("match_date")
                            ),
                            "format": self.clean_string(
                                row.get("format")
                            ),
                        }

                        if hltv_demo_id:
                            duplicate_demo = Match.objects.filter(
                                hltv_demo_id=hltv_demo_id
                            ).exclude(
                                match_id=match_id
                            ).exists()

                            if not duplicate_demo:
                                match_defaults["hltv_demo_id"] = (
                                    hltv_demo_id
                                )

                        match, match_created = (
                            Match.objects.update_or_create(
                                match_id=match_id,
                                defaults=match_defaults
                            )
                        )

                        if match_created:
                            total_matches += 1

                        map_index = self.clean_int(
                            row.get("map_index")
                        )

                        map_name = self.clean_string(
                            row.get("map_name")
                        )

                        if not map_name:
                            continue

                        match_data = row.get("match")

                        patch_version = self.clean_string(
                            row.get("patch_version")
                        )

                        if not patch_version and isinstance(
                            match_data, dict
                        ):
                            patch_version = self.clean_string(
                                match_data.get("patch_version")
                            )

                        game_map, map_created = (
                            Map.objects.update_or_create(
                                match=match,
                                map_index=map_index,
                                defaults={
                                    "map_name": map_name,
                                    "patch_version": patch_version,
                                    "rounds_played": self.clean_int(
                                        row.get("rounds_played")
                                    ),
                                    "winner_side": self.clean_string(
                                        row.get("winner_side")
                                    ),
                                }
                            )
                        )

                        if map_created:
                            total_maps += 1

                        players_data = row.get("players")

                        # Convert NumPy arrays to Python lists
                        if hasattr(players_data, "tolist"):
                            players_data = players_data.tolist()

                        if not isinstance(
                            players_data, (list, tuple)
                        ):
                            continue

                        for player_data in players_data:

                            if not isinstance(player_data, dict):
                                continue

                            steam_id = player_data.get("steamid")
                            username = self.clean_string(
                                player_data.get("name")
                            )

                            if steam_id is None or not username:
                                continue

                            if self.is_missing(steam_id):
                                continue

                            # Steam IDs are stored as strings
                            steam_id = str(int(steam_id))

                            player, player_created = (
                                Player.objects.update_or_create(
                                    steam_id=steam_id,
                                    defaults={
                                        "username": username
                                    }
                                )
                            )

                            if player_created:
                                total_players += 1

                            side = self.clean_string(
                                player_data.get("side")
                            )

                            if side not in ("ct", "t", "all"):
                                continue

                            _, stats_created = (
                                PlayerMapStats.objects.update_or_create(
                                    player=player,
                                    map=game_map,
                                    side=side,
                                    defaults={
                                        "n_rounds": self.clean_float(
                                            player_data.get("n_rounds")
                                        ),
                                        "kills": self.clean_float(
                                            player_data.get("kills")
                                        ),
                                        "headshots": self.clean_float(
                                            player_data.get("headshots")
                                        ),
                                        "deaths": self.clean_float(
                                            player_data.get("deaths")
                                        ),
                                        "assists": self.clean_float(
                                            player_data.get("assists")
                                        ),
                                        "hs_rate": self.clean_float(
                                            player_data.get("hs_rate")
                                        ),
                                        "adr": self.clean_float(
                                            player_data.get("adr"), 0
                                        ),
                                        "damage": self.clean_float(
                                            player_data.get("dmg"), 0
                                        ),
                                        "kast": self.clean_float(
                                            player_data.get("kast")
                                        ),
                                        "kast_rounds": self.clean_float(
                                            player_data.get("kast_rounds")
                                        ),
                                        "rating": self.clean_float(
                                            player_data.get("rating")
                                        ),
                                        "impact": self.clean_float(
                                            player_data.get("impact")
                                        ),
                                    }
                                )
                            )

                            if stats_created:
                                total_stats += 1

                        total_rows += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        "File imported successfully"
                    )
                )

            except Exception as error:

                errors += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"Error in {os.path.basename(file_path)}: {error}"
                    )
                )

        self.stdout.write(
            "\n========== IMPORT SUMMARY =========="
        )

        self.stdout.write(f"Rows processed: {total_rows}")
        self.stdout.write(f"New matches: {total_matches}")
        self.stdout.write(f"New maps: {total_maps}")
        self.stdout.write(f"New players: {total_players}")
        self.stdout.write(f"New player statistics: {total_stats}")

        if errors:
            self.stdout.write(
                self.style.ERROR(
                    f"Files with errors: {errors}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "All files imported successfully!"
                )
            )

    @staticmethod
    def is_missing(value):

        if value is None:
            return True

        try:
            return bool(pd.isna(value))
        except (TypeError, ValueError):
            return False

    @classmethod
    def clean_string(cls, value):

        if cls.is_missing(value):
            return None

        value = str(value).strip()

        return value if value else None

    @classmethod
    def clean_float(cls, value, default=None):

        if cls.is_missing(value):
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def clean_int(cls, value, default=0):

        if cls.is_missing(value):
            return default

        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            return default

    @classmethod
    def clean_date(cls, value):

        if cls.is_missing(value):
            return None

        try:
            date_value = pd.to_datetime(
                value,
                errors="coerce"
            )

            if pd.isna(date_value):
                return None

            return date_value.to_pydatetime()

        except (TypeError, ValueError):
            return None
