import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import {
  STATUS_APPROVED,
  STATUS_COMPLETED,
  STATUS_CONNECTED,
  STATUS_DONE,
  STATUS_FAILED,
  STATUS_LOCKED,
  STATUS_PENDING,
  STATUS_PROCESSING,
  STATUS_REJECTED,
  STATUS_RUNNING,
  STATUS_STARTED,
} from "@/utils/commonUtils";

export const getPackageViewModel = (framework) => {
  const packages = framework?.packages || [];
  const currentPackage =
    packages.find(
      (pkg) => pkg.packageVersion === framework?.currentPackageVersion
    ) || packages[0];

  // preReleasePackage represents the current active/working package shown in
  // the Deployment Package section. It is always the currentPackage regardless
  // of type — the badge on the card reflects the actual type (pre-release /
  // in-review / deployed).
  const preReleasePackage = currentPackage ?? null;

  return {
    currentPackage,
    preReleasePackage,
    livePackage: packages.find((pkg) => pkg.status?.toLowerCase() === "live"),
    // currentReviewPackage is used for the Expert Sign-off Gate steps.
    // After approval the current package is live — we still want to show its
    // gate steps, so fall back to currentPackage when no non-live match exists.
    currentReviewPackage:
      packages.find(
        (pkg) =>
          pkg.packageVersion === framework?.currentPackageVersion &&
          pkg.status !== "live"
      ) ?? currentPackage,
  };
};

export const getUploadMeta = (createdAt) =>
  createdAt ? `${formatDateWithMonthNameAndTime(createdAt)}` : "";

export const getComparisonStep = (comparison) => {
  const status = comparison?.status?.toLowerCase();
  const isCompleted = comparison === true || status === STATUS_COMPLETED;
  const isRunning =
    status === STATUS_CONNECTED ||
    status === STATUS_STARTED ||
    status === STATUS_PROCESSING ||
    status === STATUS_RUNNING;
  const isFailed = status === STATUS_FAILED;

  if (isCompleted) {
    return {
      status: STATUS_DONE,
      title: "AI Comparison Completed",
      desc: "Document comparison completed successfully.",
      meta: "Automated",
    };
  }
  if (isRunning) {
    return {
      status: STATUS_PENDING,
      title: "AI Comparison Running",
      desc: "AI comparison is currently in progress.",
      meta: "Processing in background...",
    };
  }
  if (isFailed) {
    return {
      status: STATUS_FAILED,
      title: "AI Comparison Failed",
      desc: comparison?.message || "AI comparison failed to complete.",
      meta: "Failed",
    };
  }
  return {
    status: STATUS_PENDING,
    title: "AI Comparison Pending",
    desc: "AI comparison is not completed yet.",
    meta: "Waiting for AI processing",
  };
};

export const getGapAnalysisStep = (gapAnalysis) => {
  const status = gapAnalysis?.status?.toLowerCase();
  const isCompleted = gapAnalysis === true || status === STATUS_COMPLETED;
  const isRunning =
    status === STATUS_CONNECTED ||
    status === STATUS_STARTED ||
    status === STATUS_PROCESSING ||
    status === STATUS_RUNNING;
  const isFailed = status === STATUS_FAILED;

  if (isCompleted) {
    return {
      status: STATUS_DONE,
      title: "AI Gap Analysis Completed",
      desc: "Gap analysis report generated successfully.",
      meta: "Automated",
    };
  }
  if (isRunning) {
    return {
      status: STATUS_PENDING,
      title: "AI Gap Analysis Running",
      desc: "AI gap analysis is currently in progress.",
      meta: "Processing in background...",
    };
  }
  if (isFailed) {
    return {
      status: STATUS_FAILED,
      title: "AI Gap Analysis Failed",
      desc: gapAnalysis?.message || "AI gap analysis failed to complete.",
      meta: "Failed",
    };
  }
  return {
    status: STATUS_PENDING,
    title: "AI Gap Analysis Pending",
    desc: "AI gap analysis is not completed yet.",
    meta: "Waiting for AI processing",
  };
};

export const getExpertReviewStep = (expertReview) => {
  const status = expertReview?.status?.toLowerCase();
  const assignedExpert = expertReview?.assignedExpert;
  const meta = assignedExpert
    ? `Assigned to: ${assignedExpert.name || assignedExpert}`
    : "Expert not assigned";

  if (status === STATUS_APPROVED) {
    return {
      status: STATUS_DONE,
      title: "Expert Review Completed",
      desc: "Expert has approved this deployment package.",
      meta,
    };
  }
  if (status === STATUS_REJECTED) {
    return {
      status: STATUS_PENDING,
      title: "Expert Review Returned",
      desc: "Expert has returned the package with feedback.",
      meta,
    };
  }
  return {
    status: STATUS_PENDING,
    title: "Awaiting Expert Review",
    desc: "Assigned SME must review gap findings and approve or return the package.",
    meta,
  };
};

export const getDeployStep = (isLive, version) => {
  if (isLive) {
    return {
      status: STATUS_DONE,
      title: `Deploy as v${version}`,
      desc: "Package deployed successfully.",
      meta: "",
    };
  }
  return {
    status: STATUS_LOCKED,
    title: `Deploy as v${version}`,
    desc: "Deployment will be available after expert approval.",
    meta: "",
  };
};

const getDocumentPlural = (count) => (count === 1 ? "" : "s");

const buildExtractionDetails = (pendingCount, failedCount) => {
  const details = [];
  if (pendingCount > 0) {
    details.push(`${pendingCount} pending AI processing`);
  }
  if (failedCount > 0) {
    details.push(`${failedCount} failed extraction`);
  }
  return details;
};

const getExtractionDescription = (
  totalDocs,
  extractedCount,
  failedCount,
  pendingCount
) => {
  if (totalDocs === 0) {
    return "No documents uploaded in this package.";
  }
  if (extractedCount === totalDocs) {
    const plural = getDocumentPlural(totalDocs);
    return `All ${totalDocs} document${plural} successfully processed and extracted.`;
  }
  const details = buildExtractionDetails(pendingCount, failedCount);
  const plural = getDocumentPlural(totalDocs);
  let desc = `${extractedCount}/${totalDocs} document${plural} extracted`;
  if (details.length > 0) {
    desc += ` (${details.join(", ")})`;
  }
  return desc + ".";
};

const getExtractionStatus = (totalDocs, extractedCount, failedCount) => {
  if (totalDocs === 0) {
    return STATUS_PENDING;
  }
  if (extractedCount === totalDocs) {
    return STATUS_DONE;
  }
  return failedCount > 0 ? STATUS_FAILED : STATUS_PENDING;
};

export const getMergeDocumentStep = (mergeDocument) => {
  const status = mergeDocument?.status?.toLowerCase();
  const isCompleted = status === "merged";
  const isRunning =
    status === STATUS_CONNECTED ||
    status === STATUS_STARTED ||
    status === STATUS_PROCESSING ||
    status === STATUS_RUNNING;
  const isFailed = status === STATUS_FAILED;

  if (isCompleted) {
    return {
      status: STATUS_DONE,
      title: "AI Controls Merge Completed",
      desc: "Controls merge completed successfully.",
      meta: mergeDocument.timestamp
        ? formatDateWithMonthNameAndTime(mergeDocument.timestamp)
        : "Automated",
    };
  }
  if (isRunning) {
    return {
      status: STATUS_PENDING,
      title: "AI Controls Merge Running",
      desc: "AI controls merge is currently in progress.",
      meta: "Processing in background...",
    };
  }
  if (isFailed) {
    return {
      status: STATUS_FAILED,
      title: "AI Controls Merge Failed",
      desc: mergeDocument?.message || "AI controls merge failed to complete.",
      meta: "Failed",
    };
  }
  return {
    status: STATUS_PENDING,
    title: "AI Controls Merge Pending",
    desc: "AI controls merge is not completed yet.",
    meta: "Waiting for AI processing",
  };
};

export const buildGateSteps = (currentReviewPackage) => {
  if (!currentReviewPackage) return [];

  const isLive = currentReviewPackage.status?.toLowerCase() === "live";
  const documents = currentReviewPackage.documents || [];
  const totalDocs = documents.length;
  const extractedCount = documents.filter(
    (doc) => doc.aiExtraction?.status === "extracted"
  ).length;
  const failedCount = documents.filter(
    (doc) => doc.aiExtraction?.status === "failed"
  ).length;
  const pendingCount = totalDocs - extractedCount - failedCount;

  const firstStepStatus = getExtractionStatus(
    totalDocs,
    extractedCount,
    failedCount
  );
  const firstStepDesc = getExtractionDescription(
    totalDocs,
    extractedCount,
    failedCount,
    pendingCount
  );

  return [
    {
      status: firstStepStatus,
      title: `AI Document Extraction (v${currentReviewPackage.packageVersion})`,
      desc: firstStepDesc,
      meta: getUploadMeta(currentReviewPackage.createdAt),
    },
    getMergeDocumentStep(currentReviewPackage.mergeDocument),
    getComparisonStep(currentReviewPackage.comparison),
    getGapAnalysisStep(currentReviewPackage.gapAnalysis),
    getExpertReviewStep(currentReviewPackage.expertReview),
    getDeployStep(isLive, currentReviewPackage.packageVersion),
  ];
};

export const transformAssignedFrameworks = (
  assignedFrameworks,
  framework,
  loadingAssignedFramework
) => {
  if (loadingAssignedFramework || !framework?.assignedFramework) {
    return null;
  }

  const f = assignedFrameworks.find(
    (item) => item.id === framework.assignedFramework.id
  );

  if (!f) {
    console.error("Assigned framework not found for the current framework");
    return null;
  }

  return {
    assignedFrameworkId: f.id,
    frameworkName: f.frameworkName,
    frameworkVersion: f.frameworkVersion,
    finalization: f.finalization,
    assignment: f.assignment,
    revocation: f.revocation,
    status: f.status,
  };
};

export const getStatusBadgeProps = (status, type) => {
  const normalized = status?.toLowerCase() || "not started";
  let displayType = "Gap Analysis";
  if (type === "comparison") {
    displayType = "Comparison";
  } else if (type === "merge") {
    displayType = "Controls Merge";
  }

  switch (normalized) {
    case "completed":
    case "merged":
      return {
        className:
          "px-3 py-1 rounded text-xs font-semibold bg-emerald-50 text-teal-600 border border-emerald-200",
        label: `${displayType} Completed`,
      };
    case "connected":
    case "started":
    case "running":
    case "processing":
      return {
        className:
          "px-3 py-1 rounded text-xs font-semibold bg-amber-50 text-amber-600 border border-amber-200 animate-pulse",
        label: `${displayType} Running...`,
      };
    case "failed":
      return {
        className:
          "px-3 py-1 rounded text-xs font-semibold bg-rose-50 text-rose-600 border border-rose-200",
        label: `${displayType} Failed`,
      };
    default:
      return {
        className:
          "px-3 py-1 rounded text-xs font-semibold bg-slate-50 text-slate-500 border border-slate-200",
        label: `${displayType} Not Started`,
      };
  }
};
