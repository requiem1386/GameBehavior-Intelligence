# GameBehavior Intelligence

**An AI-powered Counter-Strike 2 player performance analytics and rating prediction platform.**

GameBehavior Intelligence is a Django-based analytics platform designed to analyze Counter-Strike 2 player performance, explore historical match statistics, compare players, extract advanced gameplay features, and predict player ratings using machine learning.

The project combines structured match data, advanced feature engineering, temporal model evaluation, and an interactive dashboard.

## Key Features

- **Player Analytics:** Analyze player performance, rating, ADR, KAST, impact, kills, deaths, assists, and headshots.
- **Advanced Gameplay Analytics:** Extract 22 features from kill events, including opening kills, multi-kills, weapon categories, wallbangs, blind kills, and kill distances.
- **Player Comparison:** Compare two players using historical performance statistics.
- **Machine Learning Predictions:** Predict player ratings using a trained regression model.
- **Map-specific Analysis:** Analyze player performance across different maps.
- **Steam Profile Integration:** Synchronize available Steam profile information.
- **Interactive Dashboard:** Explore player statistics, performance trends, map performance, comparisons, and predictions.
- **Temporal Model Evaluation:** Use chronological train, validation, and test splits to reduce temporal data leakage.

## Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, Django |
| Database | SQLite (development) |
| Machine Learning | Scikit-learn |
| Data Processing | Pandas, NumPy, Polars |
| Data Storage | Parquet, PyArrow |
| Demo Parsing | DemoParser2 |
| Visualization | Matplotlib, Seaborn |
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
|   |   `-- train.py
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
|   |       |-- import_cs2_data.py
|   |       `-- inspect_cs2_dataset.py
|   |-- models.py
|   `-- ...
|
|-- players/
|   |-- management/
|   |   `-- commands/
|   |       `-- sync_steam_profiles.py
|   |-- services/
|   |   `-- steam.py
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

## Dataset

This project uses the Counter-Strike 2 demo dataset:

- **Dataset:** [OpenCS2 Dataset Demo](https://huggingface.co/datasets/blanchon/opencs2_dataset_demo)
- **Format:** Apache Parquet
- **License:** CC-BY-4.0

Raw dataset files are not included in this repository.

Place the downloaded Parquet files in:

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

```bash
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

If you already have a key stored in your Windows user environment:

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
python analytics/ml/train.py
```

The training pipeline compares multiple regression models, selects a model based on validation performance, evaluates it on an untouched test set, and saves the resulting model artifact.

### 9. Run the development server

```powershell
python manage.py runserver
```

Open the dashboard:

```text
http://127.0.0.1:8000/
```

## Machine Learning

The project uses a regression approach to estimate player ratings from historical performance.

### Feature Engineering

The training dataset contains **45 input features**, including:

- Historical performance averages
- Recent performance indicators
- Player consistency statistics
- Map-specific historical performance
- Advanced kill-event statistics

The advanced feature extraction pipeline generates 22 gameplay features, including:

- Kills, deaths, assists, and headshots
- Double kills, triple kills, four kills, and aces
- Opening kills and opening deaths
- AWP, rifle, and pistol kills
- Smoke, blind, noscope, and wallbang kills
- Average and maximum kill distance
- Damage per kill and total kill damage

### Models Evaluated

The training pipeline evaluates:

1. Random Forest Regressor
2. Extra Trees Regressor
3. Hist Gradient Boosting Regressor

### Evaluation Strategy

The dataset is divided chronologically into:

- Training set
- Validation set
- Test set

The model is selected using validation performance and evaluated on a separate test set.

This approach is designed to prevent future match information from leaking into historical training features.

### Current Model Results

The current selected model is Random Forest Regressor.

| Metric | Test Result |
|---|---:|
| MAE | 0.27961 |
| RMSE | 0.35024 |
| RÂ² | 0.00033 |
| Number of Features | 45 |

**Important:** The current model's improvement over the mean baseline is very small. These results are presented transparently; further feature engineering, target analysis, and model optimization are needed before claiming meaningful predictive performance.

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
python manage.py test -v 2
```

The project has previously passed **66 automated tests** across its Django applications.

## Development Status

The project currently includes:

- Django backend and database models
- CS2 dataset import pipeline
- Advanced gameplay feature extraction
- Steam ID-based player matching
- Machine learning training and evaluation pipeline
- Player rating prediction service
- Player analytics and comparison APIs
- Interactive analytics dashboard
- Automated application tests

Further work includes improving predictive performance, completing deployment configuration, and expanding documentation.

## Author

**GameBehavior Intelligence**

GitHub: [requiem1386](https://github.com/requiem1386)

---

*Built with Python, Django, Data Science, and Machine Learning.*
