
import time

from django.core.management.base import BaseCommand
from django.db.models import Q

from players.models import Player
from players.services.steam import fetch_steam_profile


class Command(BaseCommand):
    help = "Synchronize public Steam profiles for players"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Maximum number of profiles to process",
        )

        parser.add_argument(
            "--delay",
            type=float,
            default=15,
            help="Delay between requests in seconds",
        )

        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Include previously failed profiles",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        delay = options["delay"]
        retry_failed = options["retry_failed"]

        if limit < 1:
            self.stderr.write(
                self.style.ERROR("Limit must be at least 1.")
            )
            return

        if delay < 0:
            self.stderr.write(
                self.style.ERROR("Delay cannot be negative.")
            )
            return

        # A profile is incomplete if either field is missing.
        incomplete = (
            Q(avatar_url__isnull=True)
            | Q(avatar_url="")
            | Q(location__isnull=True)
            | Q(location="")
        )

        players = Player.objects.filter(incomplete)

        # Never automatically retry rate-limited profiles.
        if retry_failed:
         players = players.filter(
        steam_sync_status__in=[
            "pending",
            "failed",
        ]
    )
        else:
         players = players.filter(
        steam_sync_status="pending"
    )

        players = players.order_by("id")[:limit]

        players = list(players)
        total = len(players)

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "No eligible players found."
                )
            )
            return

        success_count = 0
        failed_count = 0
        rate_limited_count = 0

        self.stdout.write(
            self.style.WARNING(
                f"Starting Steam sync for {total} players..."
            )
        )

        for index, player in enumerate(players, start=1):
            self.stdout.write(
                f"\n[{index}/{total}] "
                f"{player.username} | Steam ID: {player.steam_id}"
            )

            result = fetch_steam_profile(player)

            status = result.get("status")

            if result.get("success"):
                success_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"SUCCESS: {result.get('username')} | "
                        f"Location: {result.get('location')} | "
                        f"Avatar: "
                        f"{'Yes' if result.get('avatar_url') else 'No'}"
                    )
                )

            elif status == "rate_limited":
                rate_limited_count += 1

                self.stderr.write(
                    self.style.ERROR(
                        "Steam returned HTTP 429. "
                        "Stopping immediately; do not retry now."
                    )
                )
                break

            else:
                failed_count += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"FAILED ({status}): "
                        f"{result.get('error', 'Unknown error')}"
                    )
                )

            if index < total:
                time.sleep(delay)

        self.stdout.write("\n========== SYNC SUMMARY ==========")
        self.stdout.write(f"Selected: {total}")
        self.stdout.write(f"Successful: {success_count}")
        self.stdout.write(f"Failed: {failed_count}")
        self.stdout.write(f"Rate limited: {rate_limited_count}")

        self.stdout.write(
            "Remaining incomplete profiles: "
            f"{Player.objects.filter(incomplete).count()}"
        )
