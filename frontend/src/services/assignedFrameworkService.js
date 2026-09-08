import { apiRequest } from "./apiService";

const ASSIGNMENT_BASE = "/assignment-frameworks";

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
    `${ASSIGNMENT_BASE}/assignments/${id}/finalize`,
    {
      method: "PATCH",
    },
    true
  );
}

export default {
  getAssignmentFrameworks,
  getAssignedFrameworksById,
  downloadAssignedFrameworkReport,
  updateAssignmentFrameworkControl,
  deleteAssignmentFrameworkControl,
  addAssignmentFrameworkControl,
  updateAssignmentFrameworkControlApplicability,
  updateAssignmentFrameworkControlWeightage,
  finalizeAssignmentFramework,
};
