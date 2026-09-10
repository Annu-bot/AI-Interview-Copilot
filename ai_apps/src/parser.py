import io
import re
from typing import BinaryIO, Union
from pypdf import PdfReader
from docx import Document
from config.logging_config import logger
from ai_apps.core.exceptions import DocumentParsingError


class DocumentParser:
    """
    Handles extraction and normalization of text from PDF, DOCX, and TXT files.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Cleans extracted text by normalizing whitespace, stripping non-printable characters,
        and preserving essential paragraph structure.
        """
        if not text:
            return ""
        text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def parse_pdf(self, file_bytes: Union[bytes, BinaryIO]) -> str:
        """Extract text from a PDF file."""
        try:
            stream = io.BytesIO(file_bytes) if isinstance(file_bytes, bytes) else file_bytes
            reader = PdfReader(stream)
            extracted_pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)
            full_text = "\n".join(extracted_pages)
            cleaned = self.clean_text(full_text)
            logger.info(f"Successfully extracted {len(cleaned)} chars from PDF ({len(reader.pages)} pages)")
            return cleaned
        except Exception as e:
            logger.error(f"Failed to parse PDF: {str(e)}")
            raise DocumentParsingError(f"Could not read PDF file: {str(e)}")

    def parse_docx(self, file_bytes: Union[bytes, BinaryIO]) -> str:
        """Extract text from a Word DOCX file."""
        try:
            stream = io.BytesIO(file_bytes) if isinstance(file_bytes, bytes) else file_bytes
            doc = Document(stream)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            full_text = "\n".join(paragraphs)
            cleaned = self.clean_text(full_text)
            logger.info(f"Successfully extracted {len(cleaned)} chars from DOCX")
            return cleaned
        except Exception as e:
            logger.error(f"Failed to parse DOCX: {str(e)}")
            raise DocumentParsingError(f"Could not read DOCX file: {str(e)}")

    def parse_text(self, file_bytes: bytes) -> str:
        """Decode and clean plain text."""
        try:
            decoded = file_bytes.decode("utf-8", errors="replace")
            return self.clean_text(decoded)
        except Exception as e:
            logger.error(f"Failed to decode text file: {str(e)}")
            raise DocumentParsingError(f"Could not read text file: {str(e)}")

    def extract_text_from_upload(self, filename: str, content: bytes) -> str:
        """
        Dispatches file content to appropriate parser based on file extension.
        """
        filename_lower = filename.lower()
        if filename_lower.endswith(".pdf"):
            return self.parse_pdf(content)
        elif filename_lower.endswith(".docx"):
            return self.parse_docx(content)
        elif filename_lower.endswith(".txt") or filename_lower.endswith(".md"):
            return self.parse_text(content)
        else:
            raise DocumentParsingError(
                f"Unsupported file format '{filename}'. Please upload a PDF, DOCX, or TXT file."
            )


document_parser = DocumentParser()
