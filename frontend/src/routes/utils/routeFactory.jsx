/**
 * Route Factory Utility
 * Eliminates duplicate route wrapping patterns across all route files
 * Reduces code duplication by ~60% in routes directory
 */

import { Suspense } from "react";
import { Route } from "react-router-dom";
import Layout from "@/layout/Layout";
import ProtectedRoute from "../components/ProtectedRoute";
import PublicRoute from "../components/PublicRoute";
import AuthLayout from "@/layout/AuthLayout";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";

const fallback = <LoadingSpinner className="min-h-[calc(100vh-100px)]" />;

/**
 * Create a protected route with Layout and Suspense wrapper
 * @param {string} key - Unique key for the route
 * @param {string} path - Route path
 * @param {React.Component} Component - Component to render
 * @returns {React.ReactElement} Route element
 */
export const createProtectedRoute = (key, path, Component) => (
  <Route
    key={key}
    path={path}
    element={
      <ProtectedRoute>
        <Layout>
          <Suspense fallback={fallback}>
            <Component />
          </Suspense>
        </Layout>
      </ProtectedRoute>
    }
  />
);

/**
 * Create multiple protected routes from a configuration array
 * @param {Array} routeConfigs - Array of { key, path, component } objects
 * @returns {Array} Array of Route elements
 */
export const createProtectedRoutes = (routeConfigs) =>
  routeConfigs.map(({ key, path, component }) =>
    createProtectedRoute(key, path, component)
  );

/**
 * Create a public auth route with AuthLayout wrapper
 * @param {string} key - Unique key for the route
 * @param {string} path - Route path
 * @param {React.Component} Component - Component to render
 * @returns {React.ReactElement} Route element
 */
export const createAuthRoute = (key, path, Component) => (
  <Route
    key={key}
    path={path}
    element={
      <PublicRoute>
        <AuthLayout>
          <Suspense fallback={fallback}>
            <Component />
          </Suspense>
        </AuthLayout>
      </PublicRoute>
    }
  />
);

/**
 * Create multiple auth routes from a configuration array
 * @param {Array} routeConfigs - Array of { key, path, component } objects
 * @returns {Array} Array of Route elements
 */
export const createAuthRoutes = (routeConfigs) =>
  routeConfigs.map(({ key, path, component }) =>
    createAuthRoute(key, path, component)
  );
