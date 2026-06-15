import csv
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from matcher.scorer import ScreeningResult


def results_to_dataframe(results: list[ScreeningResult]) -> pd.DataFrame:
    rows = []
    for rank, result in enumerate(results, start=1):
        display_name = result.candidate_name or result.name
        rows.append(
            {
                "Rank": rank,
                "Resume File": result.filename or result.name,
                "Candidate Name": display_name,
                "Email": result.email or "",
                "Phone": result.phone or "",
                "Total Score (%)": result.score,
                "Required Skills (%)": result.required_score,
                "Preferred Skills (%)": result.preferred_score,
                "Experience (%)": result.experience_score,
                "Keyword Match (%)": result.keyword_score,
                "Experience (Years)": result.experience_years,
                "Matched Skills": ", ".join(sorted(result.required_matched | result.preferred_matched)),
                "Missing Skills": ", ".join(sorted(result.missing_required)),
                "Category": result.category or "",
            }
        )
    return pd.DataFrame(rows)


def save_csv(results: list[ScreeningResult], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = results_to_dataframe(results)
    df.to_csv(output_path, index=False)
    return output_path


def save_json(results: list[ScreeningResult], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = []
    for rank, result in enumerate(results, start=1):
        payload.append(
            {
                "rank": rank,
                "filename": result.filename or result.name,
                "name": result.candidate_name or result.name,
                "email": result.email,
                "phone": result.phone,
                "total_score": result.score,
                "scores": {
                    "required_skills": result.required_score,
                    "preferred_skills": result.preferred_score,
                    "experience": result.experience_score,
                    "keyword_match": result.keyword_score,
                },
                "experience_years": result.experience_years,
                "matched_required_skills": sorted(result.required_matched),
                "matched_preferred_skills": sorted(result.preferred_matched),
                "missing_required_skills": sorted(result.missing_required),
                "category": result.category,
            }
        )

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    return output_path


def default_output_path(folder_name: str, output_format: str = "csv") -> Path:
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = "json" if output_format == "json" else "csv"
    return output_dir / f"results_{folder_name}_{timestamp}.{extension}"
