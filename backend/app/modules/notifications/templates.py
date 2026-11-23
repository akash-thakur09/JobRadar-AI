"""Email template generators for Job Match alerts and tailored resume notifications."""

import html
from typing import TYPE_CHECKING

from app.modules.notifications.email.protocol import EmailAttachment, EmailMessage

if TYPE_CHECKING:
    from app.modules.candidate.models import CandidateProfile
    from app.modules.jobs.models import Job
    from app.modules.matching.models import JobMatch
    from app.modules.tailoring.models import TailoredResume


def build_job_notification_email(
    candidate_profile: "CandidateProfile",
    job: "Job",
    job_match: "JobMatch",
    tailored_resume: "TailoredResume",
    pdf_bytes: bytes,
    recipient_email: str,
) -> EmailMessage:
    """Build a complete EmailMessage containing verified job information, match metrics, and tailored PDF attachment."""
    candidate_name = candidate_profile.full_name or "Candidate"
    company_name = job.canonical_company_name
    job_title = job.title
    location = job.normalized_location or "Location not specified"
    workplace_type = (
        job.workplace_type.value
        if hasattr(job.workplace_type, "value")
        else str(job.workplace_type)
    )
    application_url = job.canonical_application_url
    match_score = int(round(float(job_match.final_score)))
    explanation = job_match.match_explanation or "Strong alignment with candidate qualifications."

    # Recommendation from semantic analysis if present
    recommendation = None
    if job_match.match_explanation_details and isinstance(
        job_match.match_explanation_details, dict
    ):
        recommendation = job_match.match_explanation_details.get("recommendation")

    safe_candidate_name = html.escape(candidate_name)
    safe_company_name = html.escape(company_name)
    safe_job_title = html.escape(job_title)
    safe_location = html.escape(location)
    safe_workplace_type = html.escape(workplace_type)
    safe_explanation = html.escape(explanation)
    safe_app_url = html.escape(application_url)

    rec_badge_html = ""
    if recommendation:
        safe_rec = html.escape(str(recommendation).replace("_", " "))
        rec_badge_html = f"""
        <div style="margin-top: 8px;">
            <span style="background-color: #E0E7FF; color: #3730A3; font-weight: 600; font-size: 12px; padding: 3px 8px; border-radius: 4px; text-transform: uppercase;">
                Recommendation: {safe_rec}
            </span>
        </div>
        """

    subject = f"Job Match Found: {job_title} at {company_name} ({match_score}% Match)"

    # Formulate Plain-Text Body
    text_body = f"""Hello {candidate_name},

JobRadar AI has identified a qualified job match for your profile:

{job_title} at {company_name}
Match Score: {match_score}%
Location: {location} ({workplace_type})
Application Link: {application_url}

Match Summary:
{explanation}

Your tailored, ATS-optimized resume has been generated and is attached to this email ({tailored_resume.file_name}).

Best regards,
JobRadar AI Team
"""

    # Formulate HTML Body
    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; color: #1E293B; margin: 0; padding: 24px;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">

    <!-- Header -->
    <div style="background-color: #0F172A; padding: 24px; text-align: center; color: #FFFFFF;">
      <h1 style="margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.5px;">JobRadar AI Alert</h1>
      <p style="margin: 6px 0 0 0; font-size: 14px; color: #94A3B8;">Tailored Job Intelligence & Opportunity Delivery</p>
    </div>

    <!-- Main Content -->
    <div style="padding: 24px;">
      <p style="font-size: 15px; margin: 0 0 16px 0; color: #334155;">
        Hello <strong>{safe_candidate_name}</strong>,
      </p>
      <p style="font-size: 14px; margin: 0 0 20px 0; color: #475569; line-height: 1.5;">
        A high-confidence job opportunity has matched your professional qualifications and career preferences.
      </p>

      <!-- Opportunity Card -->
      <div style="background-color: #F1F5F9; border-radius: 6px; padding: 18px; margin-bottom: 20px; border-left: 4px solid #2563EB;">
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
          <h2 style="font-size: 18px; margin: 0; color: #0F172A;">{safe_job_title}</h2>
        </div>
        <p style="font-size: 14px; font-weight: 600; color: #2563EB; margin: 4px 0 12px 0;">{safe_company_name}</p>

        <table style="width: 100%; font-size: 13px; color: #475569; border-collapse: collapse;">
          <tr>
            <td style="padding: 4px 0; width: 110px; font-weight: 600;">Location:</td>
            <td style="padding: 4px 0;">{safe_location} ({safe_workplace_type})</td>
          </tr>
          <tr>
            <td style="padding: 4px 0; font-weight: 600;">Match Score:</td>
            <td style="padding: 4px 0;">
              <span style="background-color: #DCFCE7; color: #166534; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                {match_score}% Match
              </span>
            </td>
          </tr>
        </table>
        {rec_badge_html}
      </div>

      <!-- Match Explanation -->
      <div style="margin-bottom: 24px;">
        <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748B; margin: 0 0 8px 0;">Match Insights</h3>
        <p style="font-size: 13.5px; line-height: 1.5; color: #334155; margin: 0; background-color: #FAFAFA; padding: 12px; border-radius: 4px; border: 1px solid #E2E8F0;">
          {safe_explanation}
        </p>
      </div>

      <!-- Resume Attachment Notice -->
      <div style="background-color: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 6px; padding: 14px; margin-bottom: 24px; text-align: left;">
        <p style="margin: 0; font-size: 13px; color: #334155;">
          📎 <strong>Tailored Resume Attached:</strong> <code>{html.escape(tailored_resume.file_name or "Tailored_Resume.pdf")}</code><br/>
          <span style="font-size: 12px; color: #64748B;">
            This resume was truthful, ATS-optimized, and specifically tailored for this role using your verified credentials.
          </span>
        </p>
      </div>

      <!-- Action Button -->
      <div style="text-align: center; margin: 28px 0 16px 0;">
        <a href="{safe_app_url}" target="_blank" style="display: inline-block; background-color: #2563EB; color: #FFFFFF; font-weight: 600; font-size: 14px; text-decoration: none; padding: 12px 28px; border-radius: 6px; box-shadow: 0 2px 4px rgba(37,99,235,0.2);">
          Apply to Position &rarr;
        </a>
      </div>
    </div>

    <!-- Footer -->
    <div style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px; text-align: center; font-size: 12px; color: #94A3B8;">
      <p style="margin: 0 0 4px 0;">JobRadar AI — Automated High-Precision Career Intelligence</p>
      <p style="margin: 0;">This email was delivered based on your active candidate profile and verified job match.</p>
    </div>

  </div>
</body>
</html>"""

    attachment = EmailAttachment(
        filename=tailored_resume.file_name or "Tailored_Resume.pdf",
        content=pdf_bytes,
        content_type="application/pdf",
    )

    return EmailMessage(
        to=recipient_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        attachments=[attachment],
    )
