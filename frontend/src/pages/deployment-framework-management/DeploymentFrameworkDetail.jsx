/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAuth } from "@/context/authContext/useAuth";
import { usePageTitle } from "@/hooks/usePageTitle";
import {
  isInternalExpert,
  isAuditor,
  isCustomerAdmin,
  STATUS_PENDING,
  STATUS_CONNECTED,
  STATUS_RUNNING,
  STATUS_PROCESSING,
  STATUS_STARTED,
  STATUS_EXTRACTED,
  STATUS_APPROVED,
  STATUS_COMPLETED,
  STATUS_REVOKED,
  STATUS_DONE,
  STATUS_FAILED,
  STATUS_LOCKED,
  STATUS_UPLOADED,
  STATUS_MERGED,
  STATUS_LIVE,
  getExpertReviewBadgeVariant,
  getExpertReviewBadgeIcon,
} from "@/utils/commonUtils";
import { useCallback, useEffect, useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import MinorPatchModal from "./components/MinorPatchModal";
import MajorPatchModal from "./components/MajorPatchModal";
import {
  ConfirmDeleteModal,
  DeleteDeploymentFrameworkModal,
} from "@/components/custom/modal";
import RequestReviewModal from "./components/RequestReviewModal";
import ExpertReviewModal from "./components/ExpertReviewModal";
import {
  deleteDeploymentFrameworkPackage,
  getDeploymentFrameworkById,
  deleteDeploymentFramework,
  runAnalysis,
  mergeDeploymentFrameworkControls,
} from "@/services/deploymentFrameworkService";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { toast } from "sonner";
import DeploymentFrameworkPackageTable from "./components/custom/DeploymentFrameworkPackageTable";
import DeploymentFrameworkVersionHistoryTable from "./components/custom/DeploymentFrameworkVersionHistoryTable";
import { useAssignedFrameworks } from "@/hooks/useAssignedFrameworks";
import DeploymentFrameworkBanner from "./components/DeploymentFrameworkBanner";

import {
  getPackageViewModel,
  buildGateSteps,
  transformAssignedFrameworks,
} from "./components/helper/deploymentFrameworkHelpers";
import { useStatusPolling } from "@/hooks/useStatusPolling";

const getFileType = (document) => {
  if (document?.fileType) return document.fileType.toLowerCase();
  const extension = document?.originalFileName?.split(".").pop();
  return extension ? extension.toLowerCase() : "file";
};

const getFileTypeSummary = (documents = []) => {
  const counts = documents.reduce((summary, document) => {
    const fileType = getFileType(document);
    return { ...summary, [fileType]: (summary[fileType] || 0) + 1 };
  }, {});
  return Object.entries(counts).map(([fileType, count]) => ({
    fileType,
    count,
  }));
};

const compareVersions = (versionA = "0.0.0", versionB = "0.0.0") => {
  const partsA = versionA.split(".").map((p) => Number(p) || 0);
  const partsB = versionB.split(".").map((p) => Number(p) || 0);
  for (let i = 0; i < 3; i += 1) {
    if (partsA[i] !== partsB[i]) return partsA[i] - partsB[i];
  }
  return 0;
};

const getLatestPackage = (packages = []) =>
  [...packages].sort((a, b) =>
    compareVersions(b.packageVersion, a.packageVersion)
  )[0];

const DeploymentFrameworkDetailModals = ({
  minorPatchModalOpen,
  setMinorPatchModalOpen,
  majorPatchModalOpen,
  setMajorPatchModalOpen,
  packageToDelete,
  setPackageToDelete,
  frameworkToDelete,
  setFrameworkToDelete,
  requestReviewModalOpen,
  setRequestReviewModalOpen,
  currentPackage,
  framework,
  fetchFrameworkDetails,
  handleDeletePackage,
  handleDeleteConfirm,
}) => {
  const isCurrentPackage =
    packageToDelete?.packageVersion === framework?.currentPackageVersion;
  const isOnlyPackage = (framework?.packages?.length || 0) <= 1;
  const remainingPackages = (framework?.packages || []).filter(
    (pkg) => pkg.packageVersion !== packageToDelete?.packageVersion
  );
  const promotedPackage = getLatestPackage(remainingPackages);
  const documentsCount = packageToDelete?.documents?.length || 0;
  const fileTypeSummary = getFileTypeSummary(packageToDelete?.documents);
  const canDeletePackage = !isOnlyPackage;

  const packageBadges = packageToDelete
    ? [
      {
        text: packageToDelete.type || "package",
        className:
          "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
      },
      {
        text: packageToDelete.status || STATUS_PENDING,
        className:
          "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
      },
      ...fileTypeSummary.map(({ fileType, count }) => ({
        text: `${count} ${fileType}${count === 1 ? "" : "s"}`,
        className: "bg-background border border-border text-muted-foreground",
      })),
    ]
    : [];

  let packageWarningText = null;
  if (packageToDelete && (isCurrentPackage || isOnlyPackage)) {
    if (isOnlyPackage) {
      packageWarningText =
        "This is the only package in this framework, so it cannot be deleted here. To remove it, delete the full framework.";
    } else {
      packageWarningText = `You are deleting the current package. After deletion, package v${promotedPackage?.packageVersion} will become the current package automatically.`;
    }
  }

  return (
    <>
      <MinorPatchModal
        isOpen={minorPatchModalOpen}
        onClose={() => setMinorPatchModalOpen(false)}
        documents={currentPackage?.documents}
        framework={framework}
        onSuccess={fetchFrameworkDetails}
      />
      <MajorPatchModal
        isOpen={majorPatchModalOpen}
        onClose={() => setMajorPatchModalOpen(false)}
        framework={framework}
        onSuccess={fetchFrameworkDetails}
      />
      <RequestReviewModal
        isOpen={requestReviewModalOpen}
        onClose={() => setRequestReviewModalOpen(false)}
        frameworkId={framework?.id}
        frameworkName={framework?.frameworkName}
        packageVersion={currentPackage?.packageVersion}
        onSuccess={fetchFrameworkDetails}
      />
      {packageToDelete && (
        <ConfirmDeleteModal
          open={Boolean(packageToDelete)}
          onCancel={() => setPackageToDelete(null)}
          onConfirm={handleDeletePackage}
          title="Delete Package"
          description="Confirm deletion of deployment package. This action cannot be undone."
          bodyText="This will remove the package from the version history. Documents that are not used by another package will also be removed."
          entityIcon="document"
          entityName={`Package v${packageToDelete.packageVersion}`}
          entitySubtitle={`${documentsCount} document${documentsCount === 1 ? "" : "s"}`}
          badges={packageBadges}
          isActionDisabled={!canDeletePackage}
          warningText={packageWarningText}
        />
      )}
      {frameworkToDelete && (
        <DeleteDeploymentFrameworkModal
          open={!!frameworkToDelete}
          onCancel={() => setFrameworkToDelete(null)}
          onConfirm={handleDeleteConfirm}
          framework={frameworkToDelete}
        />
      )}
    </>
  );
};

const useDeploymentFrameworkActions = ({
  id,
  packageToDelete,
  setPackageToDelete,
  frameworkToDelete,
  setFrameworkToDelete,
  fetchFrameworkDetails,
  preReleasePackage,
  setAnalysisRunning,
  setMergeRunning,
  navigate,
}) => {
  const handleDeletePackage = async () => {
    if (!packageToDelete) return;
    try {
      const response = await deleteDeploymentFrameworkPackage(
        id,
        packageToDelete.packageVersion
      );
      toast.success(response.message || "Package deleted successfully");
      setPackageToDelete(null);
      await fetchFrameworkDetails(true);
    } catch (error) {
      console.error("Error deleting package:", error);
      toast.error(error?.message || "Failed to delete package");
    }
  };

  const handleDeleteConfirm = async () => {
    if (!frameworkToDelete) return;
    try {
      const result = await deleteDeploymentFramework(frameworkToDelete.id);
      toast.success(result.message || "Framework deleted successfully");
      setFrameworkToDelete(null);
      navigate("/deployment-frameworks");
    } catch (error) {
      console.error("Delete framework error:", error);
      toast.error(error.message || "Failed to delete framework");
    }
  };

  const handleRunAnalysis = async () => {
    try {
      setAnalysisRunning(true);
      const response = await runAnalysis(id, preReleasePackage?.packageVersion);
      if (response.success) {
        toast.success(response.message);
        await fetchFrameworkDetails(true);
      } else {
        toast.error(response.message);
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setAnalysisRunning(false);
    }
  };

  const handleMergeControls = async () => {
    try {
      setMergeRunning(true);
      const response = await mergeDeploymentFrameworkControls(
        id,
        preReleasePackage?.packageVersion
      );
      if (response.success) {
        toast.success(response.message || "Controls merged successfully");
        await fetchFrameworkDetails(true);
      } else {
        toast.error(response.message || "Failed to merge controls");
      }
    } catch (error) {
      toast.error(error.message || "An error occurred");
    } finally {
      setMergeRunning(false);
    }
  };

  return {
    handleDeletePackage,
    handleDeleteConfirm,
    handleRunAnalysis,
    handleMergeControls,
  };
};

const useFrameworkData = (id) => {
  const [loading, setLoading] = useState(true);
  const [framework, setFramework] = useState(null);

  const fetchFrameworkDetails = useCallback(
    async (isBackgroundRefresh = false) => {
      if (!isBackgroundRefresh) {
        setLoading(true);
      }
      try {
        const response = await getDeploymentFrameworkById(id);
        if (response.success) {
          setFramework(response.data);
          return response.data;
        }
      } catch (error) {
        if (!isBackgroundRefresh) {
          toast.error(error?.message || "Failed to fetch framework details");
        }
      } finally {
        setLoading(false);
      }
      return null;
    },
    [id]
  );

  useEffect(() => {
    fetchFrameworkDetails(false);
  }, [fetchFrameworkDetails]);

  return {
    loading,
    framework,
    fetchFrameworkDetails,
  };
};

const renderExpertSignOffActions = ({
  handleRunAnalysis,
  handleMergeControls,
  isAssignedFrameworkRevoked,
  isAssignedFrameworkFinalized,
  isAnalysisButtonRunning,
  isMergeButtonRunning,
  areAllDocumentsExtracted,
  isMergeCompleted,
  isAnalysisCompleted,
  isAnalysisFailed,
  setRequestReviewModalOpen,
  navigate,
  id,
  currentPackage,
  showAuditorActions,
}) => {
  const analysisButtonIcon = isAnalysisButtonRunning ? "loader" : "play";
  let analysisButtonText = "Run Analysis";
  if (isAnalysisButtonRunning) {
    analysisButtonText = "Analysis Running...";
  } else if (isAnalysisCompleted || isAnalysisFailed) {
    analysisButtonText = "Re-run Analysis";
  }

  const isCurrentPackageStatus = currentPackage?.status;
  const isCurrentPackageLive = isCurrentPackageStatus === STATUS_LIVE;

  const expertReviewStatus = currentPackage?.expertReview?.status;
  const isReviewAlreadyRequested =
    expertReviewStatus && expertReviewStatus !== STATUS_PENDING;
  const isExpertReviewApproved = expertReviewStatus === STATUS_APPROVED;

  const requestReviewTitle = isReviewAlreadyRequested
    ? `Review already ${expertReviewStatus} — cannot request again`
    : "Request an internal expert to review this package";

  return (
    <div className="flex items-center gap-2">
      {showAuditorActions && !isCurrentPackageLive && !isMergeCompleted && (
        <Button
          size="xs"
          onClick={handleMergeControls}
          disabled={
            isAssignedFrameworkRevoked ||
            !isAssignedFrameworkFinalized ||
            isMergeButtonRunning ||
            !areAllDocumentsExtracted
          }
          title="All uploaded documents must be successfully AI extracted first."
          className="mr-1"
        >
          <Icon
            name={isMergeButtonRunning ? "loader" : "git-merge"}
            size={11}
            className={`animate-${isMergeButtonRunning ? "spin" : ""}`}
          />{" "}
          {isMergeButtonRunning ? "Merging..." : "Merge Controls"}
        </Button>
      )}
      {showAuditorActions && !isCurrentPackageLive && (
        <Button
          size="xs"
          onClick={handleRunAnalysis}
          disabled={
            isAssignedFrameworkRevoked ||
            !isAssignedFrameworkFinalized ||
            isAnalysisButtonRunning ||
            !isMergeCompleted
          }
          title={
            !isMergeCompleted
              ? "Controls must be merged before running analysis."
              : "Run AI gap analysis and comparison."
          }
        >
          <Icon
            name={analysisButtonIcon}
            size={11}
            className={`animate-${isAnalysisButtonRunning ? "spin" : ""}`}
          />{" "}
          {analysisButtonText}
        </Button>
      )}
      {showAuditorActions && isAnalysisCompleted && !isExpertReviewApproved && (
        <Button
          size="xs"
          onClick={() => setRequestReviewModalOpen(true)}
          disabled={
            isAssignedFrameworkRevoked ||
            !isAssignedFrameworkFinalized ||
            isAnalysisButtonRunning ||
            isReviewAlreadyRequested
          }
          title={requestReviewTitle}
        >
          <Icon name="user-check" size={11} />{" "}
          {isReviewAlreadyRequested
            ? `Review ${expertReviewStatus}`
            : "Request Review"}
        </Button>
      )}
      <Button
        size="xs"
        onClick={() => {
          navigate(
            `/deployment-frameworks/${id}/comparison-and-gap-analysis?package-version=${currentPackage?.packageVersion}`
          );
        }}
      >
        <Icon name="eye" size={11} /> View Analysis
      </Button>
    </div>
  );
};

// ─── main component ───────────────────────────────────────────────────────────

const DeploymentFrameworkDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const showAuditorActions = isAuditor(user?.role);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [mergeRunning, setMergeRunning] = useState(false);
  const [minorPatchModalOpen, setMinorPatchModalOpen] = useState(false);
  const [majorPatchModalOpen, setMajorPatchModalOpen] = useState(false);
  const [packageToDelete, setPackageToDelete] = useState(null);
  const [frameworkToDelete, setFrameworkToDelete] = useState(null);
  const [requestReviewModalOpen, setRequestReviewModalOpen] = useState(false);
  const [expertReviewModal, setExpertReviewModal] = useState({
    open: false,
    action: null, // "approve" | "return"
  });
  const [activelyExtractingFileIds, setActivelyExtractingFileIds] = useState(
    new Set()
  );

  const { loading, framework, fetchFrameworkDetails } = useFrameworkData(id);

  const handleExtractionTriggered = useCallback((fileId) => {
    setActivelyExtractingFileIds((prev) => {
      const next = new Set(prev);
      next.add(fileId);
      return next;
    });
  }, []);

  // Reusable hook to handle dynamic breadcrumb/header title
  usePageTitle(id, "Deployment Framework Details");

  const { assignedFrameworks, loading: loadingAssignedFramework } =
    useAssignedFrameworks();

  // Transform assigned frameworks to include labels and other necessary info for display
  const assignedFramework = transformAssignedFrameworks(
    assignedFrameworks,
    framework,
    loadingAssignedFramework
  );

  const packageViewModel = getPackageViewModel(framework);
  const currentPackage = packageViewModel.currentPackage;
  const preReleasePackage = packageViewModel.preReleasePackage;
  const livePackage = packageViewModel.livePackage;
  const currentReviewPackage = packageViewModel.currentReviewPackage;

  const runningStatuses = useMemo(
    () =>
      new Set([
        STATUS_CONNECTED,
        STATUS_STARTED,
        STATUS_PROCESSING,
        STATUS_RUNNING,
      ]),
    []
  );

  const isMergeCurrentlyRunning = useMemo(() => {
    const mergeStatus = currentPackage?.mergeDocument?.status?.toLowerCase();
    return mergeRunning || runningStatuses.has(mergeStatus);
  }, [mergeRunning, currentPackage, runningStatuses]);

  const isAnalysisCurrentlyRunning = useMemo(() => {
    const comparisonStatus = currentPackage?.comparison?.status?.toLowerCase();
    const gapStatus = currentPackage?.gapAnalysis?.status?.toLowerCase();
    return (
      analysisRunning ||
      runningStatuses.has(comparisonStatus) ||
      runningStatuses.has(gapStatus)
    );
  }, [analysisRunning, currentPackage, runningStatuses]);

  useEffect(() => {
    if (!framework) return;
    const docs = preReleasePackage?.documents || [];
    setActivelyExtractingFileIds((prev) => {
      let changed = false;
      const next = new Set(prev);
      for (const fileId of prev) {
        const doc = docs.find((d) => d.fileId === fileId);
        if (
          doc &&
          (doc.aiExtraction?.status === STATUS_EXTRACTED ||
            doc.aiExtraction?.status === STATUS_FAILED)
        ) {
          next.delete(fileId);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [framework, preReleasePackage]);

  const hasDocumentsProcessing = useMemo(() => {
    const docs = preReleasePackage?.documents || [];
    return (
      docs.some(
        (doc) =>
          [STATUS_UPLOADED, STATUS_PROCESSING].includes(
            doc.aiExtraction?.status
          ) || activelyExtractingFileIds.has(doc.fileId)
      ) ?? false
    );
  }, [preReleasePackage, activelyExtractingFileIds]);

  const areAllDocumentsExtracted = useMemo(() => {
    const docs = currentPackage?.documents || [];
    if (docs.length === 0) return false;
    return docs.every((doc) => doc.aiExtraction?.status === STATUS_EXTRACTED);
  }, [currentPackage]);

  const shouldPoll =
    hasDocumentsProcessing ||
    isAnalysisCurrentlyRunning ||
    isMergeCurrentlyRunning;

  const { isTimedOut } = useStatusPolling({
    id,
    pathPattern: "/deployment-frameworks/",
    shouldPoll,
    onPoll: () => fetchFrameworkDetails(true),
    refreshTrigger: analysisRunning,
  });

  const isMergeButtonRunning = isMergeCurrentlyRunning && !isTimedOut;
  const isAnalysisButtonRunning = isAnalysisCurrentlyRunning && !isTimedOut;

  const {
    handleDeletePackage,
    handleDeleteConfirm,
    handleRunAnalysis,
    handleMergeControls,
  } = useDeploymentFrameworkActions({
    id,
    packageToDelete,
    setPackageToDelete,
    frameworkToDelete,
    setFrameworkToDelete,
    fetchFrameworkDetails,
    preReleasePackage,
    setAnalysisRunning,
    setMergeRunning,
    navigate,
  });

  const canDelete = useMemo(() => {
    const userRole = user?.role;
    const isAuthorized = isAuditor(userRole) || isCustomerAdmin(userRole);
    return isAuthorized && framework?.requestReview?.status !== STATUS_APPROVED;
  }, [user, framework]);

  if (loading) {
    return <LoadingSpinner className={"min-h-[calc(100vh-100px)]"} />;
  }

  if (!framework) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">Framework Not Found</p>
        </div>
      </div>
    );
  }

  const gateSteps = buildGateSteps(currentReviewPackage);

  const isMergeCompleted =
    currentPackage?.mergeDocument?.status === STATUS_MERGED;
  const isComparisonCompleted =
    currentPackage?.comparison?.status === STATUS_COMPLETED;
  const isGapAnalysisCompleted =
    currentPackage?.gapAnalysis?.status === STATUS_COMPLETED;
  const isCurrentPackageExpertReviewApproved =
    currentPackage?.expertReview?.status === STATUS_APPROVED;
  const isAssignedFrameworkRevoked =
    assignedFramework?.status === STATUS_REVOKED;
  const isAssignedFrameworkFinalized =
    assignedFramework?.finalization?.isFinalized === true;

  // Extracted variables for analysis button
  const isAnalysisCompleted =
    isComparisonCompleted && isGapAnalysisCompleted && isMergeCompleted;
  const isAnalysisFailed =
    currentPackage?.comparison?.status === STATUS_FAILED ||
    currentPackage?.gapAnalysis?.status === STATUS_FAILED ||
    currentPackage?.mergeDocument?.status === STATUS_FAILED;

  return (
    <div className="space-y-2 my-2">
      {/* ── Revoked Banner ── */}
      <DeploymentFrameworkBanner assignedFramework={assignedFramework} />

      {/* ── 3 stat cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* framework */}
        <Link
          to={`/assigned-frameworks/${framework?.assignedFramework?.id}`}
          className="bg-card border border-border rounded p-4 border-t-3 border-t-primary group"
        >
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
            Framework
          </p>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded bg-primary shrink-0" />
            <span className="text-base font-bold text-foreground group-hover:underline">
              {framework?.frameworkName}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            {framework?.frameworkVersion} · Active Standard
          </p>
        </Link>
        {/* current version */}
        <div className="bg-card border border-border rounded p-4 border-t-3 border-t-amber-400">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
            Current Package Version
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="w-2 h-2 rounded bg-amber-400 shrink-0" />
            <span className="text-base font-bold text-foreground">
              v{preReleasePackage?.packageVersion}
            </span>
            <Badge variant="amber" className="capitalize">
              {preReleasePackage?.type}
            </Badge>
            {preReleasePackage?.expertReview?.status &&
              preReleasePackage.expertReview.status !== STATUS_PENDING && (
                <Badge
                  variant={getExpertReviewBadgeVariant(
                    preReleasePackage.expertReview.status
                  )}
                  className="capitalize"
                >
                  <Icon
                    name={getExpertReviewBadgeIcon(
                      preReleasePackage.expertReview.status
                    )}
                    size={10}
                  />{" "}
                  {preReleasePackage.expertReview.status}
                </Badge>
              )}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            {preReleasePackage?.documents?.length || 0} documents uploaded
          </p>
        </div>
        {/* last deployed */}
        <div className="bg-card border border-border rounded p-4 border-t-3 border-t-green-500">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">
            Last Deployed Version
          </p>
          {livePackage?.createdAt ? (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="w-2 h-2 rounded bg-green-500 shrink-0" />
                <span className="text-base font-bold text-foreground">
                  v{livePackage?.packageVersion}
                </span>
                <Badge variant="green">Live</Badge>
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Deployed on{" "}
                {formatDateWithMonthNameAndTime(livePackage?.createdAt)}
              </p>
            </>
          ) : (
            <Badge variant="amber">Not deployed yet</Badge>
          )}
        </div>
      </div>

      {/* ── replicate bar ── */}
      <div className="rounded flex flex-wrap items-center justify-between gap-3 bg-muted/20 border border-border p-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-slate-200 dark:bg-slate-800 rounded flex items-center justify-center text-primary shrink-0">
            <Icon name="copy" size={18} />
          </div>
          <div>
            <p className="text-sm font-semibold">
              Replicate Deployment Package
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Minor patch carries all existing documents forward — replace only
              what changed, or add more. Major version starts completely fresh.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {showAuditorActions && (
            <>
              <Button
                size="xs"
                onClick={() => setMinorPatchModalOpen(true)}
                disabled={
                  isAssignedFrameworkRevoked || !isAssignedFrameworkFinalized
                }
              >
                <Icon name="git" size={13} /> Minor Patch
              </Button>
              <Button
                size="xs"
                onClick={() => setMajorPatchModalOpen(true)}
                disabled={
                  isAssignedFrameworkRevoked || !isAssignedFrameworkFinalized
                }
              >
                <Icon name="rocket" size={13} /> Major Version
              </Button>
            </>
          )}
          {canDelete && (
            <Button
              variant="destructive"
              size="xs"
              onClick={() => setFrameworkToDelete(framework)}
              className="gap-2"
            >
              <Icon name="trash" size={13} /> Delete Framework
            </Button>
          )}
          <Button
            variant="default"
            size="xs"
            onClick={() => navigate("/deployment-frameworks")}
            className="gap-2"
          >
            <Icon name="arrow-left" size={13} /> Back
          </Button>
        </div>
      </div>

      {/* ── deployment package table ── */}
      <div className="bg-card border border-border rounded p-2">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Icon name="folder" size="16px" className="text-primary" />
              Deployment Package
            </h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {preReleasePackage?.documents?.length || 0} documents · Current
              version:{" "}
              <strong>v{preReleasePackage?.packageVersion || "N/A"}</strong>
            </p>
          </div>
          <div className="flex flex-col gap-0">
            <p className="text-xs text-muted-foreground text-right">
              Last updated:{" "}
              {preReleasePackage?.updatedAt
                ? formatDateWithMonthNameAndTime(preReleasePackage.updatedAt)
                : "N/A"}
            </p>
            {showAuditorActions && (
              <Button
                variant="link"
                size="xs"
                onClick={() => setMinorPatchModalOpen(true)}
                className="flex items-center gap-1.5 text-[12px] text-primary"
                disabled={
                  isAssignedFrameworkRevoked || !isAssignedFrameworkFinalized
                }
              >
                <Icon name="plus" size={13} /> Upload another document
              </Button>
            )}
          </div>
        </div>

        <DeploymentFrameworkPackageTable
          preReleasePackage={preReleasePackage}
          frameworkId={framework?.id}
          showActions={showAuditorActions}
          onExtractionTriggered={handleExtractionTriggered}
          onSuccess={() => fetchFrameworkDetails(true)}
        />
      </div>

      {/* sign off */}
      <div className="bg-card border border-border rounded p-4">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            🏅 Sign-off Gate
          </h2>
          {renderExpertSignOffActions({
            isCurrentPackageExpertReviewApproved,
            handleRunAnalysis,
            handleMergeControls,
            isAssignedFrameworkRevoked,
            isAssignedFrameworkFinalized,
            isAnalysisButtonRunning,
            isMergeButtonRunning,
            areAllDocumentsExtracted,
            isMergeCompleted,
            isAnalysisCompleted,
            isAnalysisFailed,
            setRequestReviewModalOpen,
            navigate,
            id,
            currentPackage,
            showAuditorActions,
          })}
        </div>
        <p className="text-[11px] text-muted-foreground mb-4">
          No version is deployed without explicit expert approval
        </p>

        {(() => {
          const lastCompletedIndex = [...gateSteps]
            .reverse()
            .findIndex((s) => s.status === STATUS_DONE);
          const activeIndex =
            lastCompletedIndex === -1
              ? -1
              : gateSteps.length - 1 - lastCompletedIndex;
          const progressPercent =
            activeIndex === -1
              ? 0
              : (activeIndex / (gateSteps.length - 1)) * 100;
          const activeStep =
            gateSteps.find(
              (s) =>
                s.status === STATUS_PENDING || s.status === STATUS_FAILED
            ) ||
            gateSteps.find(
              (s) =>
                s.status === STATUS_DONE &&
                s.title.toLowerCase().includes("deploy")
            ) ||
            gateSteps[0];

          return (
            <div className="space-y-3">
              {/* Stepper container */}
              <div className="relative flex items-center justify-between w-full px-2 py-3 bg-muted/10 dark:bg-muted/5 border border-border/50 rounded">
                {/* Background progress line */}
                <div className="absolute left-7.5 right-7.5 top-6 h-0.5 z-0">
                  <div className="w-full h-full bg-muted dark:bg-muted/30 rounded-full" />
                  <div
                    className="absolute top-0 left-0 h-full bg-green-500 rounded-full transition-all duration-500 ease-in-out"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>

                {gateSteps.map((step, i) => {
                  const cleanTitle = step.title
                    .replace("AI ", "")
                    .replace(" Completed", "")
                    .replace(" Running", "")
                    .replace(" Pending", "");

                  return (
                    <div
                      key={step.title}
                      className="flex flex-col items-center relative z-10 flex-1"
                    >
                      <TooltipProvider delayDuration={100}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div
                              className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold border-2 border-background dark:border-card cursor-pointer transition-all duration-200 hover:scale-110 shadow-sm
                                    ${step.status === STATUS_DONE ? "bg-green-500 text-white" : ""}
                                    ${step.status === STATUS_PENDING ? "bg-amber-400 text-white animate-pulse" : ""}
                                    ${step.status === STATUS_FAILED ? "bg-rose-500 text-white animate-bounce" : ""}
                                    ${step.status === STATUS_LOCKED ? "bg-muted text-muted-foreground border-border" : ""}
                                  `}
                            >
                              {step.status === STATUS_DONE && (
                                <Icon name="check" size={10} />
                              )}
                              {step.status === STATUS_PENDING && (
                                <Icon name="clock" size={10} />
                              )}
                              {step.status === STATUS_FAILED && (
                                <Icon name="x" size={10} />
                              )}
                              {step.status === STATUS_LOCKED && i + 1}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent className="bg-primary text-background border border-border p-2 w-70 text-wrap text-xs shadow-md [&_svg]:fill-primary [&_svg]:bg-primary">
                            <p className="font-semibold text-[11px] text-background mb-0.5">
                              {step.title}
                            </p>
                            <p className="text-[10px] text-background/85 leading-normal">
                              {step.desc}
                            </p>
                            {step.meta && (
                              <p className="text-[10px] font-medium text-background/65 mt-1">
                                {step.meta}
                              </p>
                            )}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>

                      <span
                        className={`text-[9px] font-semibold text-center mt-1.5 max-w-21.25 leading-tight block truncate
                              ${step.status === STATUS_LOCKED ? "text-muted-foreground/80" : "text-foreground"}
                            `}
                      >
                        {cleanTitle}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Active step details box */}
              {activeStep && (
                <div
                  className={`p-2.5 rounded border text-[11px] flex items-start gap-2.5 transition-all duration-300
                        ${activeStep.status === STATUS_DONE ? "bg-green-500/5 border-green-500/25 text-foreground" : ""}
                        ${activeStep.status === STATUS_PENDING ? "bg-amber-500/5 border-amber-500/25 text-foreground shadow-xs" : ""}
                        ${activeStep.status === STATUS_FAILED ? "bg-rose-500/5 border-rose-500/25 text-foreground" : ""}
                      `}
                >
                  <div className="shrink-0 mt-0.5">
                    {activeStep.status === STATUS_DONE && (
                      <Icon
                        name="check"
                        size={13}
                        className="text-green-500"
                      />
                    )}
                    {activeStep.status === STATUS_PENDING && (
                      <Icon
                        name="clock"
                        size={13}
                        className="text-amber-500 animate-pulse"
                      />
                    )}
                    {activeStep.status === STATUS_FAILED && (
                      <Icon name="x" size={13} className="text-rose-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="font-semibold text-foreground">
                      {activeStep.title}
                    </span>
                    <span className="text-muted-foreground ml-1.5">
                      — {activeStep.desc}
                    </span>
                    {activeStep.meta && (
                      <p className="text-muted-foreground text-[10px] font-medium mt-0.5">
                        {activeStep.meta}
                      </p>
                    )}
                    {activeStep.comment && (
                      <div className="mt-2 p-2 bg-rose-500/10 border border-rose-500/20 rounded text-rose-800 dark:text-rose-300">
                        <span className="font-semibold block mb-0.5">Expert Comment:</span>
                        <span className="italic">{activeStep.comment}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* action required box */}
        {isInternalExpert(user?.role) &&
          currentReviewPackage?.expertReview?.status === "requested" && (
            <div className="mt-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded p-3">
              <p className="text-[12px] font-semibold text-amber-700 dark:text-amber-400 flex items-center gap-1.5 mb-1.5">
                <Icon name="alert" size={13} /> Expert Action Required
              </p>
              <p className="text-[11px] text-muted-foreground mb-3">
                Review gap analysis and confirm or reject this deployment
                package version.
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="default"
                  size="xs"
                  onClick={() =>
                    setExpertReviewModal({ open: true, action: "approve" })
                  }
                >
                  <Icon name="check" size={12} /> Approve
                </Button>
                <Button
                  variant="destructive"
                  size="xs"
                  onClick={() =>
                    setExpertReviewModal({ open: true, action: "return" })
                  }
                >
                  <Icon name="x" size={12} /> Return
                </Button>
              </div>
            </div>
          )}
      </div>

      {/* ── version history ── */}
      <div className="bg-card border border-border rounded p-2">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Icon name="history" size={15} /> Version History
              </h2>
              <Badge variant="blue">
                {framework?.packages?.length || 0} versions
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Review and manage previous versions of this deployment
              framework. Statuses:{" "}
              <span className="text-primary font-bold">Pending</span> (under
              review),{" "}
              <span className="text-primary font-bold">Returned</span>{" "}
              (changes requested),{" "}
              <span className="text-primary font-bold">Live</span>{" "}
              (currently active), and{" "}
              <span className="text-primary font-bold">Superseded</span>{" "}
              (replaced by a newer version).
            </p>
          </div>
        </div>

        <DeploymentFrameworkVersionHistoryTable
          framework={framework}
          setPackageToDelete={setPackageToDelete}
          currentPackage={currentPackage}
        />
      </div>

      <DeploymentFrameworkDetailModals
        minorPatchModalOpen={minorPatchModalOpen}
        setMinorPatchModalOpen={setMinorPatchModalOpen}
        majorPatchModalOpen={majorPatchModalOpen}
        setMajorPatchModalOpen={setMajorPatchModalOpen}
        packageToDelete={packageToDelete}
        setPackageToDelete={setPackageToDelete}
        frameworkToDelete={frameworkToDelete}
        setFrameworkToDelete={setFrameworkToDelete}
        requestReviewModalOpen={requestReviewModalOpen}
        setRequestReviewModalOpen={setRequestReviewModalOpen}
        currentPackage={currentPackage}
        framework={framework}
        fetchFrameworkDetails={fetchFrameworkDetails}
        handleDeletePackage={handleDeletePackage}
        handleDeleteConfirm={handleDeleteConfirm}
      />

      <ExpertReviewModal
        isOpen={expertReviewModal.open}
        onClose={() => setExpertReviewModal({ open: false, action: null })}
        action={expertReviewModal.action}
        frameworkId={framework?.id}
        packageVersion={currentReviewPackage?.packageVersion}
        packageData={currentReviewPackage}
        onSuccess={() => fetchFrameworkDetails(false)}
      />
    </div>
  );
};

export default DeploymentFrameworkDetail;
