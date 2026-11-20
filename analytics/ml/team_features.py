from pathlib import Path

import pandas as pd

from players.models import Player


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "dataset" / "raw" / "data"


def _as_list(value):
    """Convert Parquet array-like values into a Python list."""
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        return list(value)

    if hasattr(value, "tolist"):
        result = value.tolist()
        return result if isinstance(result, list) else [result]

    return []


def load_team_rosters():
    """
    Load team rosters from raw Parquet files.

    Returns:
        dict:
            {
                (match_id, map_index): [
                    {player_id, ...},
                    {player_id, ...},
                ]
            }

    Only players registered in the database are included.
    """

    player_ids = {
        str(steam_id): player_id
        for steam_id, player_id in Player.objects.values_list(
            "steam_id",
            "id",
        )
        if steam_id
    }

    roster_lookup = {}

    parquet_files = sorted(RAW_DATA_DIR.glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(
            f"No Parquet files found in: {RAW_DATA_DIR}"
        )

    for file_path in parquet_files:
        dataframe = pd.read_parquet(
            file_path,
            columns=["match_id", "map_index", "teams"],
        )

        for row in dataframe.itertuples(index=False):
            match_id = str(row.match_id)
            map_index = int(row.map_index)

            teams = _as_list(row.teams)
            map_rosters = []

            for team in teams:
                if not isinstance(team, dict):
                    continue

                roster = set()

                for member in _as_list(team.get("players")):
                    if not isinstance(member, dict):
                        continue

                    steam_id = member.get("steamid")

                    if steam_id is None:
                        continue

                    player_id = player_ids.get(str(steam_id))

                    if player_id is not None:
                        roster.add(player_id)

                if roster:
                    map_rosters.append(roster)

            roster_lookup[(match_id, map_index)] = map_rosters

    return roster_lookup
