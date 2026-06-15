import re
from pathlib import Path

import PyPDF2
from docx import Document

from extractors.keyword_extractor import KeywordExtractor


class JDParser:
    REQUIRED_HEADERS = (
        "required skills",
        "requirements",
        "must have",
        "required:",
        "qualifications",
        "minimum qualifications",
        "must possess",
        "essential skills",
    )
    PREFERRED_HEADERS = (
        "preferred skills",
        "nice to have",
        "preferred:",
        "bonus",
        "desired skills",
        "preferred qualifications",
        "good to have",
    )
    SECTION_BREAK_HEADERS = (
        "preferred skills",
        "nice to have",
        "preferred:",
        "experience",
        "keywords",
        "responsibilities",
        "about the role",
        "about us",
        "qualifications",
    )

    def __init__(self, keyword_extractor: KeywordExtractor):
        self.keyword_extractor = keyword_extractor

    def parse_file(self, file_path: str | Path) -> dict:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Job description file not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = self._extract_pdf(path)
        elif suffix in {".docx", ".doc"}:
            text = self._extract_docx(path)
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")

        return self.parse(text)

    def parse(self, text: str) -> dict:
        required = self._extract_section_skills(text, self.REQUIRED_HEADERS)
        preferred = self._extract_section_skills(text, self.PREFERRED_HEADERS)

        if not required:
            required = self._extract_skills_from_bullets(text, self.REQUIRED_HEADERS)

        if not preferred:
            preferred = self._extract_skills_from_bullets(text, self.PREFERRED_HEADERS)

        all_skills = self.keyword_extractor.extract_skills(text)
        if not required and all_skills:
            required = all_skills
        if not preferred:
            preferred = all_skills - required

        min_years = self._extract_min_years(text.lower())
        keywords = self._extract_jd_keywords(text, required, preferred)

        return {
            "text": text,
            "required_skills": required,
            "preferred_skills": preferred,
            "min_years": min_years,
            "min_experience": min_years,
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
            if in_section and line.strip() and self._is_section_break(line_lower):
                break
            if in_section:
                section_lines.append(line)

        section_text = "\n".join(section_lines) if section_lines else ""
        if not section_text:
            return set()

        skills = self.keyword_extractor.extract_skills(section_text)
        skills |= self._skills_from_bullet_lines(section_text)
        return skills

    def _extract_skills_from_bullets(self, text: str, headers: tuple[str, ...]) -> set[str]:
        lines = text.splitlines()
        section_lines: list[str] = []
        in_section = False

        for line in lines:
            line_lower = line.strip().lower()
            if any(header in line_lower for header in headers):
                in_section = True
                continue
            if in_section and line.strip() and self._is_section_break(line_lower):
                break
            if in_section:
                section_lines.append(line)

        return self._skills_from_bullet_lines("\n".join(section_lines))

    def _skills_from_bullet_lines(self, section_text: str) -> set[str]:
        skills = set()
        for line in section_text.splitlines():
            cleaned = re.sub(r"^[\-\*\u2022]\s*", "", line.strip())
            if not cleaned:
                continue
            skills |= self.keyword_extractor.extract_skills(cleaned)
            skills |= self.keyword_extractor.match_skill_phrase(cleaned)
        return skills

    def _is_section_break(self, line_lower: str) -> bool:
        return any(line_lower.startswith(header) or f"{header}:" in line_lower for header in self.SECTION_BREAK_HEADERS)

    def _extract_min_years(self, text_lower: str) -> int:
        patterns = [
            r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:[\w\-]+\s+){0,4}experience",
            r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:in|with)",
            r"minimum\s+(?:of\s+)?(\d+)\s+(?:years?|yrs?)",
            r"at\s+least\s+(\d+)\s+(?:years?|yrs?)",
            r"over\s+(\d+)\s+(?:years?|yrs?)",
            r"more\s+than\s+(\d+)\s+(?:years?|yrs?)",
        ]
        years = []
        for pattern in patterns:
            years.extend(int(match) for match in re.findall(pattern, text_lower))
        return max(years) if years else 0

    def _extract_jd_keywords(self, text: str, required: set[str], preferred: set[str]) -> list[str]:
        keywords = set(required) | set(preferred)
        keywords |= set(self.keyword_extractor.extract_jd_keywords(text))
        return sorted(keywords)

    def _extract_pdf(self, file_path: Path) -> str:
        text = ""
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()

    def _extract_docx(self, file_path: Path) -> str:
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs).strip()
