import { apiRequest } from "./apiService";
const FRAMEWORK_BASE = "/deployment-frameworks";
const EXTRACTION_BASE = "/extract";

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
 * Bulk update deployment points path and source
 * @param {string} frameworkId
 * @param {Object} payload
 * @returns {Promise}
 */
export async function bulkUpdateDeploymentPointPaths(frameworkId, payload) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/bulk-update-points`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
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
    `${EXTRACTION_BASE}/deployment-framework/${frameworkId}/packages/${packageVersion}/files/${fileId}/ai-extract`,
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
 * Run comparison analysis
 */
export async function runComparison(deploymentFrameworkId, packageVersion) {
  const payload = {
    deployment_framework_id: deploymentFrameworkId,
    package_version: packageVersion,
  };

  await apiRequest(
    "/comparison/start",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    true
  );

  return {
    success: true,
    message: "Comparison Analysis started successfully",
  };
}

/**
 * Run gap analysis
 */
export async function runGapAnalysis(deploymentFrameworkId, packageVersion) {
  const payload = {
    deployment_framework_id: deploymentFrameworkId,
    package_version: packageVersion,
  };

  await apiRequest(
    "/deployment-gap/start",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    true
  );

  return {
    success: true,
    message: "Gap Analysis started successfully",
  };
}

/**
 * Run full deployment analysis (comparison + gap analysis)
 */
export async function runAnalysis(deploymentFrameworkId, packageVersion) {
  await Promise.all([
    runComparison(deploymentFrameworkId, packageVersion),
    runGapAnalysis(deploymentFrameworkId, packageVersion),
  ]);

  return {
    success: true,
    message: "Comparison and Gap Analysis started successfully",
  };
}

/**
 * Merge controls for deployment framework package
 */
export function mergeDeploymentFrameworkControls(
  deploymentFrameworkId,
  packageVersion
) {
  return apiRequest(
    `${EXTRACTION_BASE}/deployment-framework/${deploymentFrameworkId}/packages/${packageVersion}/merge`,
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

/**
 * Deploy an approved deployment package
 */
export function deployDeploymentPackage(frameworkId, packageVersion) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}/deploy`,
    {
      method: "PATCH",
    },
    true
  );
}

/**
 * Add document control
 */
export function addDocumentControl(frameworkId, packageVersion, fileId, data) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}/files/${fileId}/controls`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Update document control
 */
export function updateDocumentControl(
  frameworkId,
  packageVersion,
  fileId,
  controlId,
  data
) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}/files/${fileId}/controls/${controlId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
    true
  );
}

/**
 * Delete document control
 */
export function deleteDocumentControl(
  frameworkId,
  packageVersion,
  fileId,
  controlId
) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}/files/${fileId}/controls/${controlId}`,
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Update deployment framework section
 */
export function updateDeploymentFrameworkSection(
  frameworkId,
  packageVersion,
  sectionId,
  data
) {
  return apiRequest(
    `${FRAMEWORK_BASE}/${frameworkId}/packages/${packageVersion}/sections/${sectionId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
    true
  );
}

export default {
  getDeploymentFrameworkById,
  getDeploymentFrameworkPackageByVersion,
  getAllDeploymentFrameworks,
  getDeploymentFrameworkClientControls,
  updateDeploymentPointPath,
  bulkUpdateDeploymentPointPaths,
  uploadDeploymentFramework,
  updateDeploymentFramework,
  downloadDeploymentFrameworkFile,
  deleteDeploymentFramework,
  deleteDeploymentFrameworkPackage,
  extractDeploymentFramework,
  runComparison,
  runGapAnalysis,
  runAnalysis,
  downloadDeploymentFrameworkReport,
  mergeDeploymentFrameworkControls,
  requestExpertReview,
  reviewDeploymentPoints,
  completeDeploymentFrameworkReview,

  addReviewRemark,
  addGapReviewRemark,
  reviewDeploymentPackage,
  deployDeploymentPackage,
  addDocumentControl,
  updateDocumentControl,
  deleteDocumentControl,
  updateDeploymentFrameworkSection,
};
