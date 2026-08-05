/* eslint-disable react-refresh/only-export-components */
import { createProtectedRoutes } from "../utils/routeFactory";
import {
  AssignedFrameworkDetails,
  AssignedFrameworks,
  ComparisonGapAnalysis,
  AuditorDashboard,
  DeploymentDocument,
  DeploymentDocumentDetail,
  DeploymentFramework,
  DeploymentFrameworkDetail,
  FrameworkDetailDashboard,
  ControlsPassingPage,
  ExtraControlsPage,
  CriticalGapsPage,
  OverallProtectionPage,
  DeploymentPointsPage,
  Profiles,
} from "../utils/routeImports";

const auditorRoutes = createProtectedRoutes([
  { key: "dashboard", path: "/dashboard", component: AuditorDashboard },
  {
    key: "framework-detail-dashboard",
    path: "/dashboard/framework/:frameworkId",
    component: FrameworkDetailDashboard,
  },
  {
    key: "controls-passing",
    path: "/dashboard/controls-passing",
    component: ControlsPassingPage,
  },
  {
    key: "extra-controls",
    path: "/dashboard/extra-controls",
    component: ExtraControlsPage,
  },
  {
    key: "critical-gaps",
    path: "/dashboard/critical-gaps",
    component: CriticalGapsPage,
  },
  {
    key: "overall-protection",
    path: "/dashboard/overall-protection",
    component: OverallProtectionPage,
  },
  {
    key: "deployment-points",
    path: "/dashboard/deployment-points",
    component: DeploymentPointsPage,
  },
  { key: "profiles", path: "/profiles", component: Profiles },
  {
    key: "deployment-frameworks",
    path: "/deployment-frameworks",
    component: DeploymentFramework,
  },
  {
    key: "deployment-framework-detail",
    path: "/deployment-frameworks/:id",
    component: DeploymentFrameworkDetail,
  },
  {
    key: "comparison-and-gap-analysis",
    path: "/deployment-frameworks/:id/comparison-and-gap-analysis",
    component: ComparisonGapAnalysis,
  },
  {
    key: "assigned-frameworks",
    path: "/assigned-frameworks",
    component: AssignedFrameworks,
  },
  {
    key: "assigned-frameworks-detail",
    path: "/assigned-frameworks/:id",
    component: AssignedFrameworkDetails,
  },
  {
    key: "document",
    path: "/deployment-documents",
    component: DeploymentDocument,
  },
  {
    key: "document-detail",
    path: "/deployment-documents/:id",
    component: DeploymentDocumentDetail,
  },
]);

export default auditorRoutes;
