/* eslint-disable react-refresh/only-export-components */
import { createProtectedRoutes } from "../utils/routeFactory";
import {
  AssignedFrameworkDetails,
  AssignedFrameworks,
  ComparisonGapAnalysis,
  CustomerAdminDashboard,
  DeploymentDocument,
  DeploymentDocumentDetail,
  DeploymentFramework,
  DeploymentFrameworkDetail,
  FrameworkWorkflowSetup,
  FrameworkWorkflowList,
  MonitoringSetup,
  Profiles,
  McpMonitoring,
} from "../utils/routeImports";

const customerAdminRoutes = createProtectedRoutes([
  { key: "dashboard", path: "/dashboard", component: CustomerAdminDashboard },
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
  {
    key: "framework-workflow-list",
    path: "/framework-workflow",
    component: FrameworkWorkflowList,
  },
  {
    key: "framework-workflow-setup",
    path: "/framework-workflow/setup",
    component: FrameworkWorkflowSetup,
  },
]);

export default customerAdminRoutes;
