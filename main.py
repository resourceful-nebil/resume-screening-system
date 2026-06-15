import argparse
from pathlib import Path

from data.dataset_loader import get_resumes_by_category, sample_resumes
from screening_engine import ResumeInput, ScreeningEngine
from utils.export import results_to_dataframe, save_csv, save_json, default_output_path

SAMPLE_JD = """
We are looking for a Senior Python Developer with strong experience in backend development.

Required Skills:
- Python
- Django
- REST APIs
- SQL

Preferred Skills:
- PostgreSQL
- Docker
- AWS

Experience:
- 3+ years of professional Python development
- Experience building web applications
"""


def main():
    parser = argparse.ArgumentParser(description="Screen resumes against a job description")
    parser.add_argument("--jd", type=str, help="Path to job description file (txt/pdf/docx)")
    parser.add_argument("--resumes", type=str, help="Folder containing resume files (pdf/docx/txt)")
    parser.add_argument("--category", type=str, help="Kaggle dataset category to screen")
    parser.add_argument("--limit", type=int, default=10, help="Max resumes from dataset category")
    parser.add_argument("--sample", action="store_true", help="Screen a sample from all dataset categories")
    parser.add_argument("--top", type=int, default=None, help="Return only top N results")
    parser.add_argument("--min-score", type=float, default=None, help="Minimum score threshold")
    parser.add_argument("--format", choices=["csv", "json"], default=None, help="Save results to output/")
    parser.add_argument("--no-mp", action="store_true", help="Disable multiprocessing")
    args = parser.parse_args()

    engine = ScreeningEngine()

    if args.jd:
        jd_path = Path(args.jd)
        if jd_path.suffix.lower() in {".pdf", ".docx", ".doc"}:
            jd_requirements = engine.parse_jd_file(jd_path)
            jd_text = jd_requirements["text"]
        else:
            jd_text = jd_path.read_text(encoding="utf-8")
            jd_requirements = None
    else:
        jd_text = SAMPLE_JD
        jd_requirements = None
        print("Using built-in sample job description.\n")

    resumes: list[ResumeInput] = []
    folder_name = "screening"

    if args.resumes:
        folder_name = Path(args.resumes).name
        resumes = engine.load_resumes_from_folder(args.resumes)
    elif args.category:
        folder_name = args.category
        dataset_resumes = get_resumes_by_category(args.category, args.limit)
        resumes = [
            ResumeInput(name=r["name"], text=r["text"], category=r["category"], filename=r["name"])
            for r in dataset_resumes
        ]
    elif args.sample:
        folder_name = "sample"
        dataset_resumes = sample_resumes(per_category=3)
        resumes = [
            ResumeInput(name=r["name"], text=r["text"], category=r["category"], filename=r["name"])
            for r in dataset_resumes
        ]
    else:
        folder_name = "INFORMATION-TECHNOLOGY"
        dataset_resumes = get_resumes_by_category("INFORMATION-TECHNOLOGY", args.limit)
        resumes = [
            ResumeInput(name=r["name"], text=r["text"], category=r["category"], filename=r["name"])
            for r in dataset_resumes
        ]
        print(f"No input specified — screening {len(resumes)} IT resumes from Kaggle dataset.\n")

    results = engine.screen_resumes(
        resumes,
        jd_text=jd_text if jd_requirements is None else None,
        jd_requirements=jd_requirements,
        use_multiprocessing=not args.no_mp,
        top_n=args.top,
        min_score=args.min_score,
    )

    print("=" * 60)
    print("SCREENING RESULTS")
    print("=" * 60)
    for rank, result in enumerate(results, start=1):
        matched = ", ".join(sorted(result.matched_skills)) or "none"
        missing = ", ".join(sorted(result.missing_required)[:3]) or "none"
        category = f" [{result.category}]" if result.category else ""
        name = result.candidate_name or result.name
        print(
            f"Rank #{rank}: {name}{category} | Score: {result.score}/100 | "
            f"Matched: {matched} | Missing: {missing}"
        )

    if args.format:
        output_path = default_output_path(folder_name, args.format)
        if args.format == "json":
            save_json(results, output_path)
        else:
            save_csv(results, output_path)
        print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
