from pathlib import Path

import pandas as pd

DATASET_PATH = Path(__file__).parent / "archive" / "Resume" / "Resume.csv"


def load_dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH)


def get_categories() -> list[str]:
    return sorted(load_dataset()["Category"].unique().tolist())


def get_resumes_by_category(category: str, limit: int | None = None) -> list[dict]:
    df = load_dataset()
    subset = df[df["Category"] == category]
    if limit:
        subset = subset.head(limit)
    return [
        {
            "id": row["ID"],
            "name": f"{category.replace('-', ' ').title()} #{row['ID']}",
            "text": row["Resume_str"],
            "category": row["Category"],
        }
        for _, row in subset.iterrows()
    ]


def sample_resumes(categories: list[str] | None = None, per_category: int = 5) -> list[dict]:
    df = load_dataset()
    if categories:
        df = df[df["Category"].isin(categories)]
    resumes = []
    for category in df["Category"].unique():
        subset = df[df["Category"] == category].head(per_category)
        for _, row in subset.iterrows():
            resumes.append(
                {
                    "id": row["ID"],
                    "name": f"{category.replace('-', ' ').title()} #{row['ID']}",
                    "text": row["Resume_str"],
                    "category": row["Category"],
                }
            )
    return resumes
