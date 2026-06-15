from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from pathlib import Path

from extractors.keyword_extractor import KeywordExtractor
from matcher.scorer import Scorer, ScreeningResult
from parsers.jd_parser import JDParser
from parsers.resume_parser import ResumeParser


@dataclass
class ResumeInput:
    name: str
    text: str
    category: str = ""


def _score_resume(args: tuple) -> ScreeningResult:
    resume, jd_requirements, scorer, extractor = args
    skills = extractor.extract_skills(resume.text)
    years = extractor.extract_experience_years(resume.text)
    result = scorer.score(skills, resume.text.lower(), years, jd_requirements)
    result.name = resume.name
    result.category = resume.category
    return result


class ScreeningEngine:
    def __init__(self):
        self.extractor = KeywordExtractor()
        self.jd_parser = JDParser(self.extractor)
        self.resume_parser = ResumeParser()
        self.scorer = Scorer()

    def parse_jd(self, jd_text: str) -> dict:
        return self.jd_parser.parse(jd_text)

    def screen_resumes(
        self,
        resumes: list[ResumeInput],
        jd_text: str,
        use_multiprocessing: bool = True,
    ) -> list[ScreeningResult]:
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

        return sorted(results, key=lambda r: r.score, reverse=True)

    def load_resumes_from_folder(self, folder: str | Path) -> list[ResumeInput]:
        folder = Path(folder)
        resumes = []
        for path in folder.iterdir():
            if path.suffix.lower() not in ResumeParser.SUPPORTED_EXTENSIONS:
                continue
            text = self.resume_parser.parse(path)
            resumes.append(ResumeInput(name=path.stem, text=text))
        return resumes
