"""PDF Rendering engine supporting original-template preservation and standardized ATS fallback."""

import hashlib
import io
import logging
from typing import Any

import pdfplumber
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.modules.candidate.models import CandidateProfile
from app.modules.tailoring.enums import RenderingStrategyEnum
from app.modules.tailoring.exceptions import RenderingError
from app.modules.tailoring.schemas import TailoredResumeContent

logger = logging.getLogger(__name__)


class ResumeRenderer:
    """Renders tailored resume content into valid PDF documents using either
    Strategy A (Original Template Preservation) or Strategy B (Standardized ATS Fallback).
    """

    def render(
        self,
        content: TailoredResumeContent,
        candidate_profile: CandidateProfile,
        strategy: RenderingStrategyEnum = RenderingStrategyEnum.FALLBACK,
        template_metadata: dict[str, Any] | None = None,
    ) -> tuple[bytes, RenderingStrategyEnum, str | None]:
        """Render tailored resume content into PDF binary bytes with transparent fallback tracking.

        Args:
            content: Validated tailored resume content.
            candidate_profile: Source candidate profile for contact/identity info.
            strategy: Desired rendering strategy.
            template_metadata: Layout and font metadata from parsed master resume.

        Returns:
            Tuple of (raw PDF bytes, actual RenderingStrategyEnum used, fallback_reason: str | None).
        """
        meta = template_metadata or {}
        capability = meta.get("preservation_capability", "UNSUPPORTED")

        # Strategy A: Original Template Preservation
        if strategy == RenderingStrategyEnum.PRESERVED:
            # Check eligibility for preservation
            if capability != "SUPPORTED":
                fallback_reason = (
                    f"Master resume preservation capability is '{capability}' "
                    f"(requires structural font cues and layout extractability); "
                    f"transparently selected standardized ATS fallback."
                )
                logger.info(f"Preservation rejected: {fallback_reason}")
                pdf_bytes = self._render_standardized(content, candidate_profile)
                return pdf_bytes, RenderingStrategyEnum.FALLBACK, fallback_reason

            # Attempt genuine preservation
            try:
                pdf_bytes = self._render_preserved(content, candidate_profile, meta)
                logger.info(
                    "Successfully rendered tailored resume using Original Template Preservation strategy."
                )
                return pdf_bytes, RenderingStrategyEnum.PRESERVED, None
            except Exception as exc:
                fallback_reason = (
                    f"Preservation rendering failed during compilation ({exc}); "
                    f"gracefully recovered via standardized ATS fallback."
                )
                logger.warning(fallback_reason, exc_info=True)
                pdf_bytes = self._render_standardized(content, candidate_profile)
                return pdf_bytes, RenderingStrategyEnum.FALLBACK, fallback_reason

        # Strategy B: Standardized ATS Fallback
        fallback_reason = "Standardized ATS single-column layout explicitly requested."
        pdf_bytes = self._render_standardized(content, candidate_profile)
        return pdf_bytes, RenderingStrategyEnum.FALLBACK, fallback_reason

    def _detect_template_typography(self, meta: dict[str, Any]) -> tuple[str, str, str, str, str]:
        """Infer font family and color palette from master resume template metadata.

        Returns:
            Tuple of (font_regular, font_bold, font_italic, primary_color_hex, accent_color_hex).
        """
        detected_fonts = [str(f).lower() for f in meta.get("fonts", [])]
        is_serif = any(
            keyword in font
            for font in detected_fonts
            for keyword in (
                "georgia",
                "times",
                "garamond",
                "cambria",
                "serif",
                "baskerville",
                "minion",
            )
        )

        if is_serif:
            # Serif Template: Traditional, academic, executive styling
            return (
                "Times-Roman",
                "Times-Bold",
                "Times-Italic",
                "#1E293B",  # Deep Slate
                "#1E3A8A",  # Classic Navy Accent
            )

        # Sans-serif Template: Modern, tech, clean styling
        return (
            "Helvetica",
            "Helvetica-Bold",
            "Helvetica-Oblique",
            "#111827",  # Off-Black
            "#0D5C75",  # Teal / Steel Accent
        )

    def _render_preserved(
        self,
        content: TailoredResumeContent,
        candidate_profile: CandidateProfile,
        meta: dict[str, Any],
    ) -> bytes:
        """Strategy A: Render PDF preserving original template typography, density, and styling hierarchy."""
        buffer = io.BytesIO()

        # Preserve original document margins and density budget
        page_count = meta.get("page_count", 1)
        if page_count == 1:
            margin = 0.4 * inch
            body_size = 9.0
            body_leading = 11.5
            spacer_height = 2.5
        else:
            margin = 0.55 * inch
            body_size = 9.5
            body_leading = 12.5
            spacer_height = 4.0

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
        )

        f_reg, f_bold, f_italic, c_primary, c_accent = self._detect_template_typography(meta)

        name_style = ParagraphStyle(
            "Preserved_Name",
            fontName=f_bold,
            fontSize=19,
            leading=23,
            textColor=colors.HexColor(c_primary),
            alignment=1,  # Centered
        )

        headline_style = ParagraphStyle(
            "Preserved_Headline",
            fontName=f_italic,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor(c_accent),
            alignment=1,
            spaceAfter=3,
        )

        contact_style = ParagraphStyle(
            "Preserved_Contact",
            fontName=f_reg,
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#475569"),
            alignment=1,
            spaceAfter=8,
        )

        section_heading_style = ParagraphStyle(
            "Preserved_SectionHeading",
            fontName=f_bold,
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(c_accent),
            spaceBefore=7,
            spaceAfter=2,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "Preserved_Body",
            fontName=f_reg,
            fontSize=body_size,
            leading=body_leading,
            textColor=colors.HexColor("#334155"),
        )

        exp_title_style = ParagraphStyle(
            "Preserved_ExpTitle",
            fontName=f_bold,
            fontSize=9.5,
            leading=12.5,
            textColor=colors.HexColor(c_primary),
            spaceBefore=3,
            keepWithNext=True,
        )

        exp_meta_style = ParagraphStyle(
            "Preserved_ExpMeta",
            fontName=f_italic,
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=1.5,
            keepWithNext=True,
        )

        bullet_style = ParagraphStyle(
            "Preserved_Bullet",
            fontName=f_reg,
            fontSize=body_size,
            leading=body_leading,
            textColor=colors.HexColor("#334155"),
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=1.5,
        )

        story: list[Any] = []

        # 1. Header (Name, Headline, Contact)
        story.append(Paragraph(candidate_profile.full_name, name_style))
        if content.headline:
            story.append(Paragraph(content.headline, headline_style))

        contact_items: list[str] = []
        if candidate_profile.city or candidate_profile.country:
            loc = ", ".join(filter(None, [candidate_profile.city, candidate_profile.country]))
            contact_items.append(loc)
        contact_line = (
            " • ".join(contact_items) if contact_items else "Confidential Candidate Profile"
        )
        story.append(Paragraph(contact_line, contact_style))
        story.append(
            HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(c_accent), spaceAfter=5)
        )

        # 2. Professional Summary
        if content.professional_summary:
            story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=3
                )
            )
            story.append(Paragraph(content.professional_summary, body_style))
            story.append(Spacer(1, spacer_height))

        # 3. Technical Skills
        if content.skills:
            story.append(Paragraph("AREAS OF EXPERTISE & TECHNICAL SKILLS", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=3
                )
            )
            skills_text = "  |  ".join(content.skills)
            story.append(Paragraph(skills_text, body_style))
            story.append(Spacer(1, spacer_height))

        # 4. Work Experience
        if content.experience:
            story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=3
                )
            )

            for exp in content.experience:
                title_company = f"{exp.title} — {exp.company}"
                story.append(Paragraph(title_company, exp_title_style))

                dates_loc: list[str] = []
                if exp.start_date or exp.end_date:
                    dates_loc.append(f"{exp.start_date or ''} – {exp.end_date or 'Present'}")
                if exp.location:
                    dates_loc.append(exp.location)
                if dates_loc:
                    story.append(Paragraph(" | ".join(dates_loc), exp_meta_style))

                for bullet in exp.bullet_points:
                    story.append(Paragraph(f"• {bullet}", bullet_style))
                story.append(Spacer(1, spacer_height))

        # 5. Projects
        if content.projects:
            story.append(Paragraph("TECHNICAL PROJECTS", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=3
                )
            )

            for proj in content.projects:
                proj_title = proj.name
                if proj.link:
                    proj_title += f" ({proj.link})"
                story.append(Paragraph(proj_title, exp_title_style))

                tech_line = (
                    f"Technologies: {', '.join(proj.technologies)}" if proj.technologies else ""
                )
                if tech_line:
                    story.append(Paragraph(tech_line, exp_meta_style))

                story.append(Paragraph(proj.description, body_style))
                story.append(Spacer(1, spacer_height))

        # 6. Education
        if content.education:
            story.append(Paragraph("EDUCATION & CREDENTIALS", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=3
                )
            )

            for edu in content.education:
                deg_field = edu.degree
                if edu.field_of_study:
                    deg_field += f" in {edu.field_of_study}"
                edu_line = f"{deg_field} — {edu.institution}"
                if edu.graduation_date:
                    edu_line += f" ({edu.graduation_date})"
                story.append(Paragraph(edu_line, body_style))
                story.append(Spacer(1, 2))

        doc.build(story)
        return buffer.getvalue()

    def _render_standardized(
        self,
        content: TailoredResumeContent,
        candidate_profile: CandidateProfile,
    ) -> bytes:
        """Strategy B: Render standardized single-column ATS PDF using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        styles = getSampleStyleSheet()

        name_style = ParagraphStyle(
            "ATS_Name",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1A202C"),
            alignment=1,  # Centered
        )

        headline_style = ParagraphStyle(
            "ATS_Headline",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#2B6CB0"),
            alignment=1,
            spaceAfter=4,
        )

        contact_style = ParagraphStyle(
            "ATS_Contact",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=10,
        )

        section_heading_style = ParagraphStyle(
            "ATS_SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1A202C"),
            spaceBefore=8,
            spaceAfter=2,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "ATS_Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#2D3748"),
        )

        exp_title_style = ParagraphStyle(
            "ATS_ExpTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1A202C"),
            spaceBefore=4,
            keepWithNext=True,
        )

        exp_meta_style = ParagraphStyle(
            "ATS_ExpMeta",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=2,
            keepWithNext=True,
        )

        bullet_style = ParagraphStyle(
            "ATS_Bullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=colors.HexColor("#2D3748"),
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=2,
        )

        story: list[Any] = []

        # 1. Header (Name, Headline, Contact)
        story.append(Paragraph(candidate_profile.full_name, name_style))
        if content.headline:
            story.append(Paragraph(content.headline, headline_style))

        contact_items: list[str] = []
        if candidate_profile.city or candidate_profile.country:
            loc = ", ".join(filter(None, [candidate_profile.city, candidate_profile.country]))
            contact_items.append(loc)
        contact_line = (
            " | ".join(contact_items) if contact_items else "Confidential Candidate Profile"
        )
        story.append(Paragraph(contact_line, contact_style))
        story.append(
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=6)
        )

        # 2. Professional Summary
        if content.professional_summary:
            story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=4
                )
            )
            story.append(Paragraph(content.professional_summary, body_style))
            story.append(Spacer(1, 4))

        # 3. Technical Skills
        if content.skills:
            story.append(Paragraph("CORE COMPETENCIES & TECHNICAL SKILLS", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=4
                )
            )
            skills_text = " • ".join(content.skills)
            story.append(Paragraph(skills_text, body_style))
            story.append(Spacer(1, 4))

        # 4. Work Experience
        if content.experience:
            story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=4
                )
            )

            for exp in content.experience:
                title_company = f"{exp.title} — {exp.company}"
                story.append(Paragraph(title_company, exp_title_style))

                dates_loc: list[str] = []
                if exp.start_date or exp.end_date:
                    dates_loc.append(f"{exp.start_date or ''} - {exp.end_date or 'Present'}")
                if exp.location:
                    dates_loc.append(exp.location)
                if dates_loc:
                    story.append(Paragraph(" | ".join(dates_loc), exp_meta_style))

                for bullet in exp.bullet_points:
                    story.append(Paragraph(f"• {bullet}", bullet_style))
                story.append(Spacer(1, 3))

        # 5. Projects
        if content.projects:
            story.append(Paragraph("RELEVANT PROJECTS", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=4
                )
            )

            for proj in content.projects:
                proj_title = proj.name
                if proj.link:
                    proj_title += f" ({proj.link})"
                story.append(Paragraph(proj_title, exp_title_style))

                tech_line = (
                    f"Technologies: {', '.join(proj.technologies)}" if proj.technologies else ""
                )
                if tech_line:
                    story.append(Paragraph(tech_line, exp_meta_style))

                story.append(Paragraph(proj.description, body_style))
                story.append(Spacer(1, 3))

        # 6. Education
        if content.education:
            story.append(Paragraph("EDUCATION", section_heading_style))
            story.append(
                HRFlowable(
                    width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=4
                )
            )

            for edu in content.education:
                deg_field = edu.degree
                if edu.field_of_study:
                    deg_field += f" in {edu.field_of_study}"
                edu_line = f"{deg_field} — {edu.institution}"
                if edu.graduation_date:
                    edu_line += f" ({edu.graduation_date})"
                story.append(Paragraph(edu_line, body_style))
                story.append(Spacer(1, 2))

        try:
            doc.build(story)
        except Exception as exc:
            logger.error(f"ReportLab PDF generation error: {exc}", exc_info=True)
            raise RenderingError(f"Failed to generate ATS PDF: {exc}") from exc

        return buffer.getvalue()

    def validate_pdf_binary(self, pdf_bytes: bytes) -> dict[str, Any]:
        """Validate generated PDF binary ensuring valid magic bytes, structure, and text extraction.

        Returns:
            Dictionary containing validation results and SHA-256 checksum.

        Raises:
            RenderingError: If the binary is empty, corrupted, unreadable, or missing text.
        """
        if not pdf_bytes or len(pdf_bytes) < 100:
            raise RenderingError("PDF output binary is empty or below minimum valid PDF size.")

        # 1. Validate magic bytes header
        if not pdf_bytes.startswith(b"%PDF-"):
            raise RenderingError("Corrupted PDF: binary missing valid '%PDF-' header signature.")

        # 2. Calculate SHA-256 checksum
        checksum = hashlib.sha256(pdf_bytes).hexdigest()

        # 3. Read structure with pdfplumber
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_count = len(pdf.pages)
                if page_count < 1:
                    raise RenderingError("Generated PDF contains zero pages.")

                extracted_text = ""
                for page in pdf.pages:
                    txt = page.extract_text() or ""
                    extracted_text += txt

                if not extracted_text.strip():
                    raise RenderingError(
                        "Generated PDF contains no readable text extractable by ATS engines."
                    )

                return {
                    "is_valid": True,
                    "page_count": page_count,
                    "file_size_bytes": len(pdf_bytes),
                    "checksum_sha256": checksum,
                    "text_sample": extracted_text[:200],
                }
        except RenderingError:
            raise
        except Exception as exc:
            logger.error(f"PDF validation parsing error: {exc}", exc_info=True)
            raise RenderingError(f"Generated PDF failed structural verification: {exc}") from exc
