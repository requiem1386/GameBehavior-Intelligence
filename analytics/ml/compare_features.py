
import numpy as np
import pandas as pd

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from analytics.ml.dataset import (
    build_training_dataset,
    FEATURES,
)


def evaluate(y_true, predictions):
    return {
        "MAE": mean_absolute_error(y_true, predictions),
        "RMSE": np.sqrt(mean_squared_error(y_true, predictions)),
        "R2": r2_score(y_true, predictions),
    }


def compare_features():

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

    # Chronological split by match series
    match_order = (
        df[["match_id", "match_date"]]
        .drop_duplicates("match_id")
        .sort_values("match_date")
    )

    total_matches = len(match_order)

    train_end = int(total_matches * 0.70)
    validation_end = int(total_matches * 0.85)

    train_ids = set(
        match_order.iloc[:train_end]["match_id"]
    )

    validation_ids = set(
        match_order.iloc[train_end:validation_end]["match_id"]
    )

    test_ids = set(
        match_order.iloc[validation_end:]["match_id"]
    )

    train_df = df[df["match_id"].isin(train_ids)]
    validation_df = df[df["match_id"].isin(validation_ids)]
    test_df = df[df["match_id"].isin(test_ids)]

    # Train on train + validation, evaluate on future test
    train_validation_df = pd.concat(
        [train_df, validation_df],
        ignore_index=True
    )

    # Separate feature groups
    advanced_features = [
        f for f in FEATURES
        if f.startswith("prior_avg_advanced_")
    ]

    map_features = [
        f for f in FEATURES
        if f.startswith("prior_map_")
    ]

    basic_features = [
        f for f in FEATURES
        if f not in advanced_features
        and f not in map_features
    ]

    basic_advanced_features = (
        basic_features + advanced_features
    )

    all_features = (
        basic_features
        + advanced_features
        + map_features
    )

    # Verify feature groups
    assert len(basic_features) == 18, (
        f"Expected 18 basic features, got {len(basic_features)}"
    )

    assert len(advanced_features) == 22, (
        f"Expected 22 advanced features, got {len(advanced_features)}"
    )

    assert len(map_features) == 5, (
        f"Expected 5 map features, got {len(map_features)}"
    )

    assert len(all_features) == len(FEATURES), (
        "Feature groups do not match FEATURES"
    )

    print("\n========== DATA SPLIT ==========")
    print("Total matches:", total_matches)
    print("Train matches:", len(train_ids))
    print("Validation matches:", len(validation_ids))
    print("Test matches:", len(test_ids))

    print("\n========== FEATURE SETS ==========")
    print("Basic:", len(basic_features))
    print("Basic + Advanced:", len(basic_advanced_features))
    print("Basic + Advanced + Map:", len(all_features))

    # Prepare target
    y_train = train_validation_df["target_rating"]
    y_test = test_df["target_rating"]

    model_settings = {
        "n_estimators": 300,
        "max_depth": 15,
        "min_samples_leaf": 3,
        "random_state": 42,
        "n_jobs": -1,
    }

    feature_sets = {
        "Basic (18)": basic_features,
        "Basic + Advanced (40)": basic_advanced_features,
        "Basic + Advanced + Map (45)": all_features,
    }

    results = {}

    # Train and evaluate each feature set
    for name, features in feature_sets.items():

        print(f"\nTraining: {name}")

        X_train = train_validation_df[features]
        X_test = test_df[features]

        model = ExtraTreesRegressor(
            **model_settings
        )

        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        metrics = evaluate(
            y_test,
            predictions
        )

        results[name] = metrics

        print("Results:", metrics)

    # Mean baseline
    baseline = np.full(
        len(y_test),
        y_train.mean()
    )

    baseline_metrics = evaluate(
        y_test,
        baseline
    )

    results["Baseline"] = baseline_metrics

    # Final comparison
    print("\n========== FINAL COMPARISON ==========")

    results_df = pd.DataFrame(results).T

    print(results_df.round(6))

    # Improvements
    basic_mae = results["Basic (18)"]["MAE"]
    advanced_mae = results["Basic + Advanced (40)"]["MAE"]
    map_mae = results["Basic + Advanced + Map (45)"]["MAE"]

    basic_rmse = results["Basic (18)"]["RMSE"]
    advanced_rmse = results["Basic + Advanced (40)"]["RMSE"]
    map_rmse = results["Basic + Advanced + Map (45)"]["RMSE"]

    print("\n========== FEATURE IMPACT ==========")

    print("\nAdvanced feature impact:")
    print(
        "MAE improvement:",
        round(basic_mae - advanced_mae, 6)
    )
    print(
        "RMSE improvement:",
        round(basic_rmse - advanced_rmse, 6)
    )

    print("\nMap feature impact:")
    print(
        "MAE improvement:",
        round(advanced_mae - map_mae, 6)
    )
    print(
        "RMSE improvement:",
        round(advanced_rmse - map_rmse, 6)
    )

    print("\nTotal improvement over basic:")
    print(
        "MAE improvement:",
        round(basic_mae - map_mae, 6)
    )
    print(
        "RMSE improvement:",
        round(basic_rmse - map_rmse, 6)
    )


if __name__ == "__main__":
    compare_features()
