# GameBehavior Intelligence

**An AI-powered Counter-Strike 2 player performance analytics and rating prediction platform.**

GameBehavior Intelligence is a Django-based analytics platform designed to analyze Counter-Strike 2 player performance, explore historical match statistics, compare players, extract advanced gameplay features, and predict player ratings using machine learning.

The project combines structured match data, advanced feature engineering, chronological model evaluation, and an interactive analytics dashboard.

## Key Features

- **Player Analytics:** Analyze rating, ADR, KAST, impact, kills, deaths, assists, and headshots.
- **Advanced Gameplay Analytics:** Extract 22 features from kill events, including opening kills, multi-kills, weapon categories, wallbangs, blind kills, and kill distances.
- **Player Comparison:** Compare two players using historical performance statistics.
- **Machine Learning Predictions:** Estimate player ratings using a trained Random Forest regression model.
- **Map-specific Analysis:** Analyze historical player performance across different maps.
- **Steam Profile Integration:** Synchronize available Steam profile information.
- **Interactive Dashboard:** Explore player statistics, performance trends, map performance, comparisons, and predictions.
- **Player Intelligence:** Explore historical performance trends and consistency indicators.
- **Temporal Model Evaluation:** Use chronological training, validation, and test splits to reduce temporal data leakage.

## Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, Django |
| Database | SQLite |
| Machine Learning | Scikit-learn |
| Data Processing | Pandas, NumPy, Polars |
| Data Storage | Parquet, PyArrow |
| Demo Parsing | DemoParser2 |
| Visualization | Matplotlib, Seaborn, Chart.js |
| Frontend | HTML, CSS, JavaScript |
| Model Serialization | Joblib |
| Testing | Django Test Framework |

## Project Architecture

```text
GameBehaviorIntelligence/
|
|-- analytics/
|   |-- ml/
|   |   |-- advanced_features.py
|   |   |-- dataset.py
|   |   |-- team_features.py
|   |   |-- compare_features.py
|   |   |-- train.py
|   |   |-- feature_importance.csv
|   |   `-- best_player_rating_model.joblib
|   |-- tests.py
|   `-- ...
|
|-- config/
|   |-- settings.py
|   |-- urls.py
|   `-- ...
|
|-- data_pipeline/
|   `-- demo_parser.py
|
|-- matches/
|   |-- management/
|   |   `-- commands/
|   |-- models.py
|   `-- ...
|
|-- players/
|   |-- management/
|   |   `-- commands/
|   |-- services/
|   |-- models.py
|   `-- ...
|
|-- predictions/
|   |-- services.py
|   |-- views.py
|   |-- urls.py
|   |-- templates/
|   `-- static/
|
|-- scripts/
|   `-- rebuild_advanced_features.py
|
|-- dataset/
|   |-- raw/
|   `-- processed/
|
|-- manage.py
`-- requirements.txt
```

*Note: Some generated files and local data directories are not included in the Git repository.*

## Dataset

This project uses the Counter-Strike 2 demo dataset:

- **Dataset:** [OpenCS2 Dataset Demo](https://huggingface.co/datasets/blanchon/opencs2_dataset_demo)
- **Format:** Apache Parquet
- **License:** CC-BY-4.0

Raw dataset files are not included in this repository.

Place downloaded Parquet files in:

```text
dataset/raw/data/
```

The processed advanced feature dataset is generated separately:

```text
dataset/processed/advanced_features.parquet
```

Please retain the original dataset attribution and comply with its license.

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/requiem1386/GameBehavior-Intelligence.git

cd GameBehavior-Intelligence
```

### 2. Create a virtual environment

```powershell
python -m venv venv

.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip

pip install -r requirements.txt
```

### 4. Configure the Django secret key

The application reads its secret key from the `DJANGO_SECRET_KEY` environment variable.

If a key is already stored in your Windows user environment:

```powershell
$env:DJANGO_SECRET_KEY = [Environment]::GetEnvironmentVariable("DJANGO_SECRET_KEY", "User")
```

If you do not have one, generate and store a new key:

```powershell
$key = python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

[Environment]::SetEnvironmentVariable("DJANGO_SECRET_KEY", $key, "User")

$env:DJANGO_SECRET_KEY = $key

Remove-Variable key
```

Never commit secret keys or API credentials to Git.

### 5. Apply database migrations

```powershell
python manage.py migrate
```

### 6. Import the dataset

After placing the raw Parquet files in `dataset/raw/data/`, run:

```powershell
python manage.py import_cs2_data
```

### 7. Build advanced gameplay features

```powershell
python scripts/rebuild_advanced_features.py
```

This script extracts advanced player-level gameplay features from the raw dataset and generates the processed Parquet file.

### 8. Train the machine learning model

The trained model artifact is generated locally and is not included in the Git repository.

```powershell
python -m analytics.ml.train
```

The training pipeline builds the dataset, evaluates multiple regression models, selects a model using validation performance, evaluates it on a separate test set, and saves the selected model.

The generated model is saved at:

```text
analytics/ml/best_player_rating_model.joblib
```

### 9. Run the development server

```powershell
python manage.py runserver
```

Open the dashboard:

```text
http://127.0.0.1:8000/
```

## Machine Learning

The project uses regression to estimate player ratings from historical performance.

### Feature Engineering

The training dataset contains **45 input features**, organized into three groups:

- 18 basic historical performance features.
- 22 advanced historical gameplay features.
- 5 map-specific historical performance features.

The advanced feature extraction pipeline generates 22 gameplay features, including:

- Kills, deaths, assists, and headshots.
- Double kills, triple kills, four kills, and aces.
- Opening kills and opening deaths.
- AWP, rifle, and pistol kills.
- Smoke, blind, noscope, and wallbang kills.
- Average and maximum kill distance.
- Damage per kill and total kill damage.

Features are constructed from historical information to avoid using future match data when predicting past observations.

### Models Evaluated

The training pipeline evaluates:

1. Random Forest Regressor
2. Extra Trees Regressor
3. Hist Gradient Boosting Regressor

The selected model is Random Forest Regressor.

### Evaluation Strategy

The dataset is divided chronologically into:

- Training set
- Validation set
- Test set

The model is selected using validation performance and evaluated on a separate test set.

This approach is designed to reduce temporal data leakage and better represent predictions on future matches.

### Current Model Results

Final test results from the current training run:

| Metric | Random Forest | Mean Baseline |
|---|---:|---:|
| MAE | 0.27961 | 0.27978 |
| RMSE | 0.35024 | 0.35061 |
| R² | 0.00033 | -0.00176 |

**Number of input features:** 45

**Important:** The model's improvement over the mean baseline is very small. Its current predictive performance is limited, and these results should not be interpreted as evidence of strong rating prediction accuracy. Further research and model improvements would be required before relying on predictions in real-world decisions.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/predictions/predict/` | GET | Predict a player's rating |
| `/api/predictions/players/<player_id>/overview/` | GET | Retrieve player performance statistics |
| `/api/predictions/compare/` | GET | Compare two players |

### Prediction Example

```text
GET /api/predictions/predict/?player_id=566&map_name=de_dust2
```

The prediction service requires at least three historical maps for the selected player.

### Player Overview Example

```text
GET /api/predictions/players/566/overview/
```

### Player Comparison Example

```text
GET /api/predictions/compare/?player1_id=566&player2_id=567
```

## Testing

Run the complete test suite:

```powershell
python manage.py test
```

The current project test suite contains **66 automated tests**, all of which passed in the final verification.

Additional project checks:

```powershell
python manage.py check

python manage.py makemigrations --check --dry-run
```

## Development Status

The current implementation includes:

- Django backend and database models.
- CS2 dataset import pipeline.
- Advanced gameplay feature extraction.
- Steam ID-based player matching.
- Machine learning training and evaluation pipeline.
- Player rating prediction service.
- Player analytics and comparison APIs.
- Interactive analytics dashboard.
- Player Intelligence analytics.
- Automated application tests.
- Project documentation and GitHub version control.

The current version is complete as a development and portfolio project. Deployment and further predictive model improvements are outside the scope of this release.

## Author

**GameBehavior Intelligence**

GitHub: [requiem1386](https://github.com/requiem1386)

---

Dataset attribution: [OpenCS2 Dataset Demo](https://huggingface.co/datasets/blanchon/opencs2_dataset_demo), CC-BY-4.0.
