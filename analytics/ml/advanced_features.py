
import pandas as pd
import numpy as np
from collections import Counter


def to_records(value):
    """Convert Parquet array/list values into a list of records."""
    if value is None:
        return []

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, (list, tuple)):
        return list(value)

    return []


def normalize_name(value):
    """Normalize player names for map-local event matching."""
    if value is None:
        return None

    value = str(value).strip()

    return value.casefold() if value else None


def extract_advanced_features(raw_df):
    results = []

    for _, map_row in raw_df.iterrows():

        match_id = str(map_row["match_id"])
        map_index = int(map_row["map_index"])
        map_name = map_row["map_name"]

        players = to_records(map_row["players"])
        kills = to_records(map_row["kills"])

        all_players = [
            player for player in players
            if isinstance(player, dict)
            and player.get("side") == "all"
        ]

        # Build a map-local name-to-Steam-ID mapping.
        name_to_steam_id = {}

        for player in all_players:
            name = player.get("name")
            steam_id = player.get("steamid")

            normalized_name = normalize_name(name)

            if normalized_name is None or steam_id is None:
                continue

            steam_id = str(int(steam_id))

            if (
                normalized_name in name_to_steam_id
                and name_to_steam_id[normalized_name] != steam_id
            ):
                raise ValueError(
                    f"Conflicting Steam IDs for player {name!r} "
                    f"in match {match_id}, map {map_index}"
                )

            name_to_steam_id[normalized_name] = steam_id

        for player in all_players:

            name = player.get("name")
            steam_id = player.get("steamid")

            normalized_name = normalize_name(name)

            if normalized_name is None or steam_id is None:
                continue

            steam_id = str(int(steam_id))

            player_kills = [
                kill for kill in kills
                if normalize_name(kill.get("attacker_name"))
                == normalized_name
            ]

            player_deaths = [
                kill for kill in kills
                if normalize_name(kill.get("victim_name"))
                == normalized_name
            ]

            player_assists = [
                kill for kill in kills
                if normalize_name(kill.get("assister_name"))
                == normalized_name
            ]

            kill_rounds = Counter(
                kill.get("round_num")
                for kill in player_kills
                if kill.get("round_num") is not None
            )

            double_kills = sum(
                count == 2 for count in kill_rounds.values()
            )
            triple_kills = sum(
                count == 3 for count in kill_rounds.values()
            )
            four_kills = sum(
                count == 4 for count in kill_rounds.values()
            )
            aces = sum(
                count >= 5 for count in kill_rounds.values()
            )

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
                    key=lambda event: event.get("tick") or 0
                )

                if not events:
                    continue

                first_kill = events[0]

                if (
                    normalize_name(first_kill.get("attacker_name"))
                    == normalized_name
                ):
                    opening_kills += 1

                if (
                    normalize_name(first_kill.get("victim_name"))
                    == normalized_name
                ):
                    opening_deaths += 1

            weapon_counts = Counter(
                str(kill.get("weapon", "")).lower()
                for kill in player_kills
            )

            headshots = sum(
                bool(kill.get("headshot"))
                for kill in player_kills
            )

            kill_count = len(player_kills)
            death_count = len(player_deaths)

            smoke_kills = sum(
                bool(kill.get("thrusmoke"))
                for kill in player_kills
            )

            noscope_kills = sum(
                bool(kill.get("noscope"))
                for kill in player_kills
            )

            blind_kills = sum(
                bool(kill.get("attackerblind"))
                for kill in player_kills
            )

            wallbang_kills = sum(
                (kill.get("penetrated") or 0) > 0
                for kill in player_kills
            )

            distances = [
                float(kill["distance"])
                for kill in player_kills
                if kill.get("distance") is not None
            ]

            damage_values = [
                float(kill["dmg_health"])
                for kill in player_kills
                if kill.get("dmg_health") is not None
            ]

            awp_kills = weapon_counts.get("awp", 0)

            rifle_kills = sum(
                weapon_counts.get(weapon, 0)
                for weapon in [
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
                weapon_counts.get(weapon, 0)
                for weapon in [
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
                "steam_id": steam_id,
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
                    sum(damage_values) / len(damage_values)
                    if damage_values else 0
                ),

                "advanced_total_kill_damage": sum(damage_values),
            })

    return pd.DataFrame(results)
