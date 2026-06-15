from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from pathlib import Path

from extractors.keyword_extractor import KeywordExtractor
from matcher.scorer import Scorer, ScreeningResult
from parsers.jd_parser import JDParser
from parsers.resume_parser import ResumeParser
from utils.export import default_output_path, save_csv, save_json


@dataclass
class ResumeInput:
    name: str
    text: str
    category: str = ""
    email: str = ""
    phone: str = ""
    candidate_name: str = ""
    filename: str = ""
    file_bytes: bytes | None = None


def _score_resume(args: tuple) -> ScreeningResult:
    resume, jd_requirements, scorer, extractor = args
    skills = extractor.extract_skills(resume.text)
    years = extractor.extract_experience_years(resume.text)
    keywords = extractor.extract_keywords(resume.text)
    contact = extractor.extract_contact_info(resume.text)

    result = scorer.score(skills, years, keywords, jd_requirements)
    result.name = resume.name
    result.category = resume.category
    result.filename = resume.filename or resume.name
    result.email = resume.email or contact["email"]
    result.phone = resume.phone or contact["phone"]
    result.candidate_name = resume.candidate_name or contact["name"]
    result.file_bytes = resume.file_bytes
    return result


class ScreeningEngine:
    def __init__(self):
        self.extractor = KeywordExtractor()
        self.jd_parser = JDParser(self.extractor)
        self.resume_parser = ResumeParser()
        self.scorer = Scorer()

    def parse_jd(self, jd_text: str) -> dict:
        return self.jd_parser.parse(jd_text)

    def parse_jd_file(self, file_path: str | Path) -> dict:
        return self.jd_parser.parse_file(file_path)

    def screen_resumes(
        self,
        resumes: list[ResumeInput],
        jd_text: str | None = None,
        jd_requirements: dict | None = None,
        use_multiprocessing: bool = True,
        top_n: int | None = None,
        min_score: float | None = None,
    ) -> list[ScreeningResult]:
        if jd_requirements is None:
            if not jd_text:
                raise ValueError("Either jd_text or jd_requirements must be provided")
            jd_requirements = self.parse_jd(jd_text)

        if not resumes:
            return []

        worker_args = [(resume, jd_requirements, self.scorer, self.extractor) for resume in resumes]

        if use_multiprocessing and len(resumes) > 1:
            workers = min(cpu_count(), len(resumes))
            with Pool(workers) as pool:
                results = pool.map(_score_resume, worker_args)
        else:
            results = [_score_resume(args) for args in worker_args]

        results = sorted(results, key=lambda r: r.score, reverse=True)

        if min_score is not None and min_score > 0:
            results = [result for result in results if result.score >= min_score]

        if top_n is not None:
            results = results[:top_n]

        return results

    def load_resumes_from_folder(self, folder: str | Path) -> list[ResumeInput]:
        folder = Path(folder)
        resumes = []
        for path in folder.iterdir():
            if path.suffix.lower() not in ResumeParser.SUPPORTED_EXTENSIONS:
                continue
            parsed = self.resume_parser.parse_file(path)
            resumes.append(
                ResumeInput(
                    name=path.stem,
                    text=parsed["text"],
                    email=parsed["email"],
                    phone=parsed["phone"],
                    candidate_name=parsed["name"],
                    filename=parsed["file_name"],
                )
            )
        return resumes

    def save_results(
        self,
        results: list[ScreeningResult],
        folder_name: str = "screening",
        output_format: str = "csv",
    ) -> Path:
        output_path = default_output_path(folder_name, output_format)
        if output_format == "json":
            return save_json(results, output_path)
        return save_csv(results, output_path)
