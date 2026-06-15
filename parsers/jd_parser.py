import re

from extractors.keyword_extractor import KeywordExtractor


class JDParser:
    REQUIRED_HEADERS = (
        "required skills",
        "requirements",
        "must have",
        "required:",
        "qualifications",
        "minimum qualifications",
    )
    PREFERRED_HEADERS = (
        "preferred skills",
        "nice to have",
        "preferred:",
        "bonus",
        "desired skills",
        "preferred qualifications",
    )

    def __init__(self, keyword_extractor: KeywordExtractor):
        self.keyword_extractor = keyword_extractor

    def parse(self, text: str) -> dict:
        text_lower = text.lower()
        required = self._extract_section_skills(text, self.REQUIRED_HEADERS)
        preferred = self._extract_section_skills(text, self.PREFERRED_HEADERS)

        all_skills = self.keyword_extractor.extract_skills(text)
        if not required:
            required = all_skills
        if not preferred:
            preferred = all_skills - required

        min_years = self._extract_min_years(text_lower)
        keywords = self.keyword_extractor.extract_keywords(text)

        return {
            "required_skills": required,
            "preferred_skills": preferred,
            "min_years": min_years,
            "keywords": keywords,
        }

    def _extract_section_skills(self, text: str, headers: tuple[str, ...]) -> set[str]:
        lines = text.splitlines()
        section_lines: list[str] = []
        in_section = False

        for line in lines:
            line_lower = line.strip().lower()
            if any(header in line_lower for header in headers):
                in_section = True
                continue
            if in_section and line.strip() and self._is_new_section(line_lower):
                break
            if in_section:
                section_lines.append(line)

        section_text = "\n".join(section_lines) if section_lines else text
        return self.keyword_extractor.extract_skills(section_text)

    def _is_new_section(self, line_lower: str) -> bool:
        section_markers = (
            "experience",
            "responsibilities",
            "about",
            "preferred",
            "required",
            "qualifications",
        )
        return any(marker in line_lower for marker in section_markers) and ":" in line_lower

    def _extract_min_years(self, text_lower: str) -> int:
        patterns = [
            r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience",
            r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:in|with)",
            r"minimum\s+(?:of\s+)?(\d+)\s+(?:years?|yrs?)",
        ]
        years = []
        for pattern in patterns:
            years.extend(int(match) for match in re.findall(pattern, text_lower))
        return max(years) if years else 0
