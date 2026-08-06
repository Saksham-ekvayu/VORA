import { apiRequest } from "./apiService";

const ASSIGNMENT_BASE = "/assignment-frameworks";
const FRAMEWORK_BASE = "/deployment-frameworks";

/**
 * Get frameworks assigned to the customer by admin
 */
export function getAssignmentFrameworks({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "createdAt",
  sortOrder = "desc",
  assignmentStatus = "",
  finalizationStatus = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
    ...(assignmentStatus && { assignmentStatus }),
    ...(finalizationStatus && { finalizationStatus }),
  });

  return apiRequest(
    `${ASSIGNMENT_BASE}/assignments?${params.toString()}`,
    true
  );
}

/**
 * Get framework by ID
 */
export function getAssignedFrameworksById(id) {
  return apiRequest(`${ASSIGNMENT_BASE}/assignments/${id}`, true);
}

export async function downloadAssignedFrameworkReport(
  id,
  fileVersion,
  fileName
) {
  const query = fileVersion
    ? `?${new URLSearchParams({ fileVersion }).toString()}`
    : "";
  const blob = await apiRequest(
    `${ASSIGNMENT_BASE}/assignments/${id}/report${query}`,
    { method: "GET", responseType: "blob" },
    true
  );

  const url = globalThis.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download =
    fileName || `assigned_framework_${fileVersion || "current"}_report.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  globalThis.URL.revokeObjectURL(url);
}

/**
 * Get deployment framework by ID
 */
export function getDeploymentFrameworkById(id, params = {}) {
  const query = new URLSearchParams(params).toString();
  const queryString = query ? `?${query}` : "";
  return apiRequest(`${FRAMEWORK_BASE}/${id}${queryString}`, true);
}

/**
 * Get deployment framework package by version
 */
export function getDeploymentFrameworkPackageByVersion(id, packageVersion) {
  return apiRequest(`${FRAMEWORK_BASE}/${id}/packages/${packageVersion}`, true);
}

/**
 * Get all deployment frameworks
 */
export function getAllDeploymentFrameworks({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "createdAt",
  sortOrder = "desc",
  aiExtractionStatus = "",
  requestReviewStatus = "",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
    ...(aiExtractionStatus && { aiExtractionStatus }),
    ...(requestReviewStatus && { requestReviewStatus }),
  });

  return apiRequest(`${FRAMEWORK_BASE}/?${params.toString()}`, true);
}

/**
 * Get client controls for all approved deployment frameworks
 */
export function getDeploymentFrameworkClientControls() {
  return apiRequest(`${FRAMEWORK_BASE}/client-controls`, true);
}

/**
 * Update a single deployment point path
 */
export function updateDeploymentPointPath(frameworkId, data) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/deployment-points`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Upload deployment framework file
 */
export function uploadDeploymentFramework(formData) {
  return apiRequest(
    `${FRAMEWORK_BASE}/upload`,
    {
      method: "POST",
      body: formData, // FormData object
    },
    true
  );
}

/**
 * Upload deployment framework file to ai
 */
export function extractDeploymentFramework(
  frameworkId,
  packageVersion,
  fileId
) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}/files/${fileId}/ai-upload`,
    {
      method: "POST",
    },
    true
  );
}

/**
 * Download deployment framework file
 */
export async function downloadDeploymentFrameworkFile(
  frameworkId,
  fileId,
  fileName
) {
  const blob = await apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/files/${fileId}/download`,
    {
      method: "GET",
      responseType: "blob",
    },
    true
  );

  // Trigger browser download
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
 * Update deployment framework (supports both metadata updates and file uploads)
 */
export function updateDeploymentFramework(frameworkId, data) {
  // If data is FormData (file upload), use multipart content type
  if (data instanceof FormData) {
    return apiRequest(
      `${FRAMEWORK_BASE}/${frameworkId}`,
      {
        method: "PUT",
        body: data, // FormData object
      },
      true
    );
  }

  // If data is plain object (metadata update), use JSON
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Delete deployment framework
 */
export function deleteDeploymentFramework(frameworkId) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}`,
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Delete a specific package
 */
export function deleteDeploymentFrameworkPackage(frameworkId, packageVersion) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}`,
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Download deployment framework package report
 */
export async function downloadDeploymentFrameworkReport(
  frameworkId,
  packageVersion,
  fileName
) {
  const blob = await apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}/report`,
    {
      method: "GET",
      responseType: "blob",
    },
    true
  );

  // Trigger browser download
  const url = globalThis.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName || `${frameworkId}_${packageVersion}_report.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  globalThis.URL.revokeObjectURL(url);
}

/**
 * Run full deployment analysis (comparison + gap analysis)
 */
export function runAnalysis(deploymentFrameworkId, packageVersion) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${deploymentFrameworkId}/packages/${packageVersion}/run-analysis`,
    {
      method: "POST",
    },
    true
  );
}

/**
 * Request expert review for deployment framework
 */
export function requestExpertReview(frameworkId, data) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/request-review`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Review specific deployment points directly
 */
export function reviewDeploymentPoints(frameworkId, data) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/reviews/points`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Complete framework review
 */
export function completeDeploymentFrameworkReview(id, data = {}) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${id}/complete-review`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Update deployment framework control
 */
export function updateAssignmentFrameworkControl(
  id,
  fileVersion,
  controlId,
  data
) {
  return apiRequest(
    `${ASSIGNMENT_BASE}/${id}/file-versions/${fileVersion}/controls/${controlId}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Delete deployment framework control
 */
export function deleteAssignmentFrameworkControl(id, fileVersion, controlId) {
  return apiRequest(
    `${ASSIGNMENT_BASE}/${id}/file-versions/${fileVersion}/controls/${controlId}`,
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Add deployment framework control
 */
export function addAssignmentFrameworkControl(id, fileVersion, data) {
  return apiRequest(
    `${ASSIGNMENT_BASE}/${id}/file-versions/${fileVersion}/controls`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Update control applicability for one or multiple controls
 */
export function updateAssignmentFrameworkControlApplicability(
  id,
  fileVersion,
  controlIds,
  isApplicable
) {
  return apiRequest(
    `${ASSIGNMENT_BASE}/${id}/file-versions/${fileVersion}/controls/applicability`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ controlIds, is_applicable: isApplicable }),
    },
    true
  );
}

/**
 * Update control weightage in a file version
 */
export function updateAssignmentFrameworkControlWeightage(
  id,
  fileVersion,
  controlId,
  weightage
) {
  return apiRequest(
    `${ASSIGNMENT_BASE}/${id}/file-versions/${fileVersion}/controls/${controlId}/weightage`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ weightage }),
    },
    true
  );
}

export function finalizeAssignmentFramework(id) {
  return apiRequest(
    `${ASSIGNMENT_BASE}/${id}/finalize`,
    {
      method: "PATCH",
    },
    true
  );
}

/**
 * Internal-expert approves or returns a deployment package
 */
export function reviewDeploymentPackage(frameworkId, packageVersion, data) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}/review`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    },
    true
  );
}

export function addReviewRemark(id, packageVersion, data) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${id}/packegeVersion/${packageVersion}/add-comparison-review-remark`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Add review remark for a point gap in a package gap analysis
 */
export function addGapReviewRemark(id, packageVersion, data) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${id}/packegeVersion/${packageVersion}/add-gap-review-remark`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
    true
  );
}

export default {
  getAssignmentFrameworks,
  getAssignedFrameworksById,
  downloadAssignedFrameworkReport,
  getDeploymentFrameworkById,
  getDeploymentFrameworkPackageByVersion,
  getAllDeploymentFrameworks,
  getDeploymentFrameworkClientControls,
  updateDeploymentPointPath,
  uploadDeploymentFramework,
  updateDeploymentFramework,
  downloadDeploymentFrameworkFile,
  deleteDeploymentFramework,
  deleteDeploymentFrameworkPackage,
  extractDeploymentFramework,
  runAnalysis,
  downloadDeploymentFrameworkReport,
  requestExpertReview,
  reviewDeploymentPoints,
  completeDeploymentFrameworkReview,
  updateAssignmentFrameworkControl,
  deleteAssignmentFrameworkControl,
  addAssignmentFrameworkControl,
  updateAssignmentFrameworkControlApplicability,
  updateAssignmentFrameworkControlWeightage,
  finalizeAssignmentFramework,
  addReviewRemark,
  addGapReviewRemark,
  reviewDeploymentPackage,
};
