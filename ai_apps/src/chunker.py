"""
Document Chunking and Section Parsing Module for RAG Grounding.
Splits Resumes and Job Descriptions into semantically coherent chunks with section metadata.
"""

import re
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """
    Represents a discrete semantic chunk of a resume or job description with metadata.
    """
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str  # "resume" or "job_description"
    section: str  # e.g., "Work Experience", "Projects", "Skills", "Requirements"
    content: str
    char_count: int = 0
    metadata: dict = Field(default_factory=dict)

    def model_post_init(self, __context):
        self.char_count = len(self.content)


def _split_into_paragraphs(text: str) -> List[str]:
    """Splits text by double newlines or major delimiters."""
    raw_paras = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in raw_paras if p.strip()]


def _split_into_sentences_or_bullets(text: str, max_chars: int = 400) -> List[str]:
    """
    Splits a block of text by bullet points or sentence boundaries if too long.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    chunks = []
    current_chunk = []
    current_len = 0

    for line in lines:
        line_len = len(line)
        if current_len + line_len > max_chars and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [line]
            current_len = line_len
        else:
            current_chunk.append(line)
            current_len += line_len + 1

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks if chunks else [text]


def chunk_resume(text: str, max_chunk_chars: int = 450) -> List[DocumentChunk]:
    """
    Splits a candidate resume into structured section-aware chunks.
    Detects standard resume sections (Experience, Skills, Projects, Education, etc.).
    """
    if not text or not text.strip():
        return []

    section_keywords = [
        ("EXPERIENCE", "Work Experience"),
        ("WORK HISTORY", "Work Experience"),
        ("EMPLOYMENT", "Work Experience"),
        ("PROJECTS", "Technical Projects"),
        ("TECHNICAL PROJECTS", "Technical Projects"),
        ("SKILLS", "Technical Skills"),
        ("TECHNICAL SKILLS", "Technical Skills"),
        ("CORE COMPETENCIES", "Technical Skills"),
        ("EDUCATION", "Education & Certifications"),
        ("CERTIFICATIONS", "Education & Certifications"),
        ("SUMMARY", "Professional Summary"),
        ("PROFILE", "Professional Summary"),
    ]

    # Pattern to match section headers
    header_pattern = re.compile(
        r"^(?:" + "|".join([k[0] for k in section_keywords]) + r")(?::|\b)",
        re.IGNORECASE | re.MULTILINE
    )

    paragraphs = _split_into_paragraphs(text)
    chunks: List[DocumentChunk] = []
    current_section = "General / Overview"

    for para in paragraphs:
        # Check if this paragraph is a section header
        first_line = para.split("\n")[0].strip().upper()
        matched_section = None
        for keyword, section_name in section_keywords:
            if keyword in first_line:
                matched_section = section_name
                break

        if matched_section:
            current_section = matched_section
            # Strip the header line if paragraph contains more body text
            lines = para.split("\n")
            if len(lines) > 1:
                para = "\n".join(lines[1:]).strip()
            else:
                continue  # Just the header line, move to next

        if not para:
            continue

        # Sub-divide if paragraph is too long
        sub_blocks = _split_into_sentences_or_bullets(para, max_chars=max_chunk_chars)
        for i, block in enumerate(sub_blocks):
            if block.strip():
                enriched_content = f"[{current_section}] {block.strip()}"
                chunks.append(DocumentChunk(
                    source="resume",
                    section=current_section,
                    content=enriched_content,
                    metadata={"raw_text": block.strip(), "chunk_index": len(chunks)}
                ))

    # Fallback if no structured sections were found
    if not chunks and text.strip():
        sub_blocks = _split_into_sentences_or_bullets(text.strip(), max_chars=max_chunk_chars)
        for block in sub_blocks:
            chunks.append(DocumentChunk(
                source="resume",
                section="Candidate Profile",
                content=f"[Candidate Background] {block}",
                metadata={"raw_text": block, "chunk_index": len(chunks)}
            ))

    return chunks


def chunk_job_description(text: str, max_chunk_chars: int = 450) -> List[DocumentChunk]:
    """
    Splits a job description into structured requirement and responsibility chunks.
    """
    if not text or not text.strip():
        return []

    jd_keywords = [
        ("RESPONSIBILITIES", "Role Responsibilities"),
        ("WHAT YOU WILL DO", "Role Responsibilities"),
        ("KEY DUTIES", "Role Responsibilities"),
        ("REQUIREMENTS", "Required Qualifications"),
        ("QUALIFICATIONS", "Required Qualifications"),
        ("MUST HAVE", "Required Qualifications"),
        ("NICE TO HAVE", "Preferred Qualifications"),
        ("BONUS", "Preferred Qualifications"),
        ("PREFERRED", "Preferred Qualifications"),
        ("TECH STACK", "Technology Stack"),
        ("ABOUT THE ROLE", "Role Overview"),
    ]

    paragraphs = _split_into_paragraphs(text)
    chunks: List[DocumentChunk] = []
    current_section = "Job Overview"

    for para in paragraphs:
        first_line = para.split("\n")[0].strip().upper()
        matched_section = None
        for keyword, section_name in jd_keywords:
            if keyword in first_line:
                matched_section = section_name
                break

        if matched_section:
            current_section = matched_section
            lines = para.split("\n")
            if len(lines) > 1:
                para = "\n".join(lines[1:]).strip()
            else:
                continue

        if not para:
            continue

        sub_blocks = _split_into_sentences_or_bullets(para, max_chars=max_chunk_chars)
        for block in sub_blocks:
            if block.strip():
                enriched_content = f"[{current_section}] {block.strip()}"
                chunks.append(DocumentChunk(
                    source="job_description",
                    section=current_section,
                    content=enriched_content,
                    metadata={"raw_text": block.strip(), "chunk_index": len(chunks)}
                ))

    # Fallback
    if not chunks and text.strip():
        sub_blocks = _split_into_sentences_or_bullets(text.strip(), max_chars=max_chunk_chars)
        for block in sub_blocks:
            chunks.append(DocumentChunk(
                source="job_description",
                section="Role Requirements",
                content=f"[Job Requirement] {block}",
                metadata={"raw_text": block, "chunk_index": len(chunks)}
            ))

    return chunks
