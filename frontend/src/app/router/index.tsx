import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/app/layouts/AppLayout";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { CandidateProfilePage } from "@/features/candidate/pages/CandidateProfilePage";
import { PipelineMonitoringPage } from "@/features/pipeline/pages/PipelineMonitoringPage";
import { JobsDiscoveryPage } from "@/features/jobs/pages/JobsDiscoveryPage";
import { JobDetailPage } from "@/features/jobs/pages/JobDetailPage";
import { MatchesPage } from "@/features/matches/pages/MatchesPage";
import { MatchDetailPage } from "@/features/matches/pages/MatchDetailPage";
import { PlaceholderPage } from "@/features/placeholder/pages/PlaceholderPage";
import { Bell, FileText, Settings } from "lucide-react";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: "profile",
        element: <CandidateProfilePage />,
      },
      {
        path: "jobs",
        element: <JobsDiscoveryPage />,
      },
      {
        path: "jobs/:jobId",
        element: <JobDetailPage />,
      },
      {
        path: "discovery",
        element: <Navigate to="/jobs" replace />,
      },
      {
        path: "matches",
        element: <MatchesPage />,
      },
      {
        path: "matches/:matchId",
        element: <MatchDetailPage />,
      },
      {
        path: "pipeline",
        element: <PipelineMonitoringPage />,
      },
      {
        path: "resumes",
        element: (
          <PlaceholderPage
            title="Resumes & Tailoring"
            description="Master resume management, deterministic parsing, and truthful tailored PDF generation"
            icon={FileText}
            targetMilestone="Milestone 14"
            plannedFeatures={[
              "Master resume PDF/DOCX upload and active version toggle",
              "Parsed structured content and template metadata inspection",
              "Truthful tailored resume generation against candidate Evidence Vault",
              "ATS single-column PDF previews and direct downloads",
            ]}
          />
        ),
      },
      {
        path: "notifications",
        element: (
          <PlaceholderPage
            title="Notifications"
            description="Immediate email delivery logs, PDF attachments, and retry tracking"
            icon={Bell}
            targetMilestone="Milestone 15"
            plannedFeatures={[
              "Immediate email dispatch delivery audit log",
              "Recipient delivery confirmation and SMTP message-IDs",
              "Attached tailored PDF verification and preview",
              "Delivery failure reasons and automatic retry tracking",
            ]}
          />
        ),
      },
      {
        path: "settings",
        element: (
          <PlaceholderPage
            title="Settings & Configuration"
            description="System preferences, API connections, and scheduler configurations"
            icon={Settings}
            targetMilestone="Milestone 16"
            plannedFeatures={[
              "Backend API connection and proxy configuration",
              "Ollama LLM model selection and timeout thresholds",
              "Automated pipeline scheduler frequency and Redis leader status",
              "SMTP notification provider credentials and testing",
            ]}
          />
        ),
      },
      {
        path: "*",
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
