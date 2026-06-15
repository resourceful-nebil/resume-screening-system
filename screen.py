"""
Simple Resume Screening - Single Folder Input
Drop JD + resumes in one folder, get top matches automatically.
"""

import argparse
import sys
from pathlib import Path

from screening_engine import ResumeInput, ScreeningEngine
from utils.export import save_csv, save_json, default_output_path


def find_jd_file(folder_path: str | Path) -> Path | None:
    folder = Path(folder_path)
    jd_keywords = ["job", "jd", "description", "opening", "position", "role", "vacancy"]

    for file in folder.iterdir():
        if file.is_file():
            filename_lower = file.stem.lower()
            if any(keyword in filename_lower for keyword in jd_keywords):
                if file.suffix.lower() in {".pdf", ".docx", ".doc", ".txt"}:
                    return file

    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() in {".pdf", ".docx", ".doc", ".txt"}:
            filename_lower = file.stem.lower()
            if not any(word in filename_lower for word in ["resume", "cv", "candidate"]):
                return file

    return None


def screen_folder(
    input_folder: str | Path,
    top_n: int = 10,
    min_score: float | None = None,
    output_format: str = "csv",
) -> Path | None:
    input_path = Path(input_folder)
    if not input_path.exists() or not input_path.is_dir():
        print(f"Error: Folder not found: {input_folder}")
        return None

    engine = ScreeningEngine()

    print(f"\n{'=' * 60}")
    print("RESUME SCREENING SYSTEM - SIMPLE MODE")
    print(f"{'=' * 60}\n")
    print(f"Scanning folder: {input_path}")

    jd_file = find_jd_file(input_path)
    if not jd_file:
        print("Error: Could not find job description file.")
        print("Tip: Name your JD file with keywords like 'job', 'jd', or 'description'.")
        return None

    print(f"Found JD: {jd_file.name}\n")

    try:
        jd_requirements = engine.parse_jd_file(jd_file)
    except Exception as exc:
        print(f"Error parsing JD: {exc}")
        return None

    print(f"Required Skills: {len(jd_requirements['required_skills'])}")
    print(f"Preferred Skills: {len(jd_requirements['preferred_skills'])}")
    print(f"Min Experience: {jd_requirements['min_years']} years\n")

    resumes = []
    for file in input_path.iterdir():
        if file.is_file() and file != jd_file:
            if file.suffix.lower() in engine.resume_parser.SUPPORTED_EXTENSIONS:
                try:
                    parsed = engine.resume_parser.parse_file(file)
                    resumes.append(
                        ResumeInput(
                            name=file.stem,
                            text=parsed["text"],
                            email=parsed["email"],
                            phone=parsed["phone"],
                            candidate_name=parsed["name"],
                            filename=parsed["file_name"],
                        )
                    )
                except Exception as exc:
                    print(f"Warning: Could not parse {file.name}: {exc}")

    if not resumes:
        print("Error: No resume files found.")
        return None

    print(f"Loaded {len(resumes)} resumes")
    print("Scoring resumes...\n")

    results = engine.screen_resumes(
        resumes,
        jd_requirements=jd_requirements,
        use_multiprocessing=len(resumes) > 1,
        top_n=top_n,
        min_score=min_score,
    )

    output_path = default_output_path(input_path.name, output_format)
    if output_format == "json":
        save_json(results, output_path)
    else:
        save_csv(results, output_path)

    print(f"Results saved to: {output_path}\n")
    print(f"{'=' * 60}")
    print("TOP MATCHING RESUMES")
    print(f"{'=' * 60}\n")

    for rank, result in enumerate(results[:5], start=1):
        print(f"#{rank} - {result.filename or result.name}")
        print(f"   Score: {result.score:.1f}%")
        print(f"   Experience: {result.experience_years} years")
        matched = ", ".join(sorted(result.required_matched)[:5]) or "none"
        print(f"   Matched Skills: {matched}")
        if result.missing_required:
            missing = ", ".join(sorted(result.missing_required)[:3])
            print(f"   Missing: {missing}")
        print()

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Screen resumes from a single folder")
    parser.add_argument("--folder", required=True, help="Folder containing JD and resume files")
    parser.add_argument("--top", type=int, default=10, help="Number of top matches (default: 10)")
    parser.add_argument("--min-score", type=float, default=None, help="Minimum score threshold 0-100")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format")
    args = parser.parse_args()

    try:
        screen_folder(
            input_folder=args.folder,
            top_n=args.top,
            min_score=args.min_score,
            output_format=args.format,
        )
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
