import { apiRequest } from "./apiService";

const BASE_PATH = "/deployment-documents";

/**
 * Get deployment document by ID
 */
export function getDeploymentDocumentById(id) {
  return apiRequest(`${BASE_PATH}/${id}`, true);
}

/**
 * Get all deployment documents
 */
export function getAllDeploymentDocuments({
  page = 1,
  limit = 10,
  search = "",
  sortBy = "createdAt",
  sortOrder = "desc",
} = {}) {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    ...(search && { search }),
    ...(sortBy && { sortBy }),
    ...(sortOrder && { sortOrder }),
  });

  return apiRequest(`${BASE_PATH}?${params.toString()}`, true);
}

/**
 * Upload deployment document file
 */
export function uploadDeploymentDocument(formData) {
  return apiRequest(
    `${BASE_PATH}/upload`,
    {
      method: "POST",
      body: formData, // FormData object
    },
    true
  );
}

/**
 * Get all files for a document
 */
export function getDocumentFiles(documentId) {
  return apiRequest(`${BASE_PATH}/${documentId}/files`, true);
}

/**
 * Get specific document file by ID
 */
export function getDocumentFileById(documentId, fileId) {
  return apiRequest(`${BASE_PATH}/${documentId}/files/${fileId}`, true);
}

/**
 * Download deployment document file
 */
export async function downloadDeploymentDocumentFile(
  documentId,
  fileId,
  fileName
) {
  const blob = await apiRequest(
    `${BASE_PATH}/${documentId}/files/${fileId}/download`,
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
  a.download = fileName || "document";
  document.body.appendChild(a);
  a.click();
  a.remove();
  globalThis.URL.revokeObjectURL(url);
}

/**
 * Preview deployment document file
 */
export function previewDeploymentDocumentFile(documentId, fileId) {
  return apiRequest(`${BASE_PATH}/${documentId}/files/${fileId}/preview`, true);
}

/**
 * Delete a specific file version
 */
export function deleteDeploymentDocumentVersion(documentId, fileId) {
  return apiRequest(
    `${BASE_PATH}/${documentId}/files/${fileId}`,
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Upload deployment document file to ai
 */
export function uploadDeploymentDocumentToAi(documentId, fileId) {
  return apiRequest(
    `${BASE_PATH}/${documentId}/files/${fileId}/ai-upload`,
    {
      method: "POST",
    },
    true
  );
}

/**
 * Delete deployment document (entire record)
 */
export function deleteDeploymentDocument(id) {
  return apiRequest(
    `${BASE_PATH}/${id}`,
    {
      method: "DELETE",
    },
    true
  );
}

/**
 * Update deployment document (supports both metadata updates and file uploads)
 */
export function updateDeploymentDocument(documentId, data) {
  // If data is FormData (file upload for new version), use the upload route
  if (data instanceof FormData) {
    // Ensure documentId is in the FormData
    if (!data.has("documentId")) {
      data.append("documentId", documentId);
    }
    return apiRequest(
      `${BASE_PATH}/upload`,
      {
        method: "POST",
        body: data,
      },
      true
    );
  }

  // If data is plain object (metadata update), use PUT /:id
  return apiRequest(
    `${BASE_PATH}/${documentId}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    },
    true
  );
}

export default {
  getDeploymentDocumentById,
  getAllDeploymentDocuments,
  uploadDeploymentDocument,
  updateDeploymentDocument,
  getDocumentFiles,
  getDocumentFileById,
  downloadDeploymentDocumentFile,
  previewDeploymentDocumentFile,
  deleteDeploymentDocument,
  deleteDeploymentDocumentVersion,
  uploadDeploymentDocumentToAi,
};
