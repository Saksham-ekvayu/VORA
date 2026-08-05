/* eslint-disable react/prop-types */

import { useState } from "react";
import Icon from "@/components/custom/Icon";
import FilePreviewModal from "@/components/custom/FilePreviewModal";

const FileTypeCard = ({
  fileType,
  fileSize,
  fileName,
  fileId,
  onDownload,
  serviceType,
  frameworkId,
  size = "md",
}) => {
  const getFileType = () => {
    // Direct mapping for uppercase types (most common case for initial documents)
    if (fileType && !fileType.includes("/")) {
      const upperType = fileType.toUpperCase();
      const typeMap = {
        PDF: "pdf",
        DOC: "doc",
        DOCX: "docx",
        XLS: "xls",
        XLSX: "xlsx",
        PPT: "ppt",
        PPTX: "pptx",
        TXT: "txt",
        CSV: "csv",
        ZIP: "zip",
        RAR: "rar",
      };
      if (typeMap[upperType]) {
        return typeMap[upperType];
      }
    }

    // Try to get extension from filename
    if (fileName) {
      const extension = fileName.split(".").pop()?.toLowerCase();
      if (extension && extension !== fileName) {
        return extension;
      }
    }

    // Handle MIME types
    if (fileType?.includes("/")) {
      const mimeToExt = {
        "application/pdf": "pdf",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
          "docx",
        "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
          "xlsx",
        "application/vnd.ms-powerpoint": "ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation":
          "pptx",
        "text/plain": "txt",
        "text/csv": "csv",
        "application/zip": "zip",
        "application/x-rar-compressed": "rar",
      };
      const extension = mimeToExt[fileType.toLowerCase()];
      if (extension) return extension;
    }

    return "pdf";
  };

  const getFileTypeConfig = (type) => {
    const configs = {
      pdf: {
        icon: "pdf",
        bgColor: "bg-red-50 dark:bg-red-900/20",
        textColor: "text-red-600 dark:text-red-400",
        borderColor: "border-red-200 dark:border-red-800",
        label: "PDF",
      },
      doc: {
        icon: "doc",
        bgColor: "bg-blue-50 dark:bg-blue-900/20",
        textColor: "text-blue-600 dark:text-blue-400",
        borderColor: "border-blue-200 dark:border-blue-800",
        label: "DOC",
      },
      docx: {
        icon: "doc",
        bgColor: "bg-blue-50 dark:bg-blue-900/20",
        textColor: "text-blue-600 dark:text-blue-400",
        borderColor: "border-blue-200 dark:border-blue-800",
        label: "DOCX",
      },
      xls: {
        icon: "excel",
        bgColor: "bg-green-50 dark:bg-green-900/20",
        textColor: "text-green-600 dark:text-green-400",
        borderColor: "border-green-200 dark:border-green-800",
        label: "XLS",
      },
      xlsx: {
        icon: "excel",
        bgColor: "bg-green-50 dark:bg-green-900/20",
        textColor: "text-green-600 dark:text-green-400",
        borderColor: "border-green-200 dark:border-green-800",
        label: "XLSX",
      },
      ppt: {
        icon: "ppt",
        bgColor: "bg-orange-50 dark:bg-orange-900/20",
        textColor: "text-orange-600 dark:text-orange-400",
        borderColor: "border-orange-200 dark:border-orange-800",
        label: "PPT",
      },
      pptx: {
        icon: "ppt",
        bgColor: "bg-orange-50 dark:bg-orange-900/20",
        textColor: "text-orange-600 dark:text-orange-400",
        borderColor: "border-orange-200 dark:border-orange-800",
        label: "PPTX",
      },
      txt: {
        icon: "document",
        bgColor: "bg-gray-50 dark:bg-gray-900/20",
        textColor: "text-gray-600 dark:text-gray-400",
        borderColor: "border-gray-200 dark:border-gray-800",
        label: "TXT",
      },
      zip: {
        icon: "zip",
        bgColor: "bg-purple-50 dark:bg-purple-900/20",
        textColor: "text-purple-600 dark:text-purple-400",
        borderColor: "border-purple-200 dark:border-purple-800",
        label: "ZIP",
      },
      rar: {
        icon: "zip",
        bgColor: "bg-purple-50 dark:bg-purple-900/20",
        textColor: "text-purple-600 dark:text-purple-400",
        borderColor: "border-purple-200 dark:border-purple-800",
        label: "RAR",
      },
      csv: {
        icon: "csv",
        bgColor: "bg-emerald-50 dark:bg-emerald-900/20",
        textColor: "text-emerald-600 dark:text-emerald-400",
        borderColor: "border-emerald-200 dark:border-emerald-800",
        label: "CSV",
      },
      default: {
        icon: "file",
        bgColor: "bg-gray-50 dark:bg-gray-900/20",
        textColor: "text-gray-600 dark:text-gray-400",
        borderColor: "border-gray-200 dark:border-gray-800",
        label: "FILE",
      },
    };

    return configs[type] || configs.default;
  };

  const getSizeConfig = (size) => {
    const sizes = {
      xs: {
        iconSize: "10px",
        iconContainer: "w-5 h-5",
        fileName: "text-xs",
        fileType: "text-[10px]",
        fileSize: "text-[10px]",
        gap: "gap-1",
      },
      sm: {
        iconSize: "12px",
        iconContainer: "w-6 h-6",
        fileName: "text-xs",
        fileType: "text-[10px]",
        fileSize: "text-[10px]",
        gap: "gap-1.5",
      },
      md: {
        iconSize: "14px",
        iconContainer: "w-8 h-8",
        fileName: "text-sm",
        fileType: "text-xs",
        fileSize: "text-xs",
        gap: "gap-2",
      },
      lg: {
        iconSize: "18px",
        iconContainer: "w-10 h-10",
        fileName: "text-base",
        fileType: "text-sm",
        fileSize: "text-sm",
        gap: "gap-2.5",
      },
      xl: {
        iconSize: "22px",
        iconContainer: "w-12 h-12",
        fileName: "text-lg",
        fileType: "text-sm",
        fileSize: "text-sm",
        gap: "gap-3",
      },
    };

    return sizes[size] || sizes.md;
  };

  const formatFileSize = (size) => {
    if (!size) return "—";
    if (typeof size === "string" && /[KMGT]B/i.test(size)) return size;
    const bytes = Number.parseInt(size);
    if (Number.isNaN(bytes)) return size || "—";
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (
      Number.parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i]
    );
  };

  const type = getFileType();
  const config = getFileTypeConfig(type);
  const sizeConfig = getSizeConfig(size);
  const formattedSize = formatFileSize(fileSize);
  const [previewOpen, setPreviewOpen] = useState(false);

  return (
    <>
      {/* min-w-0 is critical — without it, flex children won't shrink below their content size */}
      <div className={`flex items-center ${sizeConfig.gap} min-w-0 w-full`}>
        {/* Fixed-size icon — never shrinks */}
        <button
          type="button"
          className={`${sizeConfig.iconContainer} shrink-0 rounded ${config.bgColor} ${config.borderColor} border flex items-center justify-center ${config.textColor} ${fileId ? "cursor-pointer hover:opacity-80 transition-opacity" : ""}`}
          onClick={(e) => {
            if (fileId) {
              e.stopPropagation();
              setPreviewOpen(true);
            }
          }}
          title={fileId ? "Click to preview" : undefined}
          aria-label={fileId ? "Preview file" : undefined}
        >
          <Icon name={config.icon} size={sizeConfig.iconSize} />
        </button>

        {/* Text block — grows to fill all remaining space, truncates filename */}
        <div className="flex flex-col min-w-0 flex-1">
          {fileName && (
            <button
              type="button"
              onClick={(e) => {
                if (fileId) {
                  e.stopPropagation();
                  setPreviewOpen(true);
                }
              }}
              className={`${sizeConfig.fileName} text-foreground font-medium truncate w-full text-left ${fileId ? "cursor-pointer hover:underline" : ""}`}
              title={fileName}
              aria-label={fileId ? `Preview ${fileName}` : fileName}
            >
              {fileName}
            </button>
          )}
          <div className="flex items-center gap-1">
            <span
              className={`${sizeConfig.fileType} font-medium ${config.textColor} uppercase shrink-0`}
            >
              {config.label}
            </span>
            <span
              className={`${sizeConfig.fileSize} text-muted-foreground whitespace-nowrap shrink-0`}
            >
              {formattedSize}
            </span>
          </div>
        </div>
      </div>

      {fileId && (
        <FilePreviewModal
          fileId={fileId}
          fileName={fileName}
          open={previewOpen}
          onClose={() => setPreviewOpen(false)}
          onDownload={onDownload}
          serviceType={serviceType}
          frameworkId={frameworkId}
        />
      )}
    </>
  );
};

export default FileTypeCard;
