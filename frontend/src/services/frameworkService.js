import { apiRequest } from "./apiService";

const FRAMEWORK_BASE = "/framework";
const DASHBOARD_BASE = "/dashboard";

/**
 * Get expert dashboard analytics from framework-service
 * @param {{ startDate?: string, endDate?: string }} [dateRange]
 */
export function getExpertDashboardAnalytics(dateRange) {
  const params = new URLSearchParams();
  if (dateRange?.startDate) params.set("startDate", dateRange.startDate);
  if (dateRange?.endDate) params.set("endDate", dateRange.endDate);
  const queryString = params.toString() ? `?${params.toString()}` : "";

  return apiRequest(`${DASHBOARD_BASE}/expert/analytics${queryString}`, true);
}

/**
 * Get framework by ID
 */
export function getFrameworkById(id, params = {}) {
  const query = new URLSearchParams(params).toString();
  const queryString = query ? `?${query}` : "";
  return apiRequest(`${FRAMEWORK_BASE}/${id}${queryString}`, true);
}

/**
 * Get all frameworks
 */
export function getAllFrameworks({
  page = 1,
  limit = 10,
  search = "",
  aiStatus = "",
  approvalStatus = "",
  sortBy = "",
  sortOrder = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(aiStatus && { aiStatus }),
    ...(approvalStatus && { approvalStatus }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
  });

  return apiRequest(
    `${FRAMEWORK_BASE}/all-frameworks?${params.toString()}`,
    true
  );
}

/**
 * Get available frameworks category
 */
export function getFrameworkCategory({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "",
  sortOrder = "",
  isActive = "",
  accessStatus = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
    ...(isActive && { isActive }),
    ...(accessStatus && { accessStatus }),
  });

  return apiRequest(
    `${FRAMEWORK_BASE}/categories/available?${params.toString()}`,
    true
  );
}

/**
 * Get existing frameworks to check used categories
 */
export function getExistingFrameworks({
  page = 1,
  limit = 100, // Get more records to check all used categories
  search = "",
  sortBy = "",
  sortOrder = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
  });

  return apiRequest(
    `${FRAMEWORK_BASE}/all-frameworks?${params.toString()}`,
    true
  );
}

/**
 * Upload framework file
 */
export function uploadFramework(formData) {
  return apiRequest(
    `${FRAMEWORK_BASE}/upload`, // Correct API gateway route
    {
      method: "POST",
      body: formData, // FormData object
    },
    true
  );
}

/**
 * Extract framework file by ai
 */
export function extractFramework(frameworkId, fileId) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/files/${fileId}/ai-extract`,
    {
      method: "POST",
    },
    true
  );
}

/**
 * Download framework file
 */
export async function downloadFrameworkFile(frameworkId, fileId, fileName) {
  const blob = await apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/files/${fileId}/download`,
    {
      method: "GET",
      responseType: "blob", // 🔥 important
    },
    true
  );

  const url = globalThis.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName || "framework";
  document.body.appendChild(a);
  a.click();
  a.remove();
  globalThis.URL.revokeObjectURL(url);
}

/**
 * Download framework report PDF from backend
 */
export async function downloadFrameworkReportPdf(frameworkId, fileName) {
  const blob = await apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/download-report`,
    {
      method: "GET",
      responseType: "blob",
    },
    true
  );

  const url = globalThis.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName || "framework_report.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  globalThis.URL.revokeObjectURL(url);
}

/**
 * Update framework file
 */
export function updateFramework(frameworkId, formData) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}`, // Correct API gateway route
    {
      method: "PUT",
      body: formData, // FormData object
    },
    true
  );
}

/**
 * Delete framework
 */
export function deleteFramework(frameworkId) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}`, // Correct API gateway route
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Delete a specific file version
 */
export function deleteFrameworkVersion(frameworkId, versionFileId) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/files/${versionFileId}`, // Correct route for file deletion
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Approve framework
 */
export function approveFramework(frameworkId) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/approve`,
    {
      method: "POST",
    },
    true
  );
}

/**
 * Reject framework
 */
export function rejectFramework(frameworkId, rejectionReason) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/reject`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ rejectionReason }),
    },
    true
  );
}

/**
 * Add a new control to an existing or new section in a file version
 * POST /:id/file-versions/:fileVersion/controls
 * Payload (controlData) can contain either sectionId or newSection, along with name, description, and deployment_points.
 */
export function addFrameworkControl(frameworkId, fileVersion, controlData) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/file-versions/${fileVersion}/controls`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(controlData),
    },
    true
  );
}

/**
 * Update a control in a file version
 * PATCH /:id/file-versions/:fileVersion/controls/:controlId
 */
export function updateFrameworkControl(
  frameworkId,
  fileVersion,
  controlId,
  controlData
) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/file-versions/${fileVersion}/controls/${controlId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(controlData),
    },
    true
  );
}

/**
 * Update a control's weightage in a file version
 * PATCH /:id/file-versions/:fileVersion/controls/:controlId/weightage
 */
export function updateFrameworkControlWeightage(
  frameworkId,
  fileVersion,
  controlId,
  weightage
) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/file-versions/${fileVersion}/controls/${controlId}/weightage`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ weightage }),
    },
    true
  );
}

/**
 * Delete a control from a file version
 * DELETE /:id/file-versions/:fileVersion/controls/:controlId
 */
export function deleteFrameworkControl(frameworkId, fileVersion, controlId) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/file-versions/${fileVersion}/controls/${controlId}`,
    { method: "DELETE" },
    true
  );
}

// ========================================
// DEPLOYMENT USER APIS (Approved Frameworks Only)
// ========================================

/**
 * Get all approved frameworks for customer users
 */
export function getApprovedFrameworks({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "",
  sortOrder = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
  });

  return apiRequest(
    `${FRAMEWORK_BASE}/approved-frameworks?${params.toString()}`,
    true
  );
}

/**
 * Get approved framework by ID for customer users
 */
export function getApprovedFrameworkById(id) {
  return apiRequest(`${FRAMEWORK_BASE}/approved-frameworks/${id}`, true);
}

export default {
  getExpertDashboardAnalytics,
  uploadFramework,
  updateFramework,
  downloadFrameworkFile,
  downloadFrameworkReportPdf,
  deleteFramework,
  deleteFrameworkVersion,
  approveFramework,
  rejectFramework,
  addFrameworkControl,
  deleteFrameworkControl,
  updateFrameworkControl,
  updateFrameworkControlWeightage,
  getApprovedFrameworks,
  getApprovedFrameworkById,
};
