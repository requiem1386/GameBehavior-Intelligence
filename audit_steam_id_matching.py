import pandas as pd
from pathlib import Path
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from players.models import Player
from analytics.ml.advanced_features import to_records

raw_dir = Path("dataset/raw/data")

db_ids = set(
    Player.objects.values_list("steam_id", flat=True)
)

parquet_ids = set()

for file_path in raw_dir.glob("*.parquet"):
    raw = pd.read_parquet(file_path, columns=["players"])

    for players in raw["players"]:
        players = to_records(players)
        if not isinstance(players, (list, tuple)):
            continue

        for player in players:
            if not isinstance(player, dict):
                continue

            if player.get("side") != "all":
                continue

            steam_id = player.get("steamid")

            if steam_id is not None:
                parquet_ids.add(str(int(steam_id)))

matched_ids = db_ids & parquet_ids
missing_ids = db_ids - parquet_ids

print("Database unique IDs:", len(db_ids))
print("Parquet unique IDs:", len(parquet_ids))
print("Matched IDs:", len(matched_ids))
print("Database IDs not found in Parquet:", len(missing_ids))
print(
    "Matching coverage:",
    round(len(matched_ids) / len(db_ids) * 100, 2),
    "%"
)

