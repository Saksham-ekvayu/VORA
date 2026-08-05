/* eslint-disable react-refresh/only-export-components */
import { createProtectedRoutes } from "../utils/routeFactory";
import {
  DeploymentDocument,
  DeploymentDocumentDetail,
  DeploymentFramework,
  DeploymentFrameworkDetail,
  UserDashboard,
} from "../utils/routeImports";

const userRoutes = createProtectedRoutes([
  { key: "dashboard", path: "/dashboard", component: UserDashboard },
  {
    key: "document",
    path: "/deployment-documents",
    component: DeploymentDocument,
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
    key: "document-detail",
    path: "/deployment-documents/:id",
    component: DeploymentDocumentDetail,
  },
]);

export default userRoutes;
