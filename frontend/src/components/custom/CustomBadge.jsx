/* eslint-disable react/prop-types */

import {
  getRoleLabel,
  ROLE_ADMIN,
  ROLE_EXPERT,
  ROLE_INTERNAL_EXPERT,
  ROLE_CUSTOMER_ADMIN,
  ROLE_USER,
  ROLE_AUDITOR,
  capitalizeFirst,
} from "@/utils/commonUtils";

const ROLE_COLOR = {
  [ROLE_ADMIN]: "red",
  [ROLE_EXPERT]: "blue",
  [ROLE_INTERNAL_EXPERT]: "blue",
  [ROLE_CUSTOMER_ADMIN]: "green",
  [ROLE_USER]: "yellow",
  [ROLE_AUDITOR]: "purple",
};

const STATUS_COLOR = {
  pending: "amber",
  "in review": "purple",
  approved: "green",
  returned: "red",
  rejected: "red",
  uploaded: "purple",
  failed: "red",
  processing: "blue",
  extracted: "green",
  assigned: "green",
  revoked: "red",
  finalized: "green",
  requested: "amber",
  completed: "green",
  connected: "green",
  started: "blue",
  running: "blue",
  done: "green",
  locked: "gray",
  implemented: "green",
  "partially implemented": "amber",
  "not implemented": "red",
  active: "green",
  inactive: "red",
  passing: "primary",
  failing: "destructive",
  warning: "yellow",
  "not evaluated": "gray",
  "on track": "emerald",
  "needs attention": "yellow",
  "at risk": "red",
  "review due": "yellow",
  deprecated: "red",
  online: "emerald",
  offline: "red",
  degraded: "yellow",
  "not finalized": "yellow",
  "not finalize": "yellow",
};

const SEVERITY_COLOR = {
  critical: "purple",
  high: "red",
  medium: "yellow",
  low: "emerald",
  info: "blue",
};

const COLOR_VARIANTS = {
  primary: {
    bg: "bg-primary/10",
    text: "text-primary",
    border: "border-primary/20",
    dot: "bg-primary",
  },
  destructive: {
    bg: "bg-destructive/10",
    text: "text-destructive",
    border: "border-destructive/20",
    dot: "bg-destructive",
  },
  red: {
    bg: "bg-red-50 dark:bg-red-500/10",
    text: "text-red-800 dark:text-red-300",
    border: "border-red-200 dark:border-red-500/20",
    dot: "bg-red-500",
  },
  blue: {
    bg: "bg-blue-50 dark:bg-blue-500/10",
    text: "text-blue-800 dark:text-blue-300",
    border: "border-blue-200 dark:border-blue-500/20",
    dot: "bg-blue-500",
  },
  green: {
    bg: "bg-green-50 dark:bg-green-500/10",
    text: "text-green-800 dark:text-green-300",
    border: "border-green-200 dark:border-green-500/20",
    dot: "bg-green-500",
  },
  emerald: {
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    text: "text-emerald-800 dark:text-emerald-300",
    border: "border-emerald-200 dark:border-emerald-500/20",
    dot: "bg-emerald-500",
  },
  yellow: {
    bg: "bg-yellow-50 dark:bg-yellow-500/10",
    text: "text-yellow-700 dark:text-yellow-300",
    border: "border-yellow-200 dark:border-yellow-500/20",
    dot: "bg-yellow-500",
  },
  amber: {
    bg: "bg-amber-50 dark:bg-amber-500/10",
    text: "text-amber-800 dark:text-amber-300",
    border: "border-amber-200 dark:border-amber-500/20",
    dot: "bg-amber-500",
  },
  purple: {
    bg: "bg-purple-50 dark:bg-purple-500/10",
    text: "text-purple-800 dark:text-purple-300",
    border: "border-purple-200 dark:border-purple-500/20",
    dot: "bg-purple-500",
  },
  gray: {
    bg: "bg-gray-50 dark:bg-gray-500/10",
    text: "text-gray-700 dark:text-gray-300",
    border: "border-gray-200 dark:border-gray-500/20",
    dot: "bg-gray-500",
  },
};

const SIZE_VARIANTS = {
  xs: {
    container: "px-1.5 py-0.5 text-[10px] min-w-14 gap-1",
    dot: "w-1.5 h-1.5",
  },
  sm: {
    container: "px-2 py-1 text-[11px] min-w-16 gap-1",
    dot: "w-1.5 h-1.5",
  },
  md: {
    container: "px-3 py-1.5 text-xs min-w-20 gap-2",
    dot: "w-2 h-2",
  },
  lg: {
    container: "px-3.5 py-2 text-sm min-w-24 gap-2.5",
    dot: "w-2.5 h-2.5",
  },
  xl: {
    container: "px-4 py-2.5 text-base min-w-28 gap-3",
    dot: "w-3 h-3",
  },
};

const CustomBadge = ({
  label,
  color = "gray",
  size = "md",
  className = "",
  role,
  isActive,
  status,
  severity,
  animateDot = false,
}) => {
  let displayLabel = label;
  let displayColor = color;

  if (role) {
    displayLabel = label || getRoleLabel(role);
    displayColor = ROLE_COLOR[role?.toLowerCase()] || "gray";
  } else if (isActive !== undefined) {
    displayLabel = label || (isActive ? "Active" : "Inactive");
    displayColor = isActive ? "green" : "red";
  } else if (status) {
    displayLabel = label || capitalizeFirst(status);
    displayColor = STATUS_COLOR[status?.toLowerCase()] || "gray";
  } else if (severity) {
    displayLabel = label || capitalizeFirst(severity);
    displayColor = SEVERITY_COLOR[severity?.toLowerCase()] || "gray";
  }

  const c = COLOR_VARIANTS[displayColor] || COLOR_VARIANTS.gray;
  const s = SIZE_VARIANTS[size] || SIZE_VARIANTS.md;

  return (
    <span
      className={`inline-flex items-center rounded font-semibold capitalize border whitespace-nowrap
      ${c.bg} ${c.text} ${c.border} ${s.container} ${className}`}
    >
      <span
        className={`rounded-full shrink-0 ${c.dot} ${s.dot} ${
          animateDot ? "animate-ping" : ""
        }`}
      />
      <span className="truncate">{displayLabel || "N/A"}</span>
    </span>
  );
};

export default CustomBadge;
