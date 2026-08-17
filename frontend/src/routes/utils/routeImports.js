/**
 * Centralized Route Imports
 * Eliminates duplicate lazy imports across all route files
 * Reduces duplication by ~60%
 */

import { lazy } from "react";

// Dashboard Pages
export const AdminDashboard = lazy(
  () => import("@/pages/dashboard-management/AdminDashboard")
);
export const ExpertDashboard = lazy(
  () => import("@/pages/dashboard-management/ExpertDashboard")
);
export const CustomerAdminDashboard = lazy(
  () => import("@/pages/dashboard-management/CustomerAdminDashboard")
);
export const CustomerExpertDashboard = lazy(
  () => import("@/pages/dashboard-management/CustomerExpertDashboard")
);
export const UserDashboard = lazy(
  () => import("@/pages/dashboard-management/UserDashboard")
);
export const AuditorDashboard = lazy(
  () => import("@/pages/dashboard-management/AuditorDashboard")
);
export const FrameworkDetailDashboard = lazy(
  () => import("@/pages/dashboard-management/FrameworkDetailDashboard")
);
export const ControlsPassing = lazy(
  () => import("@/pages/dashboard-management/ControlsPassing")
);
export const ExtraControls = lazy(
  () => import("@/pages/dashboard-management/ExtraControls")
);
export const CriticalGaps = lazy(
  () => import("@/pages/dashboard-management/CriticalGaps")
);
export const OverallProtection = lazy(
  () => import("@/pages/dashboard-management/OverallProtection")
);
export const DeploymentPoints = lazy(
  () => import("@/pages/dashboard-management/DeploymentPoints")
);
export const MonitoringSetup = lazy(
  () => import("@/pages/monitoring-setup/MonitoringSetup")
);

// Profile Pages
export const Profiles = lazy(
  () => import("@/pages/profile-management/Profiles")
);
export const UserDetails = lazy(
  () => import("@/pages/profile-management/UserDetails")
);

// Customers Pages
export const Customers = lazy(
  () => import("@/pages/customer-management/Customers")
);
export const CustomerDetails = lazy(
  () => import("@/pages/customer-management/CustomerDetails")
);

// Framework Pages
export const Framework = lazy(
  () => import("@/pages/framework-management/Framework")
);
export const FrameworkDetail = lazy(
  () => import("@/pages/framework-management/FrameworkDetail")
);
export const FrameworkCategory = lazy(
  () => import("@/pages/framework-management/FrameworkCategory")
);

// Framework Category Access Management Pages
export const Category = lazy(
  () =>
    import("@/pages/framework-category-access-management/framework-category-manage/Category")
);
export const FrameworkAccessManage = lazy(
  () =>
    import("@/pages/framework-category-access-management/framework-access-manage/FrameworkAccess")
);
export const FrameworkAssignment = lazy(
  () =>
    import("@/pages/framework-category-access-management/framework-assignment-manage/FrameworkAssignment")
);

// Deployment Framework Pages
export const DeploymentFramework = lazy(
  () => import("@/pages/deployment-framework-management/DeploymentFramework")
);
export const DeploymentFrameworkDetail = lazy(
  () =>
    import("@/pages/deployment-framework-management/DeploymentFrameworkDetail")
);
export const ComparisonGapAnalysis = lazy(
  () => import("@/pages/deployment-framework-management/ComparisonGapAnalysis")
);
export const AssignedFrameworks = lazy(
  () => import("@/pages/deployment-framework-management/AssignedFrameworks")
);
export const AssignedFrameworkDetails = lazy(
  () =>
    import("@/pages/deployment-framework-management/AssignedFrameworkDetails")
);

// Deployment Document Pages
export const DeploymentDocument = lazy(
  () => import("@/pages/deployment-document-management/DeploymentDocument")
);
export const DeploymentDocumentDetail = lazy(
  () =>
    import("@/pages/deployment-document-management/DeploymentDocumentDetail")
);

// Auth Pages
export const Login = lazy(() => import("@/pages/auth/Login"));
export const Register = lazy(() => import("@/pages/auth/Register"));
export const ForgotPassword = lazy(() => import("@/pages/auth/ForgotPassword"));
export const ResetPassword = lazy(() => import("@/pages/auth/ResetPassword"));
export const VerifyEmail = lazy(() => import("@/pages/auth/VerifyEmail"));
export const VerifyOtp = lazy(() => import("@/pages/auth/VerifyOtp"));

// Workflow Management
export const FrameworkWorkflowSetup = lazy(
  () => import("@/pages/workflow-management/FrameworkWorkflowSetup")
);
export const FrameworkWorkflowList = lazy(
  () => import("@/pages/workflow-management/FrameworkWorkflowList")
);
