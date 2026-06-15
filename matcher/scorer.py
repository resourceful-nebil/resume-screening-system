import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScreeningResult:
    name: str
    score: float
    required_matched: set[str] = field(default_factory=set)
    preferred_matched: set[str] = field(default_factory=set)
    keywords_matched: set[str] = field(default_factory=set)
    experience_years: int = 0
    category: str = ""

    @property
    def matched_skills(self) -> set[str]:
        return self.required_matched | self.preferred_matched


class Scorer:
    def __init__(self, config_path: str | Path | None = None):
        path = config_path or Path(__file__).parent.parent / "data" / "config.json"
        with open(path, encoding="utf-8") as file:
            config = json.load(file)
        self.weights = config["weights"]
        self.experience_config = config["experience"]

    def score(
        self,
        resume_skills: set[str],
        resume_text: str,
        experience_years: int,
        jd_requirements: dict,
    ) -> ScreeningResult:
        required = jd_requirements["required_skills"]
        preferred = jd_requirements["preferred_skills"]
        keywords = jd_requirements["keywords"]
        min_years = jd_requirements.get("min_years") or self.experience_config["default_min_years"]

        required_matched = resume_skills & required
        preferred_matched = resume_skills & preferred
        keywords_matched = {kw for kw in keywords if kw in resume_text.lower()}

        required_score = self._ratio(len(required_matched), len(required))
        preferred_score = self._ratio(len(preferred_matched), len(preferred))
        keyword_score = self._ratio(len(keywords_matched), len(keywords))
        experience_score = self._experience_score(experience_years, min_years)

        total = (
            required_score * self.weights["required_skills"]
            + preferred_score * self.weights["preferred_skills"]
            + experience_score * self.weights["experience"]
            + keyword_score * self.weights["keywords"]
        ) * 100

        return ScreeningResult(
            name="",
            score=round(total, 2),
            required_matched=required_matched,
            preferred_matched=preferred_matched,
            keywords_matched=keywords_matched,
            experience_years=experience_years,
        )

    def _ratio(self, matched: int, total: int) -> float:
        return matched / total if total else 1.0

    def _experience_score(self, years: int, min_years: int) -> float:
        if min_years <= 0:
            return 1.0 if years > 0 else 0.5
        if years >= min_years:
            return 1.0
        return years / min_years
