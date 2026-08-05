/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";

function FileIcon({ type }) {
  const configs = {
    pdf: {
      icon: "pdf",
      bgColor: "bg-red-50 dark:bg-red-900/20",
      textColor: "text-red-600 dark:text-red-400",
      borderColor: "border-red-200 dark:border-red-800",
    },
    doc: {
      icon: "doc",
      bgColor: "bg-blue-50 dark:bg-blue-900/20",
      textColor: "text-blue-600 dark:text-blue-400",
      borderColor: "border-blue-200 dark:border-blue-800",
    },
    docx: {
      icon: "doc",
      bgColor: "bg-blue-50 dark:bg-blue-900/20",
      textColor: "text-blue-600 dark:text-blue-400",
      borderColor: "border-blue-200 dark:border-blue-800",
    },
    xls: {
      icon: "excel",
      bgColor: "bg-green-50 dark:bg-green-900/20",
      textColor: "text-green-600 dark:text-green-400",
      borderColor: "border-green-200 dark:border-green-800",
    },
    xlsx: {
      icon: "excel",
      bgColor: "bg-green-50 dark:bg-green-900/20",
      textColor: "text-green-600 dark:text-green-400",
      borderColor: "border-green-200 dark:border-green-800",
    },
    ppt: {
      icon: "ppt",
      bgColor: "bg-orange-50 dark:bg-orange-900/20",
      textColor: "text-orange-600 dark:text-orange-400",
      borderColor: "border-orange-200 dark:border-orange-800",
    },
    pptx: {
      icon: "ppt",
      bgColor: "bg-orange-50 dark:bg-orange-900/20",
      textColor: "text-orange-600 dark:text-orange-400",
      borderColor: "border-orange-200 dark:border-orange-800",
    },
    default: {
      icon: "file",
      bgColor: "bg-gray-50 dark:bg-gray-900/20",
      textColor: "text-gray-600 dark:text-gray-400",
      borderColor: "border-gray-200 dark:border-gray-800",
    },
  };

  const fileType = type?.toLowerCase() || "pdf";
  const config = configs[fileType] || configs.default;

  return (
    <span
      className={`inline-flex items-center justify-center w-6 h-6 rounded ${config.bgColor} border ${config.borderColor} ${config.textColor}`}
    >
      <Icon name={config.icon} size="13px" />
    </span>
  );
}

export default FileIcon;
