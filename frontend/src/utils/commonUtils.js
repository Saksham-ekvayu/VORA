export const ROLE_ADMIN = "admin";
export const ROLE_EXPERT = "expert";
export const ROLE_INTERNAL_EXPERT = "internal-expert";
export const ROLE_CUSTOMER_ADMIN = "customer-admin";
export const ROLE_AUDITOR = "auditor";
export const ROLE_USER = "user";
export const ROLE_ALL = "all";

export const STATUS_PENDING = "pending";
export const STATUS_APPROVED = "approved";
export const STATUS_REJECTED = "rejected";
export const STATUS_UPLOADED = "uploaded";
export const STATUS_FAILED = "failed";
export const STATUS_PROCESSING = "processing";
export const STATUS_EXTRACTED = "extracted";
export const STATUS_ASSIGNED = "assigned";
export const STATUS_REVOKED = "revoked";
export const STATUS_FINALIZED = "finalized";
export const STATUS_REQUESTED = "requested";
export const STATUS_COMPLETED = "completed";
export const STATUS_CONNECTED = "connected";
export const STATUS_STARTED = "started";
export const STATUS_RUNNING = "running";
export const STATUS_DONE = "done";
export const STATUS_LOCKED = "locked";
export const STATUS_MERGED = "merged";
export const STATUS_LIVE = "live";
export const STATUS_SKIPPED = "skipped";
export const STATUS_RETURNED = "returned";
export const STATUS_SUPERSEDED = "superseded";
export const STATUS_IN_REVIEW = "in-review";
export const STATUS_DEPLOYED = "deployed";
export const STATUS_ARCHIVED = "archived";
export const STATUS_NOT_FINALIZED = "not finalized";
export const STATUS_ACTIVE = "active";
export const STATUS_INACTIVE = "inactive";
export const STATUS_IMPLEMENTED = "implemented";
export const STATUS_PARTIAL = "partially implemented";
export const STATUS_NOT_IMPLEMENTED = "not implemented";

export const COLOR_DEFAULT = "default";
export const COLOR_AMBER = "amber";
export const COLOR_BLUE = "blue";
export const COLOR_GREEN = "green";
export const COLOR_RED = "red";
export const COLOR_DESTRUCTIVE = "destructive";
export const COLOR_VIOLET = "violet";
export const COLOR_INDIGO = "indigo";
export const COLOR_GRAY = "gray";

export const ROLE_LABELS = {
  [ROLE_ADMIN]: "Admin",
  [ROLE_EXPERT]: "Expert",
  [ROLE_INTERNAL_EXPERT]: "Internal Expert",
  [ROLE_CUSTOMER_ADMIN]: "Customer Admin",
  [ROLE_AUDITOR]: "Auditor",
  [ROLE_USER]: "User",
};

export const ROLE_BADGE_CLASSES = {
  [ROLE_ADMIN]: "bg-red-100 text-red-800",
  [ROLE_EXPERT]: "bg-blue-100 text-blue-800",
  [ROLE_INTERNAL_EXPERT]: "bg-indigo-100 text-indigo-800",
  [ROLE_CUSTOMER_ADMIN]: "bg-amber-100 text-amber-800",
  [ROLE_AUDITOR]: "bg-violet-100 text-violet-800",
  [ROLE_USER]: "bg-green-100 text-green-800",
};

export const STATUS_LABELS = {
  [STATUS_PENDING]: "Pending",
  [STATUS_APPROVED]: "Approved",
  [STATUS_REJECTED]: "Rejected",
  [STATUS_UPLOADED]: "Uploaded",
  [STATUS_FAILED]: "Failed",
  [STATUS_PROCESSING]: "Processing",
  [STATUS_EXTRACTED]: "Extracted",
  [STATUS_ASSIGNED]: "Assigned",
  [STATUS_REVOKED]: "Revoked",
  [STATUS_FINALIZED]: "Finalized",
  [STATUS_REQUESTED]: "Requested",
  [STATUS_COMPLETED]: "Completed",
  [STATUS_CONNECTED]: "Connected",
  [STATUS_STARTED]: "Started",
  [STATUS_RUNNING]: "Running",
  [STATUS_DONE]: "Done",
  [STATUS_LOCKED]: "Locked",
  [STATUS_MERGED]: "Merged",
  [STATUS_LIVE]: "Live",
  [STATUS_SKIPPED]: "Skipped",
  [STATUS_RETURNED]: "Returned",
  [STATUS_SUPERSEDED]: "Superseded",
  [STATUS_IN_REVIEW]: "In Review",
  [STATUS_DEPLOYED]: "Deployed",
  [STATUS_ARCHIVED]: "Archived",
  [STATUS_IMPLEMENTED]: "Implemented",
  [STATUS_PARTIAL]: "Partially Implemented",
  [STATUS_NOT_IMPLEMENTED]: "Not Implemented",
  [STATUS_NOT_FINALIZED]: "Not Finalized",
  [STATUS_ACTIVE]: "Active",
  [STATUS_INACTIVE]: "Inactive",
};

export const isAdmin = (role) => role === ROLE_ADMIN;
export const isExpert = (role) => role === ROLE_EXPERT;
export const isInternalExpert = (role) => role === ROLE_INTERNAL_EXPERT;
export const isCustomerAdmin = (role) => role === ROLE_CUSTOMER_ADMIN;
export const isAuditor = (role) => role === ROLE_AUDITOR;
export const isUser = (role) => role === ROLE_USER;

export const getRoleBadgeClass = (role) => {
  return ROLE_BADGE_CLASSES[role] || ROLE_BADGE_CLASSES[ROLE_USER];
};

export const getRoleFilterLabel = (role) => {
  if (role === ROLE_ADMIN) return ROLE_LABELS[ROLE_ADMIN];
  if (role === ROLE_EXPERT) return ROLE_LABELS[ROLE_EXPERT];
  if (role === ROLE_INTERNAL_EXPERT) return ROLE_LABELS[ROLE_INTERNAL_EXPERT];
  if (role === ROLE_CUSTOMER_ADMIN) return ROLE_LABELS[ROLE_CUSTOMER_ADMIN];
  if (role === ROLE_AUDITOR) return ROLE_LABELS[ROLE_AUDITOR];
  if (role === ROLE_USER) return ROLE_LABELS[ROLE_USER];
  return "All Roles";
};

export const getStatusFilterLabel = (status) => {
  if (status === "true") return STATUS_LABELS[STATUS_ACTIVE];
  if (status === "false") return STATUS_LABELS[STATUS_INACTIVE];
  return "Activity Status";
};

export const getRoleLabel = (role) => {
  if (role === ROLE_EXPERT) return ROLE_LABELS[ROLE_EXPERT];
  if (role === ROLE_INTERNAL_EXPERT) return ROLE_LABELS[ROLE_INTERNAL_EXPERT];
  if (role === ROLE_CUSTOMER_ADMIN) return ROLE_LABELS[ROLE_CUSTOMER_ADMIN];
  if (role === ROLE_ADMIN) return ROLE_LABELS[ROLE_ADMIN];
  if (role === ROLE_AUDITOR) return ROLE_LABELS[ROLE_AUDITOR];
  return ROLE_LABELS[ROLE_USER];
};

export const getAssignmentStatusFilterLabel = (status) => {
  if (status === STATUS_ASSIGNED) return STATUS_LABELS[STATUS_ASSIGNED];
  if (status === STATUS_REVOKED) return STATUS_LABELS[STATUS_REVOKED];
  return "Assignment Status";
};

export const getFinalizationStatusFilterLabel = (finalizationStatus) => {
  if (finalizationStatus === STATUS_FINALIZED)
    return STATUS_LABELS[STATUS_FINALIZED];
  if (finalizationStatus === STATUS_PENDING)
    return STATUS_LABELS[STATUS_NOT_FINALIZED];
  return "Finalization Status";
};

export const getAccessStatusFilterLabel = (status) => {
  if (status === STATUS_PENDING) return STATUS_LABELS[STATUS_PENDING];
  if (status === STATUS_APPROVED) return STATUS_LABELS[STATUS_APPROVED];
  if (status === STATUS_REJECTED) return STATUS_LABELS[STATUS_REJECTED];
  if (status === STATUS_REVOKED) return STATUS_LABELS[STATUS_REVOKED];
  return "Access Status";
};

export const getAiStatusFilterLabel = (status) => {
  if (status === STATUS_UPLOADED) return STATUS_LABELS[STATUS_UPLOADED];
  if (status === STATUS_FAILED) return STATUS_LABELS[STATUS_FAILED];
  if (status === STATUS_PENDING) return STATUS_LABELS[STATUS_PENDING];
  if (status === STATUS_PROCESSING) return STATUS_LABELS[STATUS_PROCESSING];
  if (status === STATUS_EXTRACTED) return STATUS_LABELS[STATUS_EXTRACTED];
  return "Ai Extraction";
};

export const getApprovalFilterLabel = (status) => {
  if (status === STATUS_APPROVED) return STATUS_LABELS[STATUS_APPROVED];
  if (status === STATUS_REJECTED) return STATUS_LABELS[STATUS_REJECTED];
  if (status === STATUS_PENDING) return STATUS_LABELS[STATUS_PENDING];
  return "Approval";
};

export const getReviewStatusFilterLabel = (status) => {
  if (status === STATUS_PENDING) return STATUS_LABELS[STATUS_PENDING];
  if (status === STATUS_REQUESTED) return STATUS_LABELS[STATUS_REQUESTED];
  if (status === STATUS_APPROVED) return STATUS_LABELS[STATUS_APPROVED];
  if (status === STATUS_REJECTED) return STATUS_LABELS[STATUS_REJECTED];
  return "Review Status";
};

export const getAiExtractionStatusFilterLabel = (status) => {
  if (status === STATUS_PENDING) return STATUS_LABELS[STATUS_PENDING];
  if (status === STATUS_UPLOADED) return STATUS_LABELS[STATUS_UPLOADED];
  if (status === STATUS_FAILED) return STATUS_LABELS[STATUS_FAILED];
  if (status === STATUS_PROCESSING) return STATUS_LABELS[STATUS_PROCESSING];
  if (status === STATUS_EXTRACTED) return STATUS_LABELS[STATUS_EXTRACTED];
  return "AI Extraction";
};

export const getAiExtractionStatusLabel = (status) => {
  if (status === STATUS_UPLOADED) return STATUS_LABELS[STATUS_UPLOADED];
  if (status === STATUS_PROCESSING) return STATUS_LABELS[STATUS_PROCESSING];
  if (status === STATUS_EXTRACTED) return STATUS_LABELS[STATUS_EXTRACTED];
  if (status === STATUS_FAILED) return STATUS_LABELS[STATUS_FAILED];
  return STATUS_LABELS[STATUS_PENDING];
};

export const getApprovalStatusLabel = (status) => {
  if (status === STATUS_APPROVED) return STATUS_LABELS[STATUS_APPROVED];
  if (status === STATUS_REJECTED) return STATUS_LABELS[STATUS_REJECTED];
  return STATUS_LABELS[STATUS_PENDING];
};

export const getReviewIcon = (role, hasComment) => {
  if (isAuditor(role)) return "eye";
  return hasComment ? "edit" : "plus";
};

export const statusVariantMap = {
  pending: COLOR_AMBER,
  returned: COLOR_DESTRUCTIVE,
  live: COLOR_GREEN,
  superseded: COLOR_BLUE,
};

export const typeVariantMap = {
  "pre-release": COLOR_AMBER,
  "in-review": COLOR_AMBER,
  deployed: COLOR_BLUE,
};

export const packageTypeColorMap = {
  blue: { border: "border-t-blue-500", bg: "bg-blue-500" },
  green: { border: "border-t-green-500", bg: "bg-green-500" },
  default: { border: "border-t-amber-400", bg: "bg-amber-400" },
};

export const getExpertReviewBadgeVariant = (status) => {
  const map = {
    approved: COLOR_DEFAULT,
    requested: COLOR_AMBER,
    rejected: COLOR_DESTRUCTIVE,
  };
  return map[status] || COLOR_AMBER;
};

export const getExpertReviewBadgeIcon = (status) => {
  const map = {
    approved: "check-circle",
    requested: "hourglass",
    rejected: "x-circle",
  };
  return map[status] || "hourglass";
};

export const getAssignedFrameworkApprovalStatusClass = (status) => {
  if (status === "assigned")
    return "bg-primary/10 border-primary/30 text-primary";
  if (status === "revoked") return "bg-red-50 border-red-300 text-red-700";
  return "bg-yellow-50 border-yellow-300 text-yellow-700";
};

export const getApprovalStatusClass = (status) => {
  if (status === STATUS_APPROVED) return "bg-primary/10 text-primary";
  if (status === STATUS_REJECTED) return "bg-red-50 text-red-700";
  return "bg-yellow-50 text-yellow-700";
};

export const getAiExtractionStatusClass = (status) => {
  if (status === STATUS_UPLOADED) return "bg-blue-50 text-blue-700";
  if (status === STATUS_PROCESSING) return "bg-blue-50 text-blue-700";
  if (status === STATUS_EXTRACTED) return "bg-green-50 text-green-700";
  if (status === STATUS_FAILED) return "bg-red-50 text-red-700";
  return "bg-yellow-50 text-yellow-700";
};

export const STATUS_BADGE_COLORS = {
  [STATUS_APPROVED]:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  [STATUS_COMPLETED]:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  [STATUS_REJECTED]:
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  [STATUS_FAILED]:
    "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  [STATUS_REQUESTED]:
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  [STATUS_PENDING]:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  [STATUS_PROCESSING]:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  default: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

export const APPROVAL_STATUS_COLORS = {
  [STATUS_APPROVED]:
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
  [STATUS_PENDING]:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  [STATUS_REJECTED]: "bg-destructive/10 text-destructive",
  default: "bg-muted text-muted-foreground",
};

export const getStatusBadgeColor = (status) => {
  const key = String(status || "").toLowerCase();
  return STATUS_BADGE_COLORS[key] || STATUS_BADGE_COLORS.default;
};

export const getApprovalStatusColor = (status) => {
  return APPROVAL_STATUS_COLORS[status] || APPROVAL_STATUS_COLORS.default;
};

export const aiExtractionConfig = {
  [STATUS_PENDING]: {
    label: "Pending",
    icon: "hourglass",
    textClass: "text-amber-600 dark:text-amber-400",
    buttonText: "Extract Controls",
    buttonIcon: "ai-bot",
    buttonDisabled: false,
    buttonClass:
      "text-primary border-primary/30 bg-primary/5 hover:bg-primary/10",
  },

  [STATUS_UPLOADED]: {
    label: "Uploaded",
    icon: "upload-cloud",
    textClass: "text-blue-600 dark:text-blue-400",
    buttonText: "Extract Controls",
    buttonIcon: "ai-bot",
    buttonDisabled: true,
    buttonClass:
      "text-muted-foreground border-border bg-muted/30 cursor-not-allowed",
  },

  [STATUS_PROCESSING]: {
    label: "Processing",
    icon: "loader",
    textClass: "text-violet-600 dark:text-violet-400 animate-pulse",
    buttonText: "Extract Controls",
    buttonIcon: "ai-bot",
    buttonDisabled: true,
    buttonClass:
      "text-muted-foreground border-border bg-muted/30 cursor-not-allowed",
  },

  [STATUS_EXTRACTED]: {
    label: "Extracted",
    icon: "check-circle",
    textClass: "text-green-600 dark:text-green-400",
    buttonText: "Extract Controls",
    buttonIcon: "ai-bot",
    buttonDisabled: true,
    buttonClass:
      "text-muted-foreground border-border bg-muted/30 cursor-not-allowed",
  },

  [STATUS_FAILED]: {
    label: "Failed",
    icon: "alert-circle",
    textClass: "text-red-600 dark:text-red-400",
    buttonText: "Retry Extraction",
    buttonIcon: "refresh",
    buttonDisabled: false,
    buttonClass:
      "text-red-600 border-red-300 bg-red-50 hover:bg-red-100 dark:bg-red-950/30",
  },
};

// Centralized visual mapping for statuses (icons + color classes)
export const STATUS_VISUALS = {
  [STATUS_PENDING]: {
    icon: "hourglass",
    bgColor: "bg-yellow-50 dark:bg-yellow-500/10",
    borderColor: "border-yellow-200 dark:border-yellow-500/20",
    iconColor: "text-yellow-700 dark:text-yellow-300",
    labelColor: "text-yellow-700 dark:text-yellow-300",
    label: "Pending",
  },
  [STATUS_REQUESTED]: {
    icon: "send",
    bgColor: "bg-amber-50 dark:bg-amber-500/10",
    borderColor: "border-amber-200 dark:border-amber-500/20",
    iconColor: "text-amber-800 dark:text-amber-300",
    labelColor: "text-amber-800 dark:text-amber-300",
    label: "Requested",
  },
  [STATUS_APPROVED]: {
    icon: "check-circle",
    bgColor: "bg-green-50 dark:bg-green-500/10",
    borderColor: "border-green-200 dark:border-green-500/20",
    iconColor: "text-green-800 dark:text-green-300",
    labelColor: "text-green-800 dark:text-green-300",
    label: "Approved",
  },
  [STATUS_COMPLETED]: {
    icon: "check-circle",
    bgColor: "bg-green-50 dark:bg-green-500/10",
    borderColor: "border-green-200 dark:border-green-500/20",
    iconColor: "text-green-800 dark:text-green-300",
    labelColor: "text-green-800 dark:text-green-300",
    label: "Completed",
  },
  [STATUS_EXTRACTED]: {
    icon: "check-circle",
    bgColor: "bg-green-50 dark:bg-green-500/10",
    borderColor: "border-green-200 dark:border-green-500/20",
    iconColor: "text-green-800 dark:text-green-300",
    labelColor: "text-green-800 dark:text-green-300",
    label: "Extracted",
  },
  [STATUS_PROCESSING]: {
    icon: "loader",
    bgColor: "bg-blue-50 dark:bg-blue-500/10",
    borderColor: "border-blue-200 dark:border-blue-500/20",
    iconColor: "text-blue-800 dark:text-blue-300 animate-spin",
    labelColor: "text-blue-800 dark:text-blue-300",
    label: "Processing",
  },
  [STATUS_UPLOADED]: {
    icon: "upload-cloud",
    bgColor: "bg-purple-50 dark:bg-purple-500/10",
    borderColor: "border-purple-200 dark:border-purple-500/20",
    iconColor: "text-purple-800 dark:text-purple-300",
    labelColor: "text-purple-800 dark:text-purple-300",
    label: "Uploaded",
  },
  [STATUS_FAILED]: {
    icon: "error",
    bgColor: "bg-red-50 dark:bg-red-500/10",
    borderColor: "border-red-200 dark:border-red-500/20",
    iconColor: "text-red-800 dark:text-red-300",
    labelColor: "text-red-800 dark:text-red-300",
    label: "Failed",
  },
  [STATUS_REJECTED]: {
    icon: "x-circle",
    bgColor: "bg-red-50 dark:bg-red-500/10",
    borderColor: "border-red-200 dark:border-red-500/20",
    iconColor: "text-red-800 dark:text-red-300",
    labelColor: "text-red-800 dark:text-red-300",
    label: "Rejected",
  },
  [STATUS_SKIPPED]: {
    icon: "warning",
    bgColor: "bg-yellow-50 dark:bg-yellow-500/10",
    borderColor: "border-yellow-200 dark:border-yellow-500/20",
    iconColor: "text-yellow-800 dark:text-yellow-300",
    labelColor: "text-yellow-800 dark:text-yellow-300",
    label: "Skipped",
  },
  [STATUS_LIVE]: {
    icon: "check-circle",
    bgColor: "bg-green-50 dark:bg-green-500/10",
    borderColor: "border-green-200 dark:border-green-500/20",
    iconColor: "text-green-800 dark:text-green-300",
    labelColor: "text-green-800 dark:text-green-300",
    label: "Live",
  },
  [STATUS_RETURNED]: {
    icon: "refresh",
    bgColor: "bg-red-50 dark:bg-red-500/10",
    borderColor: "border-red-200 dark:border-red-500/20",
    iconColor: "text-red-800 dark:text-red-300",
    labelColor: "text-red-800 dark:text-red-300",
    label: "Returned",
  },
  [STATUS_SUPERSEDED]: {
    icon: "arrow-up",
    bgColor: "bg-blue-50 dark:bg-blue-500/10",
    borderColor: "border-blue-200 dark:border-blue-500/20",
    iconColor: "text-blue-800 dark:text-blue-300",
    labelColor: "text-blue-800 dark:text-blue-300",
    label: "Superseded",
  },
  [STATUS_IN_REVIEW]: {
    icon: "hourglass",
    bgColor: "bg-amber-50 dark:bg-amber-500/10",
    borderColor: "border-amber-200 dark:border-amber-500/20",
    iconColor: "text-amber-800 dark:text-amber-300",
    labelColor: "text-amber-800 dark:text-amber-300",
    label: "In Review",
  },
  [STATUS_DEPLOYED]: {
    icon: "check-circle",
    bgColor: "bg-primary/5 dark:bg-primary/10",
    borderColor: "border-primary/20",
    iconColor: "text-primary",
    labelColor: "text-primary",
    label: "Deployed",
  },
  [STATUS_REVOKED]: {
    icon: "x-circle",
    bgColor: "bg-red-50 dark:bg-red-500/10",
    borderColor: "border-red-200 dark:border-red-500/20",
    iconColor: "text-red-800 dark:text-red-300",
    labelColor: "text-red-800 dark:text-red-300",
    label: "Revoked",
  },
  [STATUS_ARCHIVED]: {
    icon: "archive",
    bgColor: "bg-gray-50 dark:bg-gray-500/10",
    borderColor: "border-gray-200 dark:border-gray-500/20",
    iconColor: "text-gray-800 dark:text-gray-300",
    labelColor: "text-gray-800 dark:text-gray-300",
    label: "Archived",
  },
  default: {
    icon: "warning",
    bgColor: "bg-yellow-50 dark:bg-yellow-500/10",
    borderColor: "border-yellow-200 dark:border-yellow-500/20",
    iconColor: "text-yellow-800 dark:text-yellow-300",
    labelColor: "text-yellow-800 dark:text-yellow-300",
    label: "Unknown",
  },
};

export const getStatusVisual = (status) => {
  const key = String(status || "").toLowerCase();
  return STATUS_VISUALS[key] || STATUS_VISUALS.default;
};

export const getRequestActionLabel = (requestStatus, hasRequested) => {
  if (requestStatus === STATUS_REVOKED || requestStatus === STATUS_REJECTED)
    return "Re-request Access";
  if (hasRequested) return "Access Requested";
  return "Request Access";
};

export const getRequestActionIcon = (requestStatus, hasRequested) => {
  if (requestStatus === STATUS_REVOKED || requestStatus === STATUS_REJECTED)
    return "refresh";
  if (hasRequested) return "check";
  return "plus";
};

// ---------------------------------------------------------------------------
// Similarity / Semantic Score helpers
// ---------------------------------------------------------------------------

export const getScoreColor = (score) => {
  if (score >= 80) return "#0d9488"; // teal  — High
  if (score >= 60) return "#f59e0b"; // amber — Medium
  return "#ef4444"; // red   — Low
};

export const getScoreLabel = (score) => {
  if (score >= 80) return "High";
  if (score >= 60) return "Medium";
  return "Low";
};

export const getScoreMatchClass = (score) => {
  if (score >= 80) return "high";
  if (score >= 60) return "medium";
  return "low";
};

// Returns { color, bgColor } for inline styles
export const getScoreStyle = (score) => {
  const color = getScoreColor(score);
  return { color, backgroundColor: `${color}15` };
};

// ---------------------------------------------------------------------------
// Gap Analysis implementation-status helpers
// ---------------------------------------------------------------------------

export const getGapStatusColor = (status) => {
  switch (status?.toLowerCase()) {
    case STATUS_IMPLEMENTED:
      return "#16a34a"; // green
    case STATUS_PARTIAL:
      return "#d97706"; // amber
    case STATUS_NOT_IMPLEMENTED:
      return "#dc2626"; // red
    default:
      return "#6b7280"; // gray
  }
};

// Returns { color, backgroundColor } for inline styles
export const getGapStatusStyle = (status) => {
  const color = getGapStatusColor(status);
  return { color, backgroundColor: `${color}1a` };
};

export const capitalizeFirst = (text) => {
  if (typeof text !== "string" || !text) return "";
  return text.charAt(0).toUpperCase() + text.slice(1);
};
