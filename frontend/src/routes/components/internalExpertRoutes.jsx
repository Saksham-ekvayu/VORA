/* eslint-disable react-refresh/only-export-components */
import { createProtectedRoutes } from "../utils/routeFactory";
import {
  AssignedFrameworkDetails,
  AssignedFrameworks,
  AuditorDashboard,
  ComparisonGapAnalysis,
  // CustomerExpertDashboard,
  DeploymentDocument,
  DeploymentDocumentDetail,
  DeploymentFramework,
  DeploymentFrameworkDetail,
  Profiles,
} from "../utils/routeImports";

const internalExpertRoutes = createProtectedRoutes([
  // { key: "dashboard", path: "/dashboard", component: CustomerExpertDashboard },
  { key: "dashboard", path: "/dashboard", component: AuditorDashboard },
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

export default internalExpertRoutes;
