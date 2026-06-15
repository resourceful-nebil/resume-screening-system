import json
import re
from pathlib import Path


class KeywordExtractor:
    EXPERIENCE_PATTERNS = [
        r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"experience\s+(?:of\s+)?(\d+)\+?\s*(?:years?|yrs?)",
        r"(\d+)\+?\s*(?:years?|yrs?)\s+in\s+",
    ]
    DOMAIN_KEYWORDS = (
        "backend",
        "frontend",
        "full stack",
        "full-stack",
        "web application",
        "microservices",
        "distributed systems",
        "software development",
        "database",
        "automation",
        "testing",
        "deployment",
        "scalability",
        "security",
        "architecture",
    )

    def __init__(self, taxonomy_path: str | Path | None = None):
        path = taxonomy_path or Path(__file__).parent.parent / "data" / "skills_taxonomy.json"
        with open(path, encoding="utf-8") as file:
            self.skills_taxonomy = json.load(file)

    def extract_skills(self, text: str) -> set[str]:
        text_lower = text.lower()
        found_skills = set()

        for skills_dict in self.skills_taxonomy.values():
            for skill_name, variations in skills_dict.items():
                for variation in variations:
                    pattern = r"\b" + re.escape(variation.strip()) + r"\b"
                    if re.search(pattern, text_lower):
                        found_skills.add(skill_name)
                        break

        return found_skills

    def extract_experience_years(self, text: str) -> int:
        text_lower = text.lower()
        years = []
        for pattern in self.EXPERIENCE_PATTERNS:
            years.extend(int(match) for match in re.findall(pattern, text_lower))
        return max(years) if years else 0

    def extract_keywords(self, text: str) -> set[str]:
        text_lower = text.lower()
        return {keyword for keyword in self.DOMAIN_KEYWORDS if keyword in text_lower}
