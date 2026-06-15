import argparse
from pathlib import Path

from data.dataset_loader import get_resumes_by_category, sample_resumes
from screening_engine import ResumeInput, ScreeningEngine

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
    parser.add_argument("--jd", type=str, help="Path to job description text file")
    parser.add_argument("--resumes", type=str, help="Folder containing resume files (pdf/docx/txt)")
    parser.add_argument("--category", type=str, help="Kaggle dataset category to screen")
    parser.add_argument("--limit", type=int, default=10, help="Max resumes from dataset category")
    parser.add_argument("--sample", action="store_true", help="Screen a sample from all dataset categories")
    parser.add_argument("--no-mp", action="store_true", help="Disable multiprocessing")
    args = parser.parse_args()

    engine = ScreeningEngine()

    if args.jd:
        jd_text = Path(args.jd).read_text(encoding="utf-8")
    else:
        jd_text = SAMPLE_JD
        print("Using built-in sample job description.\n")

    resumes: list[ResumeInput] = []
    if args.resumes:
        resumes = engine.load_resumes_from_folder(args.resumes)
    elif args.category:
        dataset_resumes = get_resumes_by_category(args.category, args.limit)
        resumes = [
            ResumeInput(name=r["name"], text=r["text"], category=r["category"])
            for r in dataset_resumes
        ]
    elif args.sample:
        dataset_resumes = sample_resumes(per_category=3)
        resumes = [
            ResumeInput(name=r["name"], text=r["text"], category=r["category"])
            for r in dataset_resumes
        ]
    else:
        dataset_resumes = get_resumes_by_category("INFORMATION-TECHNOLOGY", args.limit)
        resumes = [
            ResumeInput(name=r["name"], text=r["text"], category=r["category"])
            for r in dataset_resumes
        ]
        print(f"No input specified — screening {len(resumes)} IT resumes from Kaggle dataset.\n")

    results = engine.screen_resumes(resumes, jd_text, use_multiprocessing=not args.no_mp)

    print("=" * 60)
    print("SCREENING RESULTS")
    print("=" * 60)
    for rank, result in enumerate(results, start=1):
        matched = ", ".join(sorted(result.matched_skills)) or "none"
        category = f" [{result.category}]" if result.category else ""
        print(
            f"Rank #{rank}: {result.name}{category} | "
            f"Score: {result.score}/100 | Matched: {matched}"
        )


if __name__ == "__main__":
    main()
