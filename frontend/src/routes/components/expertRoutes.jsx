/* eslint-disable react-refresh/only-export-components */
import { createProtectedRoutes } from "../utils/routeFactory";
import {
  ComparisonGapAnalysis,
  DeploymentFramework,
  DeploymentFrameworkDetail,
  ExpertDashboard,
  Framework,
  FrameworkCategory,
  FrameworkDetail,
} from "../utils/routeImports";

const expertRoutes = createProtectedRoutes([
  { key: "expert-dashboard", path: "/dashboard", component: ExpertDashboard },
  { key: "frameworks", path: "/frameworks", component: Framework },
  {
    key: "framework-detail",
    path: "/frameworks/:id",
    component: FrameworkDetail,
  },
  {
    key: "framework-category",
    path: "/framework-categories",
    component: FrameworkCategory,
  },
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
]);

export default expertRoutes;
