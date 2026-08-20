/**
 * Dashboard Service
 * Handles dashboard analytics API calls
 */

import { apiRequest } from "./apiService";

const ADMIN_BASE = "/dashboard/admin";
// const EXPERT_BASE = "/dashboard/expert";
const CUSTOMER_BASE = "/dashboard/customer-admin";
const AUDITOR_BASE = "/dashboard/auditor";

/**
 * Build a query string from an optional date range object.
 * @param {{ startDate?: string, endDate?: string }} [dateRange]
 */
function buildDateQuery(dateRange) {
  if (!dateRange) return "";
  const params = new URLSearchParams();
  if (dateRange.startDate) params.set("startDate", dateRange.startDate);
  if (dateRange.endDate) params.set("endDate", dateRange.endDate);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

/**
 * Build a query string from an optional framework ID.
 * @param {string} [frameworkId]
 */
function buildFrameworkQuery(frameworkId) {
  if (!frameworkId || frameworkId === "all") return "";
  const params = new URLSearchParams();
  params.set("frameworkId", frameworkId);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

/**
 * Get admin dashboard analytics
 * @param {{ startDate?: string, endDate?: string }} [dateRange]
 */
export function getAdminDashboardAnalytics(dateRange) {
  return apiRequest(
    `${ADMIN_BASE}/analytics${buildDateQuery(dateRange)}`,
    true
  );
}

/**
 * Get Auditor Dashboard Analytics
 * @param {{ startDate?: string, endDate?: string }} [dateRange]
 * @returns {Promise} Dashboard analytics data
 */
export async function getAuditorDashboardAnalytics(dateRange) {
  return apiRequest(
    `${AUDITOR_BASE}/analytics${buildDateQuery(dateRange)}`,
    true
  );
}

/**
 * Get Auditor Framework Details
 * @param {string} deploymentFrameworkId - The deployment framework ID
 * @returns {Promise} Framework details data
 */
export async function getAuditorFrameworkDetails(deploymentFrameworkId) {
  return apiRequest(`${AUDITOR_BASE}/framework-details/${deploymentFrameworkId}`, true);
}

/**
 * Get Auditor Overall Protection (Table + Stats)
 * @param {Object} [params] - Query parameters
 * @returns {Promise} Overall protection data
 */
export async function getAuditorOverallProtection(params) {
  const query = new URLSearchParams(params).toString();
  const endpoint = query
    ? `${AUDITOR_BASE}/overall-protection?${query}`
    : `${AUDITOR_BASE}/overall-protection`;

  return apiRequest(endpoint, true);
}

/**
 * Get Auditor Critical Gaps
 * @param {Object} [params] - Query parameters
 * @returns {Promise} Critical gaps data
 */
export async function getAuditorCriticalGaps(params) {
  const query = new URLSearchParams(params).toString();
  const endpoint = query
    ? `${AUDITOR_BASE}/critical-gaps?${query}`
    : `${AUDITOR_BASE}/critical-gaps`;

  return apiRequest(endpoint, true);
}

/**
 * Get Auditor Controls Passing
 * @param {Object} [params] - Query parameters
 * @returns {Promise} Controls passing data
 */
export async function getAuditorControlsPassing(params) {
  const query = new URLSearchParams(params).toString();
  const endpoint = query
    ? `${AUDITOR_BASE}/controls-passing?${query}`
    : `${AUDITOR_BASE}/controls-passing`;

  return apiRequest(endpoint, true);
}

/**
 * Get Auditor Extra Controls
 * @param {Object} [params] - Query parameters
 * @returns {Promise} Extra controls data
 */
export async function getAuditorExtraControls(params) {
  const query = new URLSearchParams(params).toString();
  const endpoint = query
    ? `${AUDITOR_BASE}/extra-controls?${query}`
    : `${AUDITOR_BASE}/extra-controls`;

  return apiRequest(endpoint, true);
}

/**
 * Get Auditor Deployment Points
 * @param {Object} [params] - Query parameters
 * @returns {Promise} Deployment points detailed data
 */
export async function getAuditorDeploymentPoints(params) {
  const query = new URLSearchParams(params).toString();
  const endpoint = query
    ? `${AUDITOR_BASE}/deployment-points?${query}`
    : `${AUDITOR_BASE}/deployment-points`;

  return apiRequest(endpoint, true);
}

/**
 * Get Customer Dashboard Analytics
 * @param {Object} [params] - Query parameters (startDate, endDate, frameworkId, etc)
 * @returns {Promise} Dashboard analytics data
 */
export async function getCustomerAdminDashboardAnalytics(params) {
  const dateQuery = buildDateQuery(params);
  const frameworkQuery = buildFrameworkQuery(params?.frameworkId);

  let queryString = dateQuery;
  if (frameworkQuery) {
    queryString += queryString
      ? frameworkQuery.replace("?", "&")
      : frameworkQuery;
  }

  return apiRequest(`${CUSTOMER_BASE}/analytics${queryString}`, true);
}
