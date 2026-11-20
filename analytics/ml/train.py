
import os
import django
import joblib
import numpy as np
import pandas as pd

# Initialize Django before importing application models.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()

from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
)

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.inspection import permutation_importance

from analytics.ml.dataset import (
    build_training_dataset,
    FEATURES,
)


MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "best_player_rating_model.joblib",
)


def create_models():

    return {
        "Random Forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=15,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        ),

        "Extra Trees": ExtraTreesRegressor(
            n_estimators=300,
            max_depth=15,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        ),

        "Hist Gradient Boosting": HistGradientBoostingRegressor(
            max_iter=300,
            learning_rate=0.05,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=42,
        ),
    }


def evaluate_model(y_true, predictions):

    return {
        "mae": mean_absolute_error(
            y_true, predictions
        ),

        "rmse": np.sqrt(
            mean_squared_error(
                y_true, predictions
            )
        ),

        "r2": r2_score(
            y_true, predictions
        ),
    }


def print_metrics(name, metrics):

    print(
        name,
        "| MAE:", round(metrics["mae"], 5),
        "| RMSE:", round(metrics["rmse"], 5),
        "| R2:", round(metrics["r2"], 5),
    )


def train_model():

    print("Building dataset...")

    df = build_training_dataset(
        min_history=3
    )

    df = df.dropna(
        subset=[
            "match_date",
            "target_rating",
            "match_id",
        ]
    ).copy()

    df["match_date"] = pd.to_datetime(
        df["match_date"]
    )

    df = df.sort_values(
        ["match_date", "match_id"]
    ).reset_index(drop=True)

    # Chronological split by complete match series.
    match_order = (
        df[["match_id", "match_date"]]
        .drop_duplicates(subset=["match_id"])
        .sort_values(
            ["match_date", "match_id"]
        )
        .reset_index(drop=True)
    )

    total_matches = len(match_order)

    train_end = int(total_matches * 0.70)
    validation_end = int(total_matches * 0.85)

    train_match_ids = set(
        match_order.iloc[:train_end]["match_id"]
    )

    validation_match_ids = set(
        match_order.iloc[
            train_end:validation_end
        ]["match_id"]
    )

    test_match_ids = set(
        match_order.iloc[
            validation_end:
        ]["match_id"]
    )

    train_df = df[
        df["match_id"].isin(train_match_ids)
    ].copy()

    validation_df = df[
        df["match_id"].isin(validation_match_ids)
    ].copy()

    test_df = df[
        df["match_id"].isin(test_match_ids)
    ].copy()
    # Validate chronological split boundaries.
    if not (
    train_df["match_date"].max()
    < validation_df["match_date"].min()
):
      raise ValueError(
        "Temporal leakage detected between Train and Validation."
    )

    if not (
    validation_df["match_date"].max()
    < test_df["match_date"].min()
):
      raise ValueError(
        "Temporal leakage detected between Validation and Test."
    )

    if train_df.empty or validation_df.empty or test_df.empty:
        raise ValueError(
            "One of the chronological datasets is empty."
        )

    print("\n========== TEMPORAL SPLIT ==========")

    print("Total matches:", total_matches)

    print("Training matches:", len(train_match_ids))
    print("Validation matches:", len(validation_match_ids))
    print("Testing matches:", len(test_match_ids))

    print("\nTraining samples:", len(train_df))
    print("Validation samples:", len(validation_df))
    print("Testing samples:", len(test_df))

    print("\nTraining period:")
    print(train_df["match_date"].min(), "to",
          train_df["match_date"].max())

    print("\nValidation period:")
    print(validation_df["match_date"].min(), "to",
          validation_df["match_date"].max())

    print("\nTesting period:")
    print(test_df["match_date"].min(), "to",
          test_df["match_date"].max())

    print("\nNumber of features:", len(FEATURES))

    # Prepare feature matrices.
    X_train = train_df[FEATURES]
    y_train = train_df["target_rating"]

    X_validation = validation_df[FEATURES]
    y_validation = validation_df["target_rating"]

    X_test = test_df[FEATURES]
    y_test = test_df["target_rating"]

    # Baseline on validation.
    validation_baseline = np.full(
        len(y_validation),
        y_train.mean()
    )

    validation_baseline_metrics = evaluate_model(
        y_validation,
        validation_baseline
    )

    print("\n========== VALIDATION BASELINE ==========")

    print_metrics(
        "Training mean baseline",
        validation_baseline_metrics
    )

    # Train candidate models on training data.
    models = create_models()

    validation_results = []

    best_name = None
    best_validation_mae = float("inf")

    print("\n========== MODEL TRAINING ==========")

    for name, model in models.items():

        print("\nTraining:", name)

        model.fit(
            X_train,
            y_train
        )

        predictions = model.predict(
            X_validation
        )

        metrics = evaluate_model(
            y_validation,
            predictions
        )

        print_metrics(
            name,
            metrics
        )

        validation_results.append({
            "name": name,
            **metrics,
        })

        if metrics["mae"] < best_validation_mae:

            best_validation_mae = metrics["mae"]
            best_name = name

    print("\n========== VALIDATION COMPARISON ==========")

    for result in sorted(
        validation_results,
        key=lambda item: item["mae"]
    ):

        print_metrics(
            result["name"],
            result
        )

    print("\nSelected model:", best_name)
    # Analyze feature importance using validation data.
    print("\n========== PERMUTATION FEATURE IMPORTANCE ==========")

    selected_model = models[best_name]

    importance_result = permutation_importance(
        selected_model,
        X_validation,
        y_validation,
        scoring="neg_mean_absolute_error",
        n_repeats=10,
        random_state=42,
        n_jobs=-1,
    )

    importance_df = pd.DataFrame({
        "feature": FEATURES,
        "importance_mean": importance_result.importances_mean,
        "importance_std": importance_result.importances_std,
    }).sort_values(
        "importance_mean",
        ascending=False,
    )

    print("\nTop 15 important features:")

    print(
        importance_df.head(15).to_string(
            index=False,
            float_format=lambda value: f"{value:.6f}",
        )
    )

    importance_path = os.path.join(
        os.path.dirname(__file__),
        "feature_importance.csv",
    )

    importance_df.to_csv(
        importance_path,
        index=False,
    )

    print("\nFeature importance saved to:")
    print(importance_path)
    # Refit the selected model on Train + Validation.
    train_validation_df = pd.concat(
        [train_df, validation_df],
        ignore_index=True
    )

    X_train_validation = train_validation_df[FEATURES]
    y_train_validation = train_validation_df["target_rating"]

    final_model = create_models()[best_name]

    print("\nRefitting selected model on Train + Validation...")

    final_model.fit(
        X_train_validation,
        y_train_validation
    )

    # Final evaluation on untouched Test.
    test_predictions = final_model.predict(
        X_test
    )

    test_metrics = evaluate_model(
        y_test,
        test_predictions
    )

    # Test baseline uses Train + Validation mean.
    test_baseline_predictions = np.full(
        len(y_test),
        y_train_validation.mean()
    )

    test_baseline_metrics = evaluate_model(
        y_test,
        test_baseline_predictions
    )

    print("\n========== FINAL TEST RESULTS ==========")

    print_metrics(
        "Selected ML model",
        test_metrics
    )

    print_metrics(
        "Train + Validation mean baseline",
        test_baseline_metrics
    )

    print("\n========== FINAL COMPARISON ==========")

    print(
        "MAE improvement over baseline:",
        round(
            test_baseline_metrics["mae"]
            - test_metrics["mae"],
            5
        )
    )

    # Save model and evaluation metadata.
    model_data = {

        "model": final_model,

        "features": FEATURES,

        "model_name": best_name,

        "mae": test_metrics["mae"],
        "rmse": test_metrics["rmse"],
        "r2": test_metrics["r2"],

        "validation_results": validation_results,

        "validation_baseline": validation_baseline_metrics,

        "test_metrics": test_metrics,

        "test_baseline": test_baseline_metrics,

        "feature_count": len(FEATURES),

        "split": {
            "train_matches": len(train_match_ids),
            "validation_matches": len(validation_match_ids),
            "test_matches": len(test_match_ids),
        },
    }

    joblib.dump(
        model_data,
        MODEL_PATH
    )

    print("\nModel saved to:")
    print(MODEL_PATH)

    return final_model


if __name__ == "__main__":
    train_model()
