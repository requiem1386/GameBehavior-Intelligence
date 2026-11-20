
import numpy as np
import pandas as pd

from analytics.ml.dataset import build_training_dataset


def diagnose_target():

    print("Building dataset...")

    df = build_training_dataset(min_history=3)

    df = df.dropna(
        subset=["match_date", "target_rating", "match_id"]
    ).copy()

    df["match_date"] = pd.to_datetime(
        df["match_date"],
        utc=True
    )

    df = df.sort_values("match_date")

    match_order = (
        df[["match_id", "match_date"]]
        .drop_duplicates("match_id")
        .sort_values("match_date")
    )

    test_start = int(len(match_order) * 0.85)

    test_ids = set(
        match_order.iloc[test_start:]["match_id"]
    )

    test_df = df[df["match_id"].isin(test_ids)]

    print("\n========== TARGET DISTRIBUTION ==========")

    print("\nAll dataset:")
    print(df["target_rating"].describe())

    print("\nTest dataset:")
    print(test_df["target_rating"].describe())

    print("\n========== TARGET QUANTILES ==========")

    print(
        test_df["target_rating"].quantile(
            [0, 0.10, 0.25, 0.50, 0.75, 0.90, 1]
        )
    )

    print("\n========== DATA DIVERSITY ==========")

    print("Unique players:", df["player_id"].nunique())
    print("Unique matches:", df["match_id"].nunique())

    print("\n========== MAP DISTRIBUTION ==========")

    if "map_name" in df.columns:
        print(df["map_name"].value_counts())

    else:
        print("map_name is not present in training dataset.")

    print("\n========== TARGET VARIANCE ==========")

    print(
        "Test target standard deviation:",
        round(test_df["target_rating"].std(), 5)
    )

    print(
        "Test target variance:",
        round(test_df["target_rating"].var(), 5)
    )


if __name__ == "__main__":
    diagnose_target()
