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

const AnalysisActions = ({
  frameworkId,
  currentPackage,
  isAssignedFrameworkRevoked,
  isAssignedFrameworkFinalized,
  viewContext, // "detail" | "controls-tab" | "comparison-tab" | "gap-tab"
  onRefresh,
  setRequestReviewModalOpen,
}) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const showAuditorActions = isAuditor(user?.role);

  const [mergeRunning, setMergeRunning] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [comparisonRunning, setComparisonRunning] = useState(false);
  const [gapAnalysisRunning, setGapAnalysisRunning] = useState(false);

  const isMergeProcessing =
    currentPackage?.mergeDocument?.status === STATUS_PROCESSING;
  const isComparisonProcessing =
    currentPackage?.comparison?.status === STATUS_PROCESSING;
  const isGapAnalysisProcessing =
    currentPackage?.gapAnalysis?.status === STATUS_PROCESSING;

  const isMergeCurrentlyRunning = mergeRunning || isMergeProcessing;
  const isComparisonCurrentlyRunning =
    comparisonRunning || isComparisonProcessing;
  const isGapAnalysisCurrentlyRunning =
    gapAnalysisRunning || isGapAnalysisProcessing;
  const isAnalysisCurrentlyRunning =
    analysisRunning || isComparisonProcessing || isGapAnalysisProcessing;

  const areAllDocumentsExtracted = useMemo(() => {
    const docs = currentPackage?.documents || [];
    if (docs.length === 0) return true; // allow merge if no docs
    return docs.every((doc) => doc.aiExtraction?.status === STATUS_EXTRACTED);
  }, [currentPackage]);

  const isCurrentPackageLive = currentPackage?.status === STATUS_LIVE;
  const isMergeCompleted =
    currentPackage?.mergeDocument?.status === STATUS_MERGED;
  const isComparisonCompleted =
    currentPackage?.comparison?.status === STATUS_COMPLETED;
  const isGapAnalysisCompleted =
    currentPackage?.gapAnalysis?.status === STATUS_COMPLETED;
  const isAnalysisFailed =
    currentPackage?.comparison?.status === STATUS_FAILED ||
    currentPackage?.gapAnalysis?.status === STATUS_FAILED ||
    currentPackage?.mergeDocument?.status === STATUS_FAILED;

  const isAnalysisCompleted =
    isComparisonCompleted && isGapAnalysisCompleted && isMergeCompleted;
  const expertReviewStatus = currentPackage?.expertReview?.status;
  const isReviewAlreadyRequested =
    expertReviewStatus && expertReviewStatus !== STATUS_PENDING;
  const isExpertReviewApproved = expertReviewStatus === STATUS_APPROVED;

  const handleMergeControls = async () => {
    try {
      setMergeRunning(true);
      const response = await mergeDeploymentFrameworkControls(
        frameworkId,
        currentPackage?.packageVersion
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
      const response = await runAnalysis(
        frameworkId,
        currentPackage?.packageVersion
      );
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
      const response = await runComparison(
        frameworkId,
        currentPackage?.packageVersion
      );
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
      const response = await runGapAnalysis(
        frameworkId,
        currentPackage?.packageVersion
      );
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

  if (!showAuditorActions) {
    if (viewContext === "detail") {
      return (
        <div className="flex items-center gap-2">
          <Button
            size="xs"
            onClick={() => {
              navigate(
                `/deployment-frameworks/${frameworkId}/comparison-and-gap-analysis?package-version=${currentPackage?.packageVersion}`
              );
            }}
          >
            <Icon name="eye" size={11} /> View Analysis
          </Button>
        </div>
      );
    }
    return null;
  }

  const renderMergeButton = () => {
    if (isCurrentPackageLive || isMergeCompleted) return null;

    // In detail view, apply strict validations. In tabs, be more permissive.
    const isDisabled =
      viewContext === "detail"
        ? isAssignedFrameworkRevoked ||
          !isAssignedFrameworkFinalized ||
          isMergeCurrentlyRunning ||
          !areAllDocumentsExtracted
        : isMergeCurrentlyRunning || !areAllDocumentsExtracted;

    return (
      <Button
        size="xs"
        onClick={handleMergeControls}
        disabled={isDisabled}
        title={
          !areAllDocumentsExtracted
            ? "All uploaded documents must be successfully AI extracted first."
            : "Merge Controls"
        }
        className="mr-1"
      >
        <Icon
          name={isMergeCurrentlyRunning ? "loader" : "git-merge"}
          size={11}
          className={`animate-${isMergeCurrentlyRunning ? "spin" : ""}`}
        />{" "}
        {isMergeCurrentlyRunning ? "Merging..." : "Merge Controls"}
      </Button>
    );
  };

  if (viewContext === "detail") {
    let analysisButtonText = "Run Analysis";
    if (isAnalysisCurrentlyRunning) {
      analysisButtonText = "Analysis Running...";
    } else if (isAnalysisCompleted || isAnalysisFailed) {
      analysisButtonText = "Re-run Analysis";
    }

    const requestReviewTitle = isReviewAlreadyRequested
      ? `Review already ${expertReviewStatus} — cannot request again`
      : "Request an internal expert to review this package";

    return (
      <div className="flex items-center gap-2">
        {renderMergeButton()}
        {!isCurrentPackageLive && (
          <Button
            size="xs"
            onClick={handleRunAnalysis}
            disabled={
              isAssignedFrameworkRevoked ||
              !isAssignedFrameworkFinalized ||
              isAnalysisCurrentlyRunning ||
              !isMergeCompleted
            }
            title={
              !isMergeCompleted
                ? "Controls must be merged before running analysis."
                : "Run AI gap analysis and comparison."
            }
          >
            <Icon
              name={isAnalysisCurrentlyRunning ? "loader" : "play"}
              size={11}
              className={`animate-${isAnalysisCurrentlyRunning ? "spin" : ""}`}
            />{" "}
            {analysisButtonText}
          </Button>
        )}
        {isAnalysisCompleted &&
          !isExpertReviewApproved &&
          setRequestReviewModalOpen && (
            <Button
              size="xs"
              onClick={() => setRequestReviewModalOpen(true)}
              disabled={
                isAssignedFrameworkRevoked ||
                !isAssignedFrameworkFinalized ||
                isAnalysisCurrentlyRunning ||
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
              `/deployment-frameworks/${frameworkId}/comparison-and-gap-analysis?package-version=${currentPackage?.packageVersion}`
            );
          }}
        >
          <Icon name="eye" size={11} /> View Analysis
        </Button>
      </div>
    );
  }

  if (viewContext === "controls-tab") {
    return <div className="flex items-center gap-2">{renderMergeButton()}</div>;
  }

  if (viewContext === "comparison-tab") {
    if (isCurrentPackageLive) return null;
    let comparisonBtnText = "Run Comparison";
    if (isComparisonCurrentlyRunning) comparisonBtnText = "Running...";
    else if (
      isComparisonCompleted ||
      currentPackage?.comparison?.status === STATUS_FAILED
    )
      comparisonBtnText = "Re-run Comparison";
    return (
      <div className="flex items-center gap-2">
        <Button
          size="xs"
          onClick={handleRunComparison}
          disabled={isComparisonCurrentlyRunning}
          title={"Run Comparison"}
        >
          <Icon
            name={isComparisonCurrentlyRunning ? "loader" : "play"}
            size={11}
            className={`animate-${isComparisonCurrentlyRunning ? "spin" : ""}`}
          />{" "}
          {comparisonBtnText}
        </Button>
      </div>
    );
  }

  if (viewContext === "gap-tab") {
    if (isCurrentPackageLive) return null;
    let gapBtnText = "Run Gap Analysis";
    if (isGapAnalysisCurrentlyRunning) gapBtnText = "Running...";
    else if (
      isGapAnalysisCompleted ||
      currentPackage?.gapAnalysis?.status === STATUS_FAILED
    )
      gapBtnText = "Re-run Gap Analysis";
    return (
      <div className="flex items-center gap-2">
        <Button
          size="xs"
          onClick={handleRunGapAnalysis}
          disabled={isGapAnalysisCurrentlyRunning}
          title={"Run Gap Analysis"}
        >
          <Icon
            name={isGapAnalysisCurrentlyRunning ? "loader" : "play"}
            size={11}
            className={`animate-${isGapAnalysisCurrentlyRunning ? "spin" : ""}`}
          />{" "}
          {gapBtnText}
        </Button>
      </div>
    );
  }

  return null;
};

export default AnalysisActions;
