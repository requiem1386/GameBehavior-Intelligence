
import sys
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

RAW_DIR = BASE_DIR / "dataset" / "raw" / "data"
OUTPUT_DIR = BASE_DIR / "dataset" / "processed"

OUTPUT_FILE = OUTPUT_DIR / "advanced_features.parquet"
TEMP_FILE = OUTPUT_DIR / "advanced_features.tmp.parquet"


from analytics.ml.advanced_features import extract_advanced_features


# --------------------------------------------------
# Main builder
# --------------------------------------------------

def main():

    files = sorted(RAW_DIR.glob("*.parquet"))

    if not files:
        raise FileNotFoundError(
            f"No Parquet files found in {RAW_DIR}"
        )

    print(f"Found {len(files)} raw files.")

    results = []

    # Extract features from all raw files.
    for index, file_path in enumerate(files, start=1):

        print(
            f"[{index}/{len(files)}] "
            f"Processing {file_path.name}"
        )

        raw_df = pd.read_parquet(file_path)

        extracted = extract_advanced_features(raw_df)

        if not extracted.empty:
            results.append(extracted)

    if not results:
        raise RuntimeError(
            "No advanced features were extracted."
        )

    # Combine extracted features.
    final_df = pd.concat(
        results,
        ignore_index=True
    )

    # --------------------------------------------------
    # Validate required columns
    # --------------------------------------------------

    required_columns = {
        "match_id",
        "map_index",
        "map_name",
        "steam_id",
        "player_name",
    }

    missing_columns = (
        required_columns - set(final_df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing_columns)}"
        )

    # --------------------------------------------------
    # Validate Steam IDs
    # --------------------------------------------------

    if final_df["steam_id"].isna().any():
        raise ValueError(
            "Some extracted rows have missing Steam IDs."
        )

    final_df["steam_id"] = (
        final_df["steam_id"].astype(str).str.strip()
    )

    if final_df["steam_id"].eq("").any():
        raise ValueError(
            "Some extracted rows have empty Steam IDs."
        )

    # --------------------------------------------------
    # Normalize player names
    # --------------------------------------------------

    final_df["player_name"] = (
        final_df["player_name"]
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------
    # Duplicate validation and removal
    # --------------------------------------------------

    key_columns = [
        "match_id",
        "map_index",
        "steam_id",
    ]

    duplicate_mask = final_df.duplicated(
        subset=key_columns,
        keep=False
    )

    duplicate_groups = (
        final_df.loc[duplicate_mask]
        .groupby(key_columns, dropna=False)
    )

    # Only remove duplicates when every feature value
    # is identical within each player-map group.
    excluded_columns = key_columns + [
        "player_name",
        "map_name",
    ]

    feature_columns = [
        column
        for column in final_df.columns
        if column not in excluded_columns
    ]

    for key, group in duplicate_groups:

        differing_columns = [
            column
            for column in feature_columns
            if group[column].nunique(dropna=False) > 1
        ]

        normalized_names = (
            group["player_name"]
            .str.casefold()
            .unique()
        )

        normalized_maps = (
            group["map_name"]
            .astype(str)
            .str.strip()
            .str.casefold()
            .unique()
        )

        if differing_columns:
            raise ValueError(
                f"Conflicting feature values for key {key}. "
                f"Different columns: {differing_columns}"
            )

        if len(normalized_names) > 1:
            raise ValueError(
                f"Conflicting player names for key {key}: "
                f"{normalized_names.tolist()}"
            )

        if len(normalized_maps) > 1:
            raise ValueError(
                f"Conflicting map names for key {key}: "
                f"{normalized_maps.tolist()}"
            )

    before_deduplication = len(final_df)

    final_df = final_df.drop_duplicates(
        subset=key_columns,
        keep="first",
    ).reset_index(drop=True)

    removed_duplicates = (
        before_deduplication - len(final_df)
    )

    duplicate_count = final_df.duplicated(
        subset=key_columns
    ).sum()

    if duplicate_count:
        raise ValueError(
            f"Duplicate keys remain: {duplicate_count}"
        )

    # --------------------------------------------------
    # Save and verify
    # --------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    final_df.to_parquet(
        TEMP_FILE,
        index=False
    )

    verification_df = pd.read_parquet(TEMP_FILE)

    if len(verification_df) != len(final_df):
        raise RuntimeError(
            "Parquet verification row count mismatch."
        )

    if list(verification_df.columns) != list(final_df.columns):
        raise RuntimeError(
            "Parquet verification column mismatch."
        )

    if verification_df["steam_id"].isna().any():
        raise RuntimeError(
            "Steam IDs became null after saving."
        )

    if verification_df.duplicated(
        subset=key_columns
    ).any():
        raise RuntimeError(
            "Duplicate keys detected after saving."
        )

    # Replace the old file only after successful verification.
    TEMP_FILE.replace(OUTPUT_FILE)

    # --------------------------------------------------
    # Build summary
    # --------------------------------------------------

    print("\n========== BUILD SUMMARY ==========")

    print(f"Raw files processed: {len(files)}")
    print(f"Final rows: {len(final_df)}")
    print(f"Removed duplicate rows: {removed_duplicates}")
    print(f"Columns: {len(final_df.columns)}")
    print(
        f"Unique Steam IDs: "
        f"{final_df['steam_id'].nunique()}"
    )
    print(f"Duplicate keys: {duplicate_count}")
    print(f"Output: {OUTPUT_FILE}")

    print("\nBuild completed successfully.")


if __name__ == "__main__":
    main()
