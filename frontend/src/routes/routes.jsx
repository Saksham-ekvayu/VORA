/* eslint-disable react/prop-types */
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { lazy, Suspense, useEffect } from "react";
import Layout from "../layout/Layout";
import ProtectedRoute from "../routes/components/ProtectedRoute";
import { useAuth } from "../context/authContext/useAuth";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";

const MyProfile = lazy(() => import("../pages/profile-management/MyProfile"));

// Import role-based routes
import adminRoutes from "./components/adminRoutes";
import expertRoutes from "./components/expertRoutes";
import customerAdminRoutes from "./components/customerAdminRoutes";
import authRoutes from "./components/authRoutes";
import userRoutes from "./components/userRoutes";
import auditorRoutes from "./components/auditorRoutes";
import internalExpertRoutes from "./components/internalExpertRoutes";
import {
  ROLE_ADMIN,
  ROLE_EXPERT,
  ROLE_CUSTOMER_ADMIN,
  ROLE_USER,
  ROLE_AUDITOR,
  ROLE_INTERNAL_EXPERT,
} from "../utils/commonUtils";

/**
 * Redirect component for catch-all routes
 * Navigates to dashboard for authenticated users, login for others
 */
const CatchAllRedirect = ({ isAuthenticated, user }) => {
  const navigate = useNavigate();

  useEffect(() => {
    const redirectPath = isAuthenticated && user ? "/dashboard" : "/auth/login";
    navigate(redirectPath, { replace: true });
  }, [navigate, isAuthenticated, user]);

  return null;
};

/**
 * Get role-based routes configuration
 * @param {string} role - User role
 * @param {boolean} isAuthenticated - Authentication status
 * @returns {Array} Route elements for the user role
 */
const getRoleBasedRoutes = (role, isAuthenticated) => {
  if (!isAuthenticated || !role) {
    return authRoutes;
  }

  const roleRoutesMap = {
    [ROLE_ADMIN]: adminRoutes,
    [ROLE_EXPERT]: expertRoutes,
    [ROLE_CUSTOMER_ADMIN]: customerAdminRoutes,
    [ROLE_USER]: userRoutes,
    [ROLE_AUDITOR]: auditorRoutes,
    [ROLE_INTERNAL_EXPERT]: internalExpertRoutes,
  };

  return roleRoutesMap[role.toLowerCase()] || customerAdminRoutes;
};

/**
 * Main application routes component
 * Handles authentication, role-based routing, and shared routes
 */
function AppRoutes() {
  const { isAuthenticated, user } = useAuth();

  return (
    <Routes>
      {/* ================= DYNAMIC ROUTES ================= */}
      {/* Role-based routes - shown based on authentication and user role */}
      {getRoleBasedRoutes(user?.role, isAuthenticated)}

      {/* ================= SHARED ROUTES ================= */}
      {/* My Profile - Only for authenticated users */}
      {isAuthenticated && (
        <Route
          path="/my-profile"
          element={
            <ProtectedRoute>
              <Layout>
                <Suspense
                  fallback={
                    <LoadingSpinner className="min-h-[calc(100vh-100px)]" />
                  }
                >
                  <MyProfile />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          }
        />
      )}

      {/* ================= REDIRECTS ================= */}
      {/* Root redirect - dashboard for authenticated, login for non-authenticated */}
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <Navigate to="/auth/login" replace />
          )
        }
      />

      {/* Catch all - redirect to dashboard or login based on auth status */}
      <Route
        path="*"
        element={
          <CatchAllRedirect isAuthenticated={isAuthenticated} user={user} />
        }
      />
    </Routes>
  );
}

export default AppRoutes;
