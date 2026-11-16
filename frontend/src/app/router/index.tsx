import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/app/layouts/AppLayout";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { CandidateProfilePage } from "@/features/candidate/pages/CandidateProfilePage";
import { PipelineMonitoringPage } from "@/features/pipeline/pages/PipelineMonitoringPage";
import { JobsDiscoveryPage } from "@/features/jobs/pages/JobsDiscoveryPage";
import { JobDetailPage } from "@/features/jobs/pages/JobDetailPage";
import { MatchesPage } from "@/features/matches/pages/MatchesPage";
import { MatchDetailPage } from "@/features/matches/pages/MatchDetailPage";
import { ResumesPage } from "@/features/resumes/pages/ResumesPage";
import { ResumeDetailPage } from "@/features/resumes/pages/ResumeDetailPage";
import { TailoredResumesPage } from "@/features/tailored-resumes/pages/TailoredResumesPage";
import { TailoredResumeDetailPage } from "@/features/tailored-resumes/pages/TailoredResumeDetailPage";
import { PlaceholderPage } from "@/features/placeholder/pages/PlaceholderPage";
import { Bell, Settings } from "lucide-react";

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
        path: "resumes",
        element: <ResumesPage />,
      },
      {
        path: "resumes/:resumeId",
        element: <ResumeDetailPage />,
      },
      {
        path: "tailored-resumes",
        element: <TailoredResumesPage />,
      },
      {
        path: "tailored-resumes/:tailoredResumeId",
        element: <TailoredResumeDetailPage />,
      },
      {
        path: "pipeline",
        element: <PipelineMonitoringPage />,
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
