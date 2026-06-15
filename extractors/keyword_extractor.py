import json
import re
from datetime import datetime
from pathlib import Path


class KeywordExtractor:
    EXPERIENCE_PATTERNS = [
        r"(\d+)\+?\s*(?:years?|yrs?).*?(?:experience|exp)",
        r"(?:experience|exp).*?(\d+)\+?\s*(?:years?|yrs?)",
        r"over\s+(\d+)\s+(?:years?|yrs?)",
        r"more\s+than\s+(\d+)\s+(?:years?|yrs?)",
        r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?(?:experience|development)",
        r"(\d+)\+?\s*(?:years?|yrs?)\s+in\s+",
    ]
    DATE_RANGE_PATTERNS = [
        r"(\d{4})\s*[-–]\s*(\d{4}|present|current)",
        r"(\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{4}|present|current)",
    ]

    def __init__(self, taxonomy_path: str | Path | None = None):
        path = taxonomy_path or Path(__file__).parent.parent / "data" / "skills_taxonomy.json"
        with open(path, encoding="utf-8") as file:
            self.skills_taxonomy = json.load(file)

    def extract_contact_info(self, text: str) -> dict[str, str]:
        return {
            "email": self._extract_email(text),
            "phone": self._extract_phone(text),
            "name": self._extract_name(text),
        }

    def _extract_email(self, text: str) -> str:
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for email in re.findall(pattern, text):
            email_lower = email.lower()
            if "example" not in email_lower and "sample" not in email_lower:
                return email
        return ""

    def _extract_phone(self, text: str) -> str:
        patterns = [
            r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
            r"\b\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b",
            r"\b\d{10}\b",
            r"\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match and len(re.sub(r"\D", "", match.group(0))) >= 10:
                return match.group(0)
        return ""

    def _extract_name(self, text: str) -> str:
        name_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b"
        for line in text.split("\n")[:5]:
            if "@" in line or re.search(r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}", line):
                continue
            match = re.search(name_pattern, line)
            if match:
                name = match.group(1).strip()
                if name.lower() not in {"resume", "curriculum vitae", "summary"}:
                    return name
        return ""

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
            for match in re.finditer(pattern, text_lower):
                try:
                    year = int(match.group(1))
                    if 0 < year < 50:
                        years.append(year)
                except (ValueError, IndexError):
                    continue

        date_years = self._calculate_experience_from_dates(text)
        if date_years:
            years.append(date_years)

        return max(years) if years else 0

    def _calculate_experience_from_dates(self, text: str) -> int:
        current_year = datetime.now().year
        total_years = 0

        for pattern in self.DATE_RANGE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = match.group(1)
                end = match.group(2)
                try:
                    start_year = int(re.search(r"\d{4}", start).group())
                    if end.lower() in {"present", "current"}:
                        end_year = current_year
                    else:
                        end_year = int(re.search(r"\d{4}", end).group())
                    years = max(0, end_year - start_year)
                    if 0 < years < 30:
                        total_years += years
                except (ValueError, AttributeError):
                    continue

        return total_years

    def extract_keywords(self, text: str) -> list[str]:
        text_lower = text.lower()
        keywords = []

        for skills_dict in self.skills_taxonomy.values():
            for variations in skills_dict.values():
                for variation in variations:
                    pattern = r"\b" + re.escape(variation.strip()) + r"\b"
                    keywords.extend(re.findall(pattern, text_lower))

        return keywords

    def extract_jd_keywords(self, text: str) -> list[str]:
        keywords = list(self.extract_skills(text))
        text_lower = text.lower()

        if "domain_keywords" in self.skills_taxonomy:
            for keyword, variations in self.skills_taxonomy["domain_keywords"].items():
                if any(variation in text_lower for variation in variations):
                    keywords.append(keyword)

        return keywords
