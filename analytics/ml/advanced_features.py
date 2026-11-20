
import pandas as pd
import numpy as np
from collections import Counter


def to_records(value):
    """Convert Parquet array/list values into a list of dictionaries."""
    if value is None:
        return []

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, list):
        return value

    return []


def extract_advanced_features(raw_df):
    results = []

    for _, map_row in raw_df.iterrows():

        match_id = str(map_row["match_id"])
        map_index = int(map_row["map_index"])
        map_name = map_row["map_name"]

        players = to_records(map_row["players"])
        kills = to_records(map_row["kills"])
        rounds = to_records(map_row["rounds"])

        # Only use the "all" player records as the player list.
        all_players = [
            p for p in players
            if p.get("side") == "all"
        ]

        for player in all_players:

            name = player.get("name")

            if not name:
                continue

            player_kills = [
                k for k in kills
                if k.get("attacker_name") == name
            ]

            player_deaths = [
                k for k in kills
                if k.get("victim_name") == name
            ]

            player_assists = [
                k for k in kills
                if k.get("assister_name") == name
            ]

            # Kills per round
            kill_rounds = Counter(
                k.get("round_num")
                for k in player_kills
                if k.get("round_num") is not None
            )

            # Multi-kill rounds
            double_kills = sum(v == 2 for v in kill_rounds.values())
            triple_kills = sum(v == 3 for v in kill_rounds.values())
            four_kills = sum(v == 4 for v in kill_rounds.values())
            aces = sum(v >= 5 for v in kill_rounds.values())

            # Opening duels
            opening_kills = 0
            opening_deaths = 0

            round_events = {}

            for kill in kills:
                round_num = kill.get("round_num")

                if round_num is None:
                    continue

                round_events.setdefault(round_num, []).append(kill)

            for events in round_events.values():

                events = sorted(
                    events,
                    key=lambda x: x.get("tick") or 0
                )

                if not events:
                    continue

                first_kill = events[0]

                if first_kill.get("attacker_name") == name:
                    opening_kills += 1

                if first_kill.get("victim_name") == name:
                    opening_deaths += 1

            # Weapon statistics
            weapon_counts = Counter(
                str(k.get("weapon", "")).lower()
                for k in player_kills
            )

            headshots = sum(
                bool(k.get("headshot"))
                for k in player_kills
            )

            kill_count = len(player_kills)
            death_count = len(player_deaths)

            # Special kill events
            smoke_kills = sum(
                bool(k.get("thrusmoke"))
                for k in player_kills
            )

            noscope_kills = sum(
                bool(k.get("noscope"))
                for k in player_kills
            )

            blind_kills = sum(
                bool(k.get("attackerblind"))
                for k in player_kills
            )

            wallbang_kills = sum(
                (k.get("penetrated") or 0) > 0
                for k in player_kills
            )

            distances = [
                float(k["distance"])
                for k in player_kills
                if k.get("distance") is not None
            ]

            damage_values = [
                float(k["dmg_health"])
                for k in player_kills
                if k.get("dmg_health") is not None
            ]

            # Weapon categories
            awp_kills = weapon_counts.get("awp", 0)

            rifle_kills = sum(
                weapon_counts.get(w, 0)
                for w in [
                    "ak47",
                    "m4a1",
                    "m4a1_silencer",
                    "aug",
                    "sg556",
                    "famas",
                    "galilar",
                ]
            )

            pistol_kills = sum(
                weapon_counts.get(w, 0)
                for w in [
                    "glock",
                    "usp_silencer",
                    "hkp2000",
                    "p250",
                    "deagle",
                    "revolver",
                    "elite",
                    "tec9",
                    "fiveseven",
                    "cz75a",
                ]
            )

            results.append({

                "match_id": match_id,
                "map_index": map_index,
                "map_name": map_name,
                "player_name": name,

                "advanced_kills": kill_count,
                "advanced_deaths": death_count,
                "advanced_assists": len(player_assists),

                "advanced_headshots": headshots,
                "advanced_hs_rate": (
                    headshots / kill_count
                    if kill_count > 0 else 0
                ),

                "advanced_double_kills": double_kills,
                "advanced_triple_kills": triple_kills,
                "advanced_four_kills": four_kills,
                "advanced_aces": aces,

                "advanced_opening_kills": opening_kills,
                "advanced_opening_deaths": opening_deaths,

                "advanced_awp_kills": awp_kills,
                "advanced_rifle_kills": rifle_kills,
                "advanced_pistol_kills": pistol_kills,

                "advanced_smoke_kills": smoke_kills,
                "advanced_noscope_kills": noscope_kills,
                "advanced_blind_kills": blind_kills,
                "advanced_wallbang_kills": wallbang_kills,

                "advanced_avg_kill_distance": (
                    np.mean(distances) if distances else 0
                ),

                "advanced_max_kill_distance": (
                    max(distances) if distances else 0
                ),

                "advanced_damage_per_kill": (
                    sum(damage_values) / kill_count
                    if kill_count > 0 else 0
                ),

                "advanced_total_kill_damage": sum(damage_values),

            })

    return pd.DataFrame(results)
