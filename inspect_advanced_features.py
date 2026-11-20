import pandas as pd

df = pd.read_parquet(
    "dataset/processed/advanced_features.parquet"
)

print("Shape:", df.shape)

print("\nColumns:")
print(df.columns.tolist())

print("\nSample:")
print(df[["match_id", "map_index", "player_name"]].head(5))
