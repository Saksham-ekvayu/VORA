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
  ControlsPassing,
  ExtraControls,
  CriticalGaps,
  OverallProtection,
  DeploymentPoints,
  Profiles,
  MonitoringSetup,
  McpMonitoring,
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
    component: ControlsPassing,
  },
  {
    key: "extra-controls",
    path: "/dashboard/extra-controls",
    component: ExtraControls,
  },
  {
    key: "critical-gaps",
    path: "/dashboard/critical-gaps",
    component: CriticalGaps,
  },
  {
    key: "overall-protection",
    path: "/dashboard/overall-protection",
    component: OverallProtection,
  },
  {
    key: "deployment-points",
    path: "/dashboard/deployment-points",
    component: DeploymentPoints,
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
  {
    key: "mcp-server-monitoring",
    path: "/mcp-server/monitoring",
    component: McpMonitoring,
  },
  {
    key: "mcp-server-monitoring-setup",
    path: "/mcp-server/monitoring-setup",
    component: MonitoringSetup,
  },
]);

export default auditorRoutes;
