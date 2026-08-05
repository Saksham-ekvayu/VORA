/* eslint-disable react/prop-types */

import { normalizeFileType } from "./normalizeFileType";
import { updateDeploymentFramework } from "@/services/deploymentFrameworkService";
import { toast } from "sonner";

// File handling helpers
export const createDocumentFromFile = (file, index = 0) => ({
  id: `doc-${Date.now()}-${index}`,
  name: file.name,
  size: file.size,
  type: normalizeFileType(file.type, file.name),
  fileVersion: "1.0.0",
  aiExtraction: null,
  file: file,
  action: "add",
});

export const createReplicatedDocument = (doc) => ({
  id: doc.fileId,
  fileId: doc.fileId,
  name: doc.originalFileName,
  size: doc.fileSize,
  type: doc.fileType,
  fileVersion: doc.fileVersion,
  aiExtraction: doc.aiExtraction,
  replicated: true,
  original: true,
  action: "replicate",
  fileUrl: doc.fileUrl,
  uploadedAt: doc.uploadedAt,
});

// API submission helpers
export const buildDocumentOperations = (documents, patchType) => {
  if (patchType === "minor") {
    return documents.map((doc) => ({
      action: doc.action || (doc.replicated ? "replicate" : "add"),
      fileId: doc.fileId,
      originalFileName: doc.name,
      fileSize: doc.size,
      fileType: doc.type,
      fileVersion: doc.fileVersion,
      replicated: doc.replicated || false,
    }));
  }

  // Major patch - all are new
  return documents.map((doc) => ({
    action: "add",
    originalFileName: doc.name,
    fileSize: doc.size,
    fileType: doc.type,
    fileVersion: "1.0.0",
    replicated: false,
  }));
};

export const buildMetadata = (
  framework,
  patchType,
  documentOperations,
  removedDocuments = []
) => {
  return {
    patchType,
    frameworkName: framework.frameworkName,
    frameworkCode: framework.frameworkCode,
    frameworkVersion: framework.frameworkVersion,
    frameworkId: framework.frameworkId,
    documents: [...documentOperations, ...removedDocuments],
  };
};

export const createFormData = (documents, metadata) => {
  const formData = new FormData();

  // Add new files to FormData
  const newFiles = documents.filter((doc) => doc.file);
  newFiles.forEach((doc) => {
    formData.append("files", doc.file);
  });

  // Add metadata
  formData.append("metadata", JSON.stringify(metadata));

  return formData;
};

export const getNextVersion = (currentVersion, patchType) => {
  if (!currentVersion) return "1.0.0";

  const [major, minor, patch] = currentVersion.split(".").map(Number);

  if (patchType === "major") {
    return `${major + 1}.0.0`;
  }

  // For minor patches: if patch reaches 9, increment minor version and reset patch to 0
  if (patch >= 9) {
    const nextMinor = minor + 1;
    return `${major}.${nextMinor}.0`;
  } else {
    // Otherwise increment patch number
    const nextPatch = patch + 1;
    return `${major}.${minor}.${nextPatch}`;
  }
};

export const submitPatch = async (
  framework,
  documents,
  patchType,
  onSuccess,
  onClose,
  removedDocuments = []
) => {
  try {
    const documentOperations = buildDocumentOperations(documents, patchType);
    const removedOps = removedDocuments.map((doc) => ({
      action: "remove",
      fileId: doc.fileId || doc.id,
      originalFileName: doc.name,
    }));

    const metadata = buildMetadata(
      framework,
      patchType,
      documentOperations,
      removedOps
    );
    const formData = createFormData(documents, metadata);

    const response = await updateDeploymentFramework(framework.id, formData);

    if (response.success) {
      toast.success(response.message);
      onClose();
      onSuccess();
    } else {
      toast.error(response.message || `Failed to create ${patchType} patch`);
    }
  } catch (error) {
    toast.error(error.message || `Failed to create ${patchType} patch`);
  }
};
