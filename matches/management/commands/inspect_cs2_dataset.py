import glob
import os

import pandas as pd

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = "Inspect all CS2 Parquet files"

    def handle(self, *args, **options):

        dataset_path = os.path.join(
            "dataset", "raw", "data", "*.parquet"
        )

        files = glob.glob(dataset_path)

        all_columns = set()
        nested_fields = {}
        total_rows = 0

        for file_path in files:

            df = pd.read_parquet(file_path)
            total_rows += len(df)

            all_columns.update(df.columns)

            for column in ["players", "rounds", "kills",
                           "match", "teams", "meta"]:

                if column not in df.columns:
                    continue

                for value in df[column]:

                    if isinstance(value, dict):
                        nested_fields.setdefault(column, set())
                        nested_fields[column].update(value.keys())
                        break

                    if isinstance(value, list) and value:
                        if isinstance(value[0], dict):
                            nested_fields.setdefault(column, set())
                            nested_fields[column].update(value[0].keys())
                            break

        self.stdout.write("\n--- DATASET SUMMARY ---")
        self.stdout.write(f"Files: {len(files)}")
        self.stdout.write(f"Total rows: {total_rows}")

        self.stdout.write("\n--- COLUMNS ---")

        for column in sorted(all_columns):
            self.stdout.write(column)

        self.stdout.write("\n--- NESTED FIELDS ---")

        for column, fields in nested_fields.items():

            self.stdout.write(f"\n{column}:")

            for field in sorted(fields):
                self.stdout.write(f"  - {field}")

        self.stdout.write(
            self.style.SUCCESS("\nInspection completed.")
        )