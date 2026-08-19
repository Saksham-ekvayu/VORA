/**
 * Generate framework version prefix based on category code
 */
export const generateFrameworkVersionPrefix = (categoryCode) => {
  if (!categoryCode) return "";

  const codeMap = {
    iso27001: "ISO27001:",
    iso9001: "ISO9001:",
    iso14001: "ISO14001:",
    iso45001: "ISO45001:",
    iso20000: "ISO20000:",
    iso22301: "ISO22301:",
    nist: "NISTCSF:",
    sox: "SOX:",
    pci: "PCIDSS:",
    hipaa: "HIPAA:",
    gdpr: "GDPR:",
    cobit: "COBIT:",
    itil: "ITIL:",
  };

  return (
    codeMap[categoryCode.toLowerCase()] || `${categoryCode.toUpperCase()}:`
  );
};

/**
 * Validate framework version format - must have prefix and year
 */
export const validateFrameworkVersion = (version, categoryCode) => {
  if (!version?.trim()) {
    return { isValid: false, message: "Framework version is required" };
  }

  const expectedPrefix = generateFrameworkVersionPrefix(categoryCode);

  if (expectedPrefix && !version.startsWith(expectedPrefix)) {
    return {
      isValid: false,
      message: `Version should start with "${expectedPrefix}"`,
    };
  }

  // Check if there's content after the prefix
  const versionContent = version.replace(expectedPrefix, "").trim();
  if (!versionContent) {
    return {
      isValid: false,
      message: "Please add year after the prefix (e.g., 2022, 2023)",
    };
  }

  // Check if version contains a valid year (4 digits between 1900-2100)
  const yearMatch = versionContent.match(/\b(19|20|21)\d{2}\b/);
  if (!yearMatch) {
    return {
      isValid: false,
      message: "Version must contain a valid year (e.g., 2020, 2022, 2023)",
    };
  }

  return { isValid: true, message: "" };
};

/**
 * Allowed file types for framework uploads
 */
export const ALLOWED_FRAMEWORK_FILE_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

/**
 * Validate framework file type and size
 */
export const validateFrameworkFile = (file, handleError) => {
  if (!file) return false;

  if (!ALLOWED_FRAMEWORK_FILE_TYPES.includes(file.type)) {
    handleError(
      new Error("File type not supported"),
      "File type not supported. Please upload PDF, DOC, DOCX files."
    );
    return false;
  }

  if (file.size > 50 * 1024 * 1024) {
    handleError(
      new Error("File size exceeded"),
      "File size must be less than 50MB"
    );
    return false;
  }

  return true;
};

/**
 * Allowed file types for deployment document uploads
 */
export const ALLOWED_DEPLOYMENT_DOCUMENT_FILE_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

/**
 * Validate deployment document file type and size
 */
export const validateDeploymentDocumentFile = (file, toast) => {
  if (!file) return false;

  if (!ALLOWED_DEPLOYMENT_DOCUMENT_FILE_TYPES.includes(file.type)) {
    toast.error(
      "File type not supported. Please upload PDF, DOC, or DOCX files."
    );
    return false;
  }

  if (file.size > 50 * 1024 * 1024) {
    toast.error("File size must be less than 50MB");
    return false;
  }

  return true;
};

/**
 * Validate a single file for deployment framework upload
 */
export const validateDeploymentFrameworkFile = (file, toast) => {
  if (!file) return false;

  if (!ALLOWED_FRAMEWORK_FILE_TYPES.includes(file.type)) {
    toast.error(
      `File type not supported for ${file.name}. Please upload PDF, DOC, or DOCX files.`
    );
    return false;
  }

  if (file.size > 50 * 1024 * 1024) {
    toast.error(`File size must be less than 50MB for ${file.name}`);
    return false;
  }

  return true;
};
