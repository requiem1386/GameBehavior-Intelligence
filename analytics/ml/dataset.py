import os
import pandas as pd

from collections import defaultdict
from matches.models import PlayerMapStats
from analytics.ml.team_features import load_team_rosters


ADVANCED_FEATURES = [
    "advanced_kills",
    "advanced_deaths",
    "advanced_assists",
    "advanced_headshots",
    "advanced_hs_rate",
    "advanced_double_kills",
    "advanced_triple_kills",
    "advanced_four_kills",
    "advanced_aces",
    "advanced_opening_kills",
    "advanced_opening_deaths",
    "advanced_awp_kills",
    "advanced_rifle_kills",
    "advanced_pistol_kills",
    "advanced_smoke_kills",
    "advanced_noscope_kills",
    "advanced_blind_kills",
    "advanced_wallbang_kills",
    "advanced_avg_kill_distance",
    "advanced_max_kill_distance",
    "advanced_damage_per_kill",
    "advanced_total_kill_damage",
]


MAP_FEATURES = [
    "prior_map_avg_rating",
    "prior_map_avg_adr",
    "prior_map_avg_kills",
    "prior_map_avg_impact",
    "prior_map_matches_count",
]


TEAM_FEATURES = [
    "prior_team_avg_rating",
    "prior_team_avg_adr",
    "prior_team_avg_impact",
    "prior_teammate_experience",
    "prior_roster_continuity",
]


FEATURES = [
    "prior_avg_adr",
    "prior_avg_rating",
    "prior_avg_impact",
    "prior_avg_kast",
    "prior_last_rating",
    "prior_last_adr",
    "prior_maps_count",
    "prior_avg_kills",
    "prior_avg_deaths",
    "prior_avg_assists",
    "prior_avg_headshots",
    "prior_kd_ratio",
    "prior_rating_std",
    "prior_recent_avg_rating",
    "prior_rating_trend",
    "prior_adr_std",
    "prior_recent_avg_adr",
    "prior_kd_trend",
] + [
    f"prior_avg_{feature}"
    for feature in ADVANCED_FEATURES
] + MAP_FEATURES


def safe_number(value):

    if value is None or pd.isna(value):
        return None

    return float(value)


def average(items, field):

    values = [
        item[field]
        for item in items
        if item.get(field) is not None
    ]

    return sum(values) / len(values) if values else 0.0


def standard_deviation(items, field):

    values = [
        item[field]
        for item in items
        if item.get(field) is not None
    ]

    if len(values) < 2:
        return 0.0

    return float(pd.Series(values).std(ddof=0))


def kd_ratio(items):

    kills = average(items, "kills")
    deaths = average(items, "deaths")

    return kills / deaths if deaths > 0 else 0.0


def load_advanced_features():

    file_path = os.path.join(
        "dataset",
        "processed",
        "advanced_features.parquet"
    )

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            "Advanced features file not found: "
            + file_path
        )

    advanced_df = pd.read_parquet(file_path)

    advanced_lookup = {}

    for row in advanced_df.to_dict("records"):

        key = (
            str(row["match_id"]),
            int(row["map_index"]),
            str(row["steam_id"]),
        )

        advanced_lookup[key] = row

    return advanced_lookup


def team_historical_average(roster, player_history, field):

    values = []

    for teammate_id in roster:

        history = player_history[teammate_id]

        if not history:
            continue

        recent_history = history[-5:]

        values.append(
            average(recent_history, field)
        )

    return (
        sum(values) / len(values)
        if values else 0.0
    )


def build_training_dataset(min_history=3):

    advanced_lookup = load_advanced_features()

    team_rosters = load_team_rosters()

    # Collect CT and T combat statistics.
    side_stats = (
        PlayerMapStats.objects
        .filter(side__in=["ct", "t"])
        .only(
            "player_id",
            "map_id",
            "kills",
            "deaths",
            "assists",
            "headshots",
        )
    )

    map_combat_stats = defaultdict(
        lambda: {
            "kills": [],
            "deaths": [],
            "assists": [],
            "headshots": [],
        }
    )

    for stat in side_stats:

        key = (stat.player_id, stat.map_id)

        for field in [
            "kills",
            "deaths",
            "assists",
            "headshots",
        ]:

            value = safe_number(
                getattr(stat, field)
            )

            if value is not None:
                map_combat_stats[key][field].append(value)

    # Combine CT and T statistics.
    for key, values in map_combat_stats.items():

        for field, numbers in values.items():

            values[field] = (
                sum(numbers) if numbers else None
            )

    # Get overall player statistics.
    stats = list(
        PlayerMapStats.objects
        .filter(side="all")
        .select_related(
            "player",
            "map",
            "map__match"
        )
        .order_by(
            "map__match__match_date",
            "map__match_id",
            "map__map_index",
            "player_id",
        )
    )

    # Group maps by match series.
    matches = defaultdict(list)

    for stat in stats:
        matches[stat.map.match_id].append(stat)

    # General history for each player.
    player_history = defaultdict(list)

    # Separate history for each player and map.
    player_map_history = defaultdict(list)

    # Number of previous maps played together by each pair.
    teammate_history = defaultdict(int)

    samples = []

    # Process matches chronologically.
    for match_id, match_stats in sorted(
        matches.items(),
        key=lambda item: (
            item[1][0].map.match.match_date,
            str(item[0]),
        )
    ):

        current_match_updates = defaultdict(list)

        current_match_map_updates = defaultdict(list)

        # Store each map roster only once.
        current_match_roster_updates = {}

        # Generate samples before updating histories.
        for stat in match_stats:

            player_id = stat.player_id
            map_name = stat.map.map_name

            history = player_history[player_id]

            map_history = player_map_history[
                (player_id, map_name)
            ]

            target = safe_number(stat.rating)
            match_date = stat.map.match.match_date

            combat = map_combat_stats.get(
                (player_id, stat.map_id),
                {}
            )

            current = {

                "kills": combat.get("kills"),
                "deaths": combat.get("deaths"),
                "assists": combat.get("assists"),
                "headshots": combat.get("headshots"),

                "adr": safe_number(stat.adr),
                "rating": target,
                "impact": safe_number(stat.impact),
                "kast": safe_number(stat.kast),
            }

            # Find advanced features for this player and map.
            advanced_key = (
                str(stat.map.match.match_id),
                int(stat.map.map_index),
                str(stat.player.steam_id),
            )

            advanced_record = advanced_lookup.get(
                advanced_key,
                {}
            )

            # Add advanced statistics to current map record.
            for feature in ADVANCED_FEATURES:

                value = safe_number(
                    advanced_record.get(feature)
                )

                current[feature] = (
                    value if value is not None else 0.0
                )

            # Queue current map for future history.
            current_match_updates[player_id].append(
                current
            )

            current_match_map_updates[
                (player_id, map_name)
            ].append(current)

            # Resolve the current player's team roster.
            roster_key = (
                str(stat.map.match.match_id),
                int(stat.map.map_index),
            )

            map_rosters = team_rosters.get(
                roster_key,
                []
            )

            current_match_roster_updates[
                roster_key
            ] = map_rosters

            player_roster = next(
                (
                    roster
                    for roster in map_rosters
                    if player_id in roster
                ),
                set()
            )

            teammates = (
                player_roster - {player_id}
            )

            # Historical team strength.
            team_avg_rating = team_historical_average(
                player_roster,
                player_history,
                "rating",
            )

            team_avg_adr = team_historical_average(
                player_roster,
                player_history,
                "adr",
            )

            team_avg_impact = team_historical_average(
                player_roster,
                player_history,
                "impact",
            )

            # Previous shared maps with current teammates.
            teammate_counts = [
                teammate_history[
                    tuple(sorted((player_id, teammate_id)))
                ]
                for teammate_id in teammates
            ]

            teammate_experience = (
                sum(teammate_counts) / len(teammate_counts)
                if teammate_counts else 0.0
            )

            roster_continuity = (
                sum(
                    count > 0
                    for count in teammate_counts
                ) / len(teammate_counts)
                if teammate_counts else 0.0
            )

            if len(history) < min_history or target is None:
                continue

            # General historical features.
            recent = history[-5:]
            recent_three = history[-3:]
            previous_three = history[-6:-3]

            avg_kills = average(recent, "kills")
            avg_deaths = average(recent, "deaths")

            current_kd = (
                avg_kills / avg_deaths
                if avg_deaths > 0 else 0.0
            )

            recent_rating = average(
                recent_three,
                "rating"
            )

            recent_adr = average(
                recent_three,
                "adr"
            )

            rating_trend = 0.0
            kd_trend = 0.0

            if len(previous_three) == 3:

                previous_rating = average(
                    previous_three,
                    "rating"
                )

                previous_kd = kd_ratio(
                    previous_three
                )

                rating_trend = (
                    recent_rating - previous_rating
                )

                recent_kd = kd_ratio(
                    recent_three
                )

                kd_trend = (
                    recent_kd - previous_kd
                )

            # Map-specific historical features.
            map_recent = map_history[-5:]

            sample = {

                "prior_avg_adr": average(
                    recent, "adr"
                ),

                "prior_avg_rating": average(
                    recent, "rating"
                ),

                "prior_avg_impact": average(
                    recent, "impact"
                ),

                "prior_avg_kast": average(
                    recent, "kast"
                ),

                "prior_last_rating": (
                    history[-1]["rating"] or 0.0
                ),

                "prior_last_adr": (
                    history[-1]["adr"] or 0.0
                ),

                "prior_maps_count": len(history),

                "prior_avg_kills": avg_kills,
                "prior_avg_deaths": avg_deaths,

                "prior_avg_assists": average(
                    recent, "assists"
                ),

                "prior_avg_headshots": average(
                    recent, "headshots"
                ),

                "prior_kd_ratio": current_kd,

                "prior_rating_std": standard_deviation(
                    recent, "rating"
                ),

                "prior_recent_avg_rating": recent_rating,

                "prior_rating_trend": rating_trend,

                "prior_adr_std": standard_deviation(
                    recent, "adr"
                ),

                "prior_recent_avg_adr": recent_adr,

                "prior_kd_trend": kd_trend,

                # Map-specific features.
                "prior_map_avg_rating": average(
                    map_recent, "rating"
                ),

                "prior_map_avg_adr": average(
                    map_recent, "adr"
                ),

                "prior_map_avg_kills": average(
                    map_recent, "kills"
                ),

                "prior_map_avg_impact": average(
                    map_recent, "impact"
                ),

                "prior_map_matches_count": len(map_history),

                # Team historical features.
                "prior_team_avg_rating": team_avg_rating,

                "prior_team_avg_adr": team_avg_adr,

                "prior_team_avg_impact": team_avg_impact,

                "prior_teammate_experience": teammate_experience,

                "prior_roster_continuity": roster_continuity,

                "target_rating": target,
                "match_date": match_date,
                "match_id": match_id,
                "player_id": player_id,
                "map_name": map_name,
            }

            # Historical averages of advanced features.
            for feature in ADVANCED_FEATURES:

                sample[f"prior_avg_{feature}"] = average(
                    recent,
                    feature
                )

            samples.append(sample)

        # Update player histories after the entire match series.
        for player_id, updates in current_match_updates.items():

            player_history[player_id].extend(updates)

        for key, updates in current_match_map_updates.items():

            player_map_history[key].extend(updates)

        # Update teammate history after the entire series.
        # Each map contributes exactly one shared-map count.
        for map_rosters in current_match_roster_updates.values():

            for roster in map_rosters:

                roster_players = sorted(roster)

                for index, player_id in enumerate(roster_players):

                    for teammate_id in roster_players[index + 1:]:

                        pair = (
                            player_id,
                            teammate_id,
                        )

                        teammate_history[pair] += 1

    df = pd.DataFrame(samples)

    if df.empty:

        raise ValueError(
            "No training samples found."
        )

    df["match_date"] = pd.to_datetime(
        df["match_date"]
    )

    df = (
        df
        .sort_values(
            ["match_date", "match_id", "player_id"]
        )
        .reset_index(drop=True)
    )

    return df
