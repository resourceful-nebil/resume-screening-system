from io import BytesIO
from pathlib import Path

import PyPDF2
from docx import Document


class ResumeParser:
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    def parse(self, source: str | Path | bytes, filename: str = "") -> str:
        if isinstance(source, bytes):
            return self._parse_bytes(source, filename)
        path = Path(source)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(path)
        if suffix == ".docx":
            return self._extract_docx(path)
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore").strip()
        raise ValueError(f"Unsupported file type: {suffix}")

    def _parse_bytes(self, data: bytes, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            reader = PyPDF2.PdfReader(BytesIO(data))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        if suffix == ".docx":
            doc = Document(BytesIO(data))
            return "\n".join(para.text for para in doc.paragraphs).strip()
        if suffix == ".txt":
            return data.decode("utf-8", errors="ignore").strip()
        raise ValueError(f"Unsupported file type: {suffix}")

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
