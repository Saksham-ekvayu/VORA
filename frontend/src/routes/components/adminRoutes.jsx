/* eslint-disable react-refresh/only-export-components */
import { createProtectedRoutes } from "../utils/routeFactory";
import {
  AdminDashboard,
  Profiles,
  Category,
  FrameworkAccessManage,
  FrameworkAssignment,
  Customers,
  CustomerDetails,
  UserDetails,
} from "../utils/routeImports";

const adminRoutes = createProtectedRoutes([
  { key: "dashboard", path: "/dashboard", component: AdminDashboard },
  { key: "profiles", path: "/profiles", component: Profiles },
  { key: "profile", path: "/profiles/:id", component: UserDetails },
  { key: "customers", path: "/customers", component: Customers },
  {
    key: "customer-details",
    path: "/customers/:id",
    component: CustomerDetails,
  },
  {
    key: "framework-category",
    path: "/framework-categories",
    component: Category,
  },
  {
    key: "framework-access",
    path: "/framework-access",
    component: FrameworkAccessManage,
  },
  {
    key: "framework-assignment",
    path: "/framework-assignments",
    component: FrameworkAssignment,
  },
]);

export default adminRoutes;
