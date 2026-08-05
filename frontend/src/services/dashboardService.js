/**
 * Dashboard Service
 * Handles dashboard analytics API calls
 */

import { apiRequest } from "./apiService";

const ADMIN_BASE = "/dashboard/admin";
const EXPERT_BASE = "/dashboard/expert";
const CUSTOMER_BASE = "/dashboard/customer-admin";

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
    `${EXPERT_BASE}/analytics${buildDateQuery(dateRange)}`,
    true
  );
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
