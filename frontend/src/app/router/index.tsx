import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/app/layouts/AppLayout";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { CandidateProfilePage } from "@/features/candidate/pages/CandidateProfilePage";
import { PipelineMonitoringPage } from "@/features/pipeline/pages/PipelineMonitoringPage";
import { PipelineRunDetailPage } from "@/features/pipeline/pages/PipelineRunDetailPage";
import { NotificationsPage } from "@/features/notifications/pages/NotificationsPage";
import { NotificationDetailPage } from "@/features/notifications/pages/NotificationDetailPage";
import { JobsDiscoveryPage } from "@/features/jobs/pages/JobsDiscoveryPage";
import { JobDetailPage } from "@/features/jobs/pages/JobDetailPage";
import { MatchesPage } from "@/features/matches/pages/MatchesPage";
import { MatchDetailPage } from "@/features/matches/pages/MatchDetailPage";
import { ResumesPage } from "@/features/resumes/pages/ResumesPage";
import { ResumeDetailPage } from "@/features/resumes/pages/ResumeDetailPage";
import { TailoredResumesPage } from "@/features/tailored-resumes/pages/TailoredResumesPage";
import { TailoredResumeDetailPage } from "@/features/tailored-resumes/pages/TailoredResumeDetailPage";
import { SettingsPage } from "@/features/settings/pages/SettingsPage";

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
        path: "pipeline/:runId",
        element: <PipelineRunDetailPage />,
      },
      {
        path: "notifications",
        element: <NotificationsPage />,
      },
      {
        path: "notifications/:notificationId",
        element: <NotificationDetailPage />,
      },
      {
        path: "settings",
        element: <SettingsPage />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
