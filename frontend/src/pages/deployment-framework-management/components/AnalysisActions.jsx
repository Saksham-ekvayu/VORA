import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import Icon from "@/components/custom/Icon";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/authContext/useAuth";
import {
  isAuditor,
  STATUS_EXTRACTED,
  STATUS_PENDING,
  STATUS_APPROVED,
  STATUS_MERGED,
  STATUS_COMPLETED,
  STATUS_FAILED,
  STATUS_LIVE,
  STATUS_PROCESSING,
} from "@/utils/commonUtils";
import {
  mergeDeploymentFrameworkControls,
  runAnalysis,
  runComparison,
  runGapAnalysis,
} from "@/services/deploymentFrameworkService";

// --- Hook for API calls ---
const useAnalysisOperations = (frameworkId, packageVersion, onRefresh) => {
  const [mergeRunning, setMergeRunning] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [comparisonRunning, setComparisonRunning] = useState(false);
  const [gapAnalysisRunning, setGapAnalysisRunning] = useState(false);

  const handleMergeControls = async () => {
    try {
      setMergeRunning(true);
      const response = await mergeDeploymentFrameworkControls(
        frameworkId,
        packageVersion
      );
      if (response.success) {
        toast.success(response.message || "Controls merged successfully");
        if (onRefresh) onRefresh();
      } else {
        toast.error(response.message || "Failed to merge controls");
      }
    } catch (error) {
      toast.error(error.message || "An error occurred");
    } finally {
      setMergeRunning(false);
    }
  };

  const handleRunAnalysis = async () => {
    try {
      setAnalysisRunning(true);
      const response = await runAnalysis(frameworkId, packageVersion);
      if (response.success) {
        toast.success(response.message);
        if (onRefresh) onRefresh();
      } else {
        toast.error(response.message);
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setAnalysisRunning(false);
    }
  };

  const handleRunComparison = async () => {
    try {
      setComparisonRunning(true);
      const response = await runComparison(frameworkId, packageVersion);
      if (response.success) {
        toast.success(response.message);
        if (onRefresh) onRefresh();
      } else {
        toast.error(response.message);
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setComparisonRunning(false);
    }
  };

  const handleRunGapAnalysis = async () => {
    try {
      setGapAnalysisRunning(true);
      const response = await runGapAnalysis(frameworkId, packageVersion);
      if (response.success) {
        toast.success(response.message);
        if (onRefresh) onRefresh();
      } else {
        toast.error(response.message);
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setGapAnalysisRunning(false);
    }
  };

  return {
    mergeRunning,
    analysisRunning,
    comparisonRunning,
    gapAnalysisRunning,
    handleMergeControls,
    handleRunAnalysis,
    handleRunComparison,
    handleRunGapAnalysis,
  };
};

// --- Sub-components for specific views ---

const MergeButton = ({ state, onMerge }) => {
  if (state.isCurrentPackageLive) return null;

  let mergeBtnText = "Merge Controls";
  if (state.isMergeCurrentlyRunning) mergeBtnText = "Merging...";
  else if (state.isMergeCompleted || state.isMergeFailed)
    mergeBtnText = "Re-run Merge";

  const isDisabled =
    state.viewContext === "detail"
      ? state.isAssignedFrameworkRevoked ||
        !state.isAssignedFrameworkFinalized ||
        state.isMergeCurrentlyRunning ||
        !state.areAllDocumentsExtracted
      : state.isMergeCurrentlyRunning || !state.areAllDocumentsExtracted;

  return (
    <Button
      size="xs"
      onClick={onMerge}
      disabled={isDisabled}
      title={
        !state.areAllDocumentsExtracted
          ? "All uploaded documents must be successfully AI extracted first."
          : mergeBtnText
      }
      className="mr-1"
    >
      <Icon
        name={state.isMergeCurrentlyRunning ? "loader" : "git-merge"}
        size={11}
        className={`animate-${state.isMergeCurrentlyRunning ? "spin" : ""}`}
      />{" "}
      {mergeBtnText}
    </Button>
  );
};

const DetailViewActions = ({ state, actions }) => {
  let analysisButtonText = "Run Analysis";
  if (state.isAnalysisCurrentlyRunning) {
    analysisButtonText = "Analysis Running...";
  } else if (state.isAnalysisCompleted || state.isAnalysisFailed) {
    analysisButtonText = "Re-run Analysis";
  }

  const requestReviewTitle = state.isReviewAlreadyRequested
    ? `Review already ${state.expertReviewStatus} — cannot request again`
    : "Request an internal expert to review this package";

  return (
    <div className="flex items-center gap-2">
      <MergeButton state={state} onMerge={actions.handleMergeControls} />
      {!state.isCurrentPackageLive && (
        <Button
          size="xs"
          onClick={actions.handleRunAnalysis}
          disabled={
            state.isAssignedFrameworkRevoked ||
            !state.isAssignedFrameworkFinalized ||
            state.isAnalysisCurrentlyRunning ||
            !state.isMergeCompleted
          }
          title={
            !state.isMergeCompleted
              ? "Controls must be merged before running analysis."
              : "Run AI gap analysis and comparison."
          }
        >
          <Icon
            name={state.isAnalysisCurrentlyRunning ? "loader" : "play"}
            size={11}
            className={`animate-${state.isAnalysisCurrentlyRunning ? "spin" : ""}`}
          />{" "}
          {analysisButtonText}
        </Button>
      )}
      {state.isAnalysisCompleted &&
        !state.isExpertReviewApproved &&
        state.setRequestReviewModalOpen && (
          <Button
            size="xs"
            onClick={() => state.setRequestReviewModalOpen(true)}
            disabled={
              state.isAssignedFrameworkRevoked ||
              !state.isAssignedFrameworkFinalized ||
              state.isAnalysisCurrentlyRunning ||
              state.isReviewAlreadyRequested
            }
            title={requestReviewTitle}
          >
            <Icon name="user-check" size={11} />{" "}
            {state.isReviewAlreadyRequested
              ? `Review ${state.expertReviewStatus}`
              : "Request Review"}
          </Button>
        )}
      <Button
        size="xs"
        onClick={() => {
          actions.navigate(
            `/deployment-frameworks/${state.frameworkId}/comparison-and-gap-analysis?package-version=${state.packageVersion}`
          );
        }}
      >
        <Icon name="eye" size={11} /> View Analysis
      </Button>
    </div>
  );
};

const ComparisonTabActions = ({ state, actions }) => {
  if (state.isCurrentPackageLive) return null;
  let comparisonBtnText = "Run Comparison";
  if (state.isComparisonCurrentlyRunning) comparisonBtnText = "Running...";
  else if (state.isComparisonCompleted || state.isComparisonFailed)
    comparisonBtnText = "Re-run Comparison";

  return (
    <div className="flex items-center gap-2">
      <Button
        size="xs"
        onClick={actions.handleRunComparison}
        disabled={state.isComparisonCurrentlyRunning}
        title="Run Comparison"
      >
        <Icon
          name={state.isComparisonCurrentlyRunning ? "loader" : "play"}
          size={11}
          className={`animate-${state.isComparisonCurrentlyRunning ? "spin" : ""}`}
        />{" "}
        {comparisonBtnText}
      </Button>
    </div>
  );
};

const GapTabActions = ({ state, actions }) => {
  if (state.isCurrentPackageLive) return null;
  let gapBtnText = "Run Gap Analysis";
  if (state.isGapAnalysisCurrentlyRunning) gapBtnText = "Running...";
  else if (state.isGapAnalysisCompleted || state.isGapAnalysisFailed)
    gapBtnText = "Re-run Gap Analysis";

  return (
    <div className="flex items-center gap-2">
      <Button
        size="xs"
        onClick={actions.handleRunGapAnalysis}
        disabled={state.isGapAnalysisCurrentlyRunning}
        title="Run Gap Analysis"
      >
        <Icon
          name={state.isGapAnalysisCurrentlyRunning ? "loader" : "play"}
          size={11}
          className={`animate-${state.isGapAnalysisCurrentlyRunning ? "spin" : ""}`}
        />{" "}
        {gapBtnText}
      </Button>
    </div>
  );
};

// --- Main Component ---
const AnalysisActions = ({
  frameworkId,
  currentPackage,
  isAssignedFrameworkRevoked,
  isAssignedFrameworkFinalized,
  viewContext,
  onRefresh,
  setRequestReviewModalOpen,
}) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const showAuditorActions = isAuditor(user?.role);

  const ops = useAnalysisOperations(
    frameworkId,
    currentPackage?.packageVersion,
    onRefresh
  );

  const isMergeProcessing =
    currentPackage?.mergeDocument?.status === STATUS_PROCESSING;
  const isComparisonProcessing =
    currentPackage?.comparison?.status === STATUS_PROCESSING;
  const isGapAnalysisProcessing =
    currentPackage?.gapAnalysis?.status === STATUS_PROCESSING;

  const isMergeCurrentlyRunning = ops.mergeRunning || isMergeProcessing;
  const isComparisonCurrentlyRunning =
    ops.comparisonRunning || isComparisonProcessing;
  const isGapAnalysisCurrentlyRunning =
    ops.gapAnalysisRunning || isGapAnalysisProcessing;
  const isAnalysisCurrentlyRunning =
    ops.analysisRunning || isComparisonProcessing || isGapAnalysisProcessing;

  const areAllDocumentsExtracted = useMemo(() => {
    const docs = currentPackage?.documents || [];
    if (docs.length === 0) return true;
    return docs.every((doc) => doc.aiExtraction?.status === STATUS_EXTRACTED);
  }, [currentPackage]);

  const expertReviewStatus = currentPackage?.expertReview?.status;

  const state = {
    viewContext,
    frameworkId,
    packageVersion: currentPackage?.packageVersion,
    isAssignedFrameworkRevoked,
    isAssignedFrameworkFinalized,
    setRequestReviewModalOpen,
    isCurrentPackageLive: currentPackage?.status === STATUS_LIVE,
    isMergeCompleted: currentPackage?.mergeDocument?.status === STATUS_MERGED,
    isMergeFailed: currentPackage?.mergeDocument?.status === STATUS_FAILED,
    isComparisonCompleted:
      currentPackage?.comparison?.status === STATUS_COMPLETED,
    isGapAnalysisCompleted:
      currentPackage?.gapAnalysis?.status === STATUS_COMPLETED,
    isComparisonFailed: currentPackage?.comparison?.status === STATUS_FAILED,
    isGapAnalysisFailed: currentPackage?.gapAnalysis?.status === STATUS_FAILED,
    isAnalysisFailed:
      currentPackage?.comparison?.status === STATUS_FAILED ||
      currentPackage?.gapAnalysis?.status === STATUS_FAILED ||
      currentPackage?.mergeDocument?.status === STATUS_FAILED,
    isMergeCurrentlyRunning,
    isComparisonCurrentlyRunning,
    isGapAnalysisCurrentlyRunning,
    isAnalysisCurrentlyRunning,
    areAllDocumentsExtracted,
    expertReviewStatus,
    isReviewAlreadyRequested:
      expertReviewStatus && expertReviewStatus !== STATUS_PENDING,
    isExpertReviewApproved: expertReviewStatus === STATUS_APPROVED,
  };

  state.isAnalysisCompleted =
    state.isComparisonCompleted &&
    state.isGapAnalysisCompleted &&
    state.isMergeCompleted;

  const actions = { ...ops, navigate };

  if (!showAuditorActions) {
    if (viewContext === "detail") {
      return (
        <div className="flex items-center gap-2">
          <Button
            size="xs"
            onClick={() =>
              navigate(
                `/deployment-frameworks/${frameworkId}/comparison-and-gap-analysis?package-version=${currentPackage?.packageVersion}`
              )
            }
          >
            <Icon name="eye" size={11} /> View Analysis
          </Button>
        </div>
      );
    }
    return null;
  }

  switch (viewContext) {
    case "detail":
      return <DetailViewActions state={state} actions={actions} />;
    case "controls-tab":
      return (
        <div className="flex items-center gap-2">
          <MergeButton state={state} onMerge={actions.handleMergeControls} />
        </div>
      );
    case "comparison-tab":
      return <ComparisonTabActions state={state} actions={actions} />;
    case "gap-tab":
      return <GapTabActions state={state} actions={actions} />;
    default:
      return null;
  }
};

export default AnalysisActions;
