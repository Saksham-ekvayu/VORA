/* eslint-disable react/prop-types */

const normalizeFileType = (mimeType, fileName) => {
  const allowed = new Set(["pdf", "doc", "docx"]);
  const normalizedMime = String(mimeType || "")
    .toLowerCase()
    .trim();
  const extension = String(fileName || "")
    .split(".")
    .pop()
    .toLowerCase();

  const mimeMap = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
      "docx",
  };

  const suffixMap = {
    "vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    msword: "doc",
    "officedocument.wordprocessingml.document": "docx",
  };

  if (allowed.has(normalizedMime)) return normalizedMime;
  if (mimeMap[normalizedMime]) return mimeMap[normalizedMime];

  const suffix = normalizedMime.replace(/^.*\//, "");
  if (suffixMap[suffix]) return suffixMap[suffix];
  if (allowed.has(suffix)) return suffix;
  if (allowed.has(extension)) return extension;
  return "pdf";
};

export { normalizeFileType };
