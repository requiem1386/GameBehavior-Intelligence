
from pathlib import Path
import pandas as pd

DATASET_PATH = Path("dataset/raw/data")
files = list(DATASET_PATH.glob("*.parquet"))

df = pd.read_parquet(files[0])

print("========== DATASET SUMMARY ==========")
print("Total rows:", len(df))
print("Total columns:", len(df.columns))
print("Unique matches:", df["match_id"].nunique())
print("Unique maps:", df["map_name"].nunique())

print("\n========== MATCH INFORMATION ==========")
print(df[[
    "match_id",
    "hltv_demo_id",
    "match_date",
    "map_index",
    "map_name",
    "team1",
    "team2",
    "score1",
    "score2"
]].head(10).to_string(index=False))

print("\n========== PLAYER STATISTICS ==========")

all_players = []

for _, row in df.iterrows():
    for player in row["players"]:
        player_data = player.copy()
        player_data["match_id"] = row["match_id"]
        player_data["hltv_demo_id"] = row["hltv_demo_id"]
        player_data["map_name"] = row["map_name"]
        player_data["match_date"] = row["match_date"]
        all_players.append(player_data)

players_df = pd.DataFrame(all_players)

print("Total player records:", len(players_df))
print("Unique Steam IDs:", players_df["steamid"].nunique())
print("Unique player names:", players_df["name"].nunique())

print("\n========== PLAYER COLUMNS ==========")
print(players_df.columns.tolist())

print("\n========== MISSING VALUES ==========")
print(players_df.isnull().sum())

print("\n========== PLAYER DATA SAMPLE ==========")
print(players_df.head(5).to_string(index=False))

print("\n========== DUPLICATE CHECK ==========")
print(
    "Duplicate player-map records:",
    players_df.duplicated(
        subset=["steamid", "hltv_demo_id", "map_name"]
    ).sum()
)


print("\n========== DUPLICATE ANALYSIS ==========")

print(
    "Duplicates without side:",
    players_df.duplicated(
        subset=["steamid", "hltv_demo_id", "map_name"]
    ).sum()
)

print(
    "Duplicates with side:",
    players_df.duplicated(
        subset=["steamid", "hltv_demo_id", "map_name", "side"]
    ).sum()
)

print("\n========== SIDE DISTRIBUTION ==========")
print(players_df["side"].value_counts())

print("\n========== PLAYER RECORDS PER MAP ==========")
print(
    players_df.groupby(
        ["hltv_demo_id", "map_name"]
    ).size()
)

print("\n========== MISSING DATA PERCENTAGE ==========")
print(
    (players_df.isnull().mean() * 100).round(2)
)


print("\n========== SIDE DETAILS ==========")

for side in ["ct", "t", "all"]:
    side_df = players_df[players_df["side"] == side]

    print(f"\nSide: {side}")
    print("Records:", len(side_df))
    print("Average kills:", side_df["kills"].mean())
    print("Average ADR:", side_df["adr"].mean())
    print("Average Rating:", side_df["rating"].mean())

print("\n========== SAMPLE PLAYER ==========")

sample_id = players_df.iloc[0]["steamid"]

print(
    players_df[
        players_df["steamid"] == sample_id
    ][[
        "name",
        "side",
        "map_name",
        "kills",
        "deaths",
        "adr",
        "rating"
    ]].to_string(index=False)
)
