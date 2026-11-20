
from pathlib import Path
import pandas as pd

total_players = 0
missing_ids = 0
invalid_ids = 0
duplicate_name_conflicts = 0
duplicate_steamids = 0

for file_path in Path("dataset/raw/data").glob("*.parquet"):
    df = pd.read_parquet(file_path, columns=["players"])

    for players in df["players"]:
        if hasattr(players, "tolist"):
            players = players.tolist()

        if not isinstance(players, list):
            continue

        name_to_ids = {}
        steamid_to_names = {}

        for player in players:
            if not isinstance(player, dict):
                continue

            total_players += 1

            name = str(player.get("name", "")).strip().casefold()
            steamid = player.get("steamid")

            if steamid is None:
                missing_ids += 1
                continue

            if (
                isinstance(steamid, bool)
                or not isinstance(steamid, int)
                or steamid <= 0
            ):
                invalid_ids += 1
                continue

            name_to_ids.setdefault(name, set()).add(steamid)
            steamid_to_names.setdefault(steamid, set()).add(name)

        duplicate_name_conflicts += sum(
            len(ids) > 1 for ids in name_to_ids.values()
        )

        duplicate_steamids += sum(
            len(names) > 1 for names in steamid_to_names.values()
        )

print("Total player records:", total_players)
print("Missing Steam IDs:", missing_ids)
print("Invalid Steam IDs:", invalid_ids)
print("Names with multiple Steam IDs:", duplicate_name_conflicts)
print("Steam IDs with multiple names:", duplicate_steamids)
