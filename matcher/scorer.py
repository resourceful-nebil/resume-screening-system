import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScreeningResult:
    name: str
    score: float
    required_matched: set[str] = field(default_factory=set)
    preferred_matched: set[str] = field(default_factory=set)
    missing_required: set[str] = field(default_factory=set)
    keywords_matched: set[str] = field(default_factory=set)
    required_score: float = 0.0
    preferred_score: float = 0.0
    experience_score: float = 0.0
    keyword_score: float = 0.0
    experience_years: int = 0
    required_experience: int = 0
    email: str = ""
    phone: str = ""
    candidate_name: str = ""
    filename: str = ""
    category: str = ""
    file_bytes: bytes | None = None

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
        self.min_score = config.get("min_score", 0.0)

    def score(
        self,
        resume_skills: set[str],
        resume_experience: int,
        resume_keywords: list[str],
        jd_requirements: dict,
    ) -> ScreeningResult:
        required = {skill.lower() for skill in jd_requirements["required_skills"]}
        preferred = {skill.lower() for skill in jd_requirements["preferred_skills"]}
        jd_keywords = [kw.lower() for kw in jd_requirements.get("keywords", [])]
        min_years = jd_requirements.get("min_years") or jd_requirements.get("min_experience") or 0
        if not min_years:
            min_years = self.experience_config.get("default_min_years", 0)

        resume_skills_lower = {skill.lower() for skill in resume_skills}
        required_matched = resume_skills_lower & required
        preferred_matched = resume_skills_lower & preferred
        missing_required = required - resume_skills_lower

        required_component = self._skill_ratio(len(required_matched), len(required))
        preferred_component = self._skill_ratio(len(preferred_matched), len(preferred))
        experience_component = self._experience_score(resume_experience, min_years)
        keyword_component = self._keyword_score(resume_keywords, jd_keywords)

        total = (
            required_component * self.weights["required_skills"]
            + preferred_component * self.weights["preferred_skills"]
            + experience_component * self.weights["experience"]
            + keyword_component * self.weights["keywords"]
        ) * 100

        resume_keyword_set = {kw.lower() for kw in resume_keywords}
        jd_keyword_set = set(jd_keywords)
        keywords_matched = resume_keyword_set & jd_keyword_set

        return ScreeningResult(
            name="",
            score=round(total, 2),
            required_matched=required_matched,
            preferred_matched=preferred_matched,
            missing_required=missing_required,
            keywords_matched=keywords_matched,
            required_score=round(required_component * 100, 2),
            preferred_score=round(preferred_component * 100, 2),
            experience_score=round(experience_component * 100, 2),
            keyword_score=round(keyword_component * 100, 2),
            experience_years=resume_experience,
            required_experience=min_years,
        )

    def _skill_ratio(self, matched: int, total: int) -> float:
        return matched / total if total else 1.0

    def _experience_score(self, resume_exp: int, required_exp: int) -> float:
        if required_exp <= 0:
            return 1.0 if resume_exp > 0 else 0.5
        if resume_exp >= required_exp:
            return 1.0

        tolerance = self.experience_config.get("tolerance", 2)
        if resume_exp >= (required_exp - tolerance):
            gap = required_exp - resume_exp
            score = 1.0 - (gap / (tolerance + 1) * 0.3)
            return max(0.7, score)

        ratio = resume_exp / required_exp if required_exp > 0 else 0
        return max(0.0, ratio * 0.7)

    def _keyword_score(self, resume_keywords: list[str], jd_keywords: list[str]) -> float:
        if not jd_keywords:
            return 1.0

        resume_keyword_set = {kw.lower() for kw in resume_keywords}
        jd_keyword_set = {kw.lower() for kw in jd_keywords}
        matched = resume_keyword_set & jd_keyword_set

        if not jd_keyword_set:
            return 1.0

        match_ratio = len(matched) / len(jd_keyword_set)
        frequency_bonus = 0.0
        if resume_keywords:
            keyword_count = sum(1 for kw in resume_keywords if kw.lower() in jd_keyword_set)
            frequency_bonus = min(0.2, keyword_count / len(resume_keywords))

        return min(1.0, match_ratio + frequency_bonus)
