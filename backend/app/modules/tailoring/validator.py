"""Claim Validator ensuring truthfulness and zero-hallucination guarantees in tailored resumes."""

import logging
import re

from app.modules.tailoring.evidence import CandidateEvidenceVault, extract_metrics_from_text
from app.modules.tailoring.schemas import ClaimValidationReport, TailoredResumeContent

logger = logging.getLogger(__name__)


class ClaimValidator:
    """Validates tailored resume claims against verified candidate evidence and repairs violations."""

    def __init__(self, vault: CandidateEvidenceVault) -> None:
        self.vault = vault

    def validate_and_repair(
        self,
        content: TailoredResumeContent,
    ) -> tuple[TailoredResumeContent, ClaimValidationReport]:
        """Verify tailored content against candidate evidence, repairing recoverable violations.

        Returns:
            Tuple of (repaired TailoredResumeContent, ClaimValidationReport).
        """
        report = ClaimValidationReport(
            is_valid=True,
            supported_skills=[],
            unsupported_skills=[],
            supported_metrics=[],
            unsupported_metrics=[],
            repaired_claims=[],
            violations_detected=[],
        )

        # 1. Validate & Filter Skills
        validated_skills: list[str] = []
        for skill in content.skills:
            if self.vault.is_skill_supported(skill):
                report.supported_skills.append(skill)
                validated_skills.append(skill)
            else:
                report.unsupported_skills.append(skill)
                report.repaired_claims.append(f"Pruned unverified skill: '{skill}'")

        # Fallback if all skills were pruned: inject known verified skills
        if not validated_skills:
            fallback_skills = sorted(self.vault.get_known_skills())
            if fallback_skills:
                validated_skills = fallback_skills[:10]
                report.repaired_claims.append("Restored verified skills from evidence vault")
            else:
                report.violations_detected.append(
                    "No verified skills available in candidate evidence"
                )

        content.skills = validated_skills

        # 2. Validate Technologies and Metrics in Projects
        for proj in content.projects:
            valid_techs: list[str] = []
            for tech in proj.technologies:
                if self.vault.is_skill_supported(tech):
                    valid_techs.append(tech)
                else:
                    report.repaired_claims.append(
                        f"Pruned unverified project tech '{tech}' from project '{proj.name}'"
                    )
            proj.technologies = valid_techs

            if proj.description:
                proj_metrics = extract_metrics_from_text(proj.description)
                repaired_desc = proj.description
                for metric in proj_metrics:
                    if self.vault.is_metric_supported(metric):
                        report.supported_metrics.append(metric)
                    else:
                        report.unsupported_metrics.append(metric)
                        pattern = re.compile(re.escape(metric), re.IGNORECASE)
                        repaired_desc = pattern.sub("significantly", repaired_desc)
                        report.repaired_claims.append(
                            f"Sanitized hallucinated metric '{metric}' in project '{proj.name}'"
                        )
                proj.description = re.sub(r"\s+", " ", repaired_desc).strip()

        # 3. Validate Metrics in Professional Summary
        if content.professional_summary:
            summary_metrics = extract_metrics_from_text(content.professional_summary)
            repaired_summary = content.professional_summary
            for metric in summary_metrics:
                if self.vault.is_metric_supported(metric):
                    report.supported_metrics.append(metric)
                else:
                    report.unsupported_metrics.append(metric)
                    pattern = re.compile(re.escape(metric), re.IGNORECASE)
                    repaired_summary = pattern.sub("significantly", repaired_summary)
                    report.repaired_claims.append(
                        f"Sanitized hallucinated metric '{metric}' in professional summary"
                    )
            content.professional_summary = re.sub(r"\s+", " ", repaired_summary).strip()

        # 4. Validate Metrics in Headline
        if content.headline:
            headline_metrics = extract_metrics_from_text(content.headline)
            repaired_headline = content.headline
            for metric in headline_metrics:
                if self.vault.is_metric_supported(metric):
                    report.supported_metrics.append(metric)
                else:
                    report.unsupported_metrics.append(metric)
                    pattern = re.compile(re.escape(metric), re.IGNORECASE)
                    repaired_headline = pattern.sub("", repaired_headline)
                    report.repaired_claims.append(
                        f"Sanitized hallucinated metric '{metric}' in headline"
                    )
            content.headline = re.sub(r"\s+", " ", repaired_headline).strip()

        # 5. Validate Employers in Experience
        for exp in content.experience:
            if not self.vault.is_employer_supported(exp.company):
                report.violations_detected.append(
                    f"Unverified employer claimed: '{exp.company}' not found in candidate history"
                )

        # 6. Validate and Sanitize Metrics in Experience Bullets
        for exp in content.experience:
            sanitized_bullets: list[str] = []
            for bullet in exp.bullet_points:
                bullet_metrics = extract_metrics_from_text(bullet)
                repaired_bullet = bullet

                for metric in bullet_metrics:
                    if self.vault.is_metric_supported(metric):
                        report.supported_metrics.append(metric)
                    else:
                        report.unsupported_metrics.append(metric)
                        # Attempt to sanitize the hallucinated metric token
                        pattern = re.compile(re.escape(metric), re.IGNORECASE)
                        cleaned_bullet = pattern.sub("significantly", repaired_bullet)
                        cleaned_bullet = re.sub(
                            r"\bby significantly\b", "significantly", cleaned_bullet
                        )
                        cleaned_bullet = re.sub(r"\s+", " ", cleaned_bullet).strip()

                        if cleaned_bullet != repaired_bullet:
                            repaired_bullet = cleaned_bullet
                            report.repaired_claims.append(
                                f"Sanitized hallucinated metric '{metric}' in experience for '{exp.company}'"
                            )
                        else:
                            report.violations_detected.append(
                                f"Unrepairable hallucinated metric '{metric}' in bullet: '{bullet}'"
                            )

                sanitized_bullets.append(repaired_bullet)
            exp.bullet_points = sanitized_bullets

        # Determine overall validity
        if report.violations_detected:
            report.is_valid = False
            logger.warning(
                f"Resume tailoring validation failed with {len(report.violations_detected)} violations: "
                f"{report.violations_detected}"
            )
        else:
            report.is_valid = True

        return content, report
