/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { useModalState } from "@/hooks/useModalState";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import { getFrameworkById } from "@/services/frameworkService";
import {
  compareFrameworks,
  analyzeDeploymentGap,
} from "@/services/deploymentFrameworkService";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";

// Helper function to render framework loading/content
const renderFrameworkContent = (
  loadingFramework,
  frameworkDetail,
  frameworkJobId
) => {
  if (loadingFramework) {
    return (
      <div className="flex items-center gap-2 py-2">
        <div className="w-4 h-4 border-2 border-border border-t-primary rounded-full animate-spin" />
        <span className="text-sm text-muted-foreground">
          Loading framework details...
        </span>
      </div>
    );
  }

  if (frameworkDetail) {
    return (
      <>
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-sm text-foreground">
            {frameworkDetail.frameworkName}
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-secondary/15 text-secondary uppercase">
            {frameworkDetail.frameworkCode}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>v{frameworkDetail.currentFileVersion}</span>
          <span>•</span>
          <span>{frameworkDetail.frameworkVersion}</span>
          {frameworkJobId ? (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-500/15 text-green-600 dark:text-green-400">
              AI Ready
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/15 text-red-600">
              AI Not Ready
            </span>
          )}
        </div>
      </>
    );
  }

  return (
    <p className="text-sm text-muted-foreground">
      Framework details not available
    </p>
  );
};

export default function CompareFrameworkModal({
  isOpen,
  onClose,
  onSuccess,
  deploymentFramework,
  mode = "compare", // "compare" or "deploymentGap"
}) {
  const [frameworkDetail, setFrameworkDetail] = useState(null);
  const [loadingFramework, setLoadingFramework] = useState(false);
  const { loading: comparing, setLoading: setComparing } = useModalState();

  const isDeploymentGap = mode === "deploymentGap";
  const actionText = isDeploymentGap ? "Analyze" : "Compare";
  const actioningText = isDeploymentGap ? "Analyzing" : "Comparing";
  const headerTitle = isDeploymentGap
    ? "Deployment Gap Analysis"
    : "Compare Framework";
  const buttonText = isDeploymentGap
    ? "Analyze Deployment Gap"
    : "Compare Frameworks";

  // Fetch framework detail using frameworkId from deploymentFramework
  useEffect(() => {
    if (!isOpen || !deploymentFramework?.frameworkId) return;

    const fetchFramework = async () => {
      try {
        setLoadingFramework(true);
        const response = await getFrameworkById(
          deploymentFramework.frameworkId
        );
        if (response.success) {
          setFrameworkDetail(response.data);
        }
      } catch (error) {
        toast.error(error.message || "Failed to fetch framework details");
      } finally {
        setLoadingFramework(false);
      }
    };

    fetchFramework();
  }, [isOpen, deploymentFramework?.frameworkId]);

  // Get job_id from current version of the fetched framework
  const getFrameworkJobId = () => {
    if (!frameworkDetail) return null;
    const currentVersion =
      frameworkDetail.fileVersions?.find(
        (v) => v.fileVersion === frameworkDetail.currentFileVersion
      ) || frameworkDetail.fileVersions?.[0];
    return currentVersion?.aiUpload?.job_id || null;
  };

  const handleClose = () => {
    setFrameworkDetail(null);
    onClose();
  };

  const handleCompare = async () => {
    if (!deploymentFramework?.aiUpload?.job_id) {
      toast.error("Deployment framework AI job ID not found");
      return;
    }

    const deploymentFrameworkJobId = deploymentFramework.aiUpload.job_id;
    const frameworkJobId = getFrameworkJobId();
    if (!frameworkJobId) {
      toast.error(
        "Framework AI job ID not found — ensure AI processing is completed"
      );
      return;
    }

    try {
      setComparing(true);
      const response = isDeploymentGap
        ? await analyzeDeploymentGap(deploymentFrameworkJobId, frameworkJobId)
        : await compareFrameworks(deploymentFrameworkJobId, frameworkJobId);

      if (response.success) {
        toast.success(
          response.message ||
            `Framework ${actionText.toLowerCase()} started successfully`
        );
        if (onSuccess) await onSuccess();
        else handleClose();
      }
    } catch (error) {
      toast.error(
        error.message || `Failed to start ${actionText.toLowerCase()}`
      );
    } finally {
      setComparing(false);
    }
  };

  const frameworkJobId = getFrameworkJobId();
  const canProceed =
    !!frameworkJobId && !!deploymentFramework?.aiUpload?.job_id;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <ModalHeader
          icon="activity"
          title={headerTitle}
          description={`${actionText} deployment framework with original framework`}
        />

        <div className="p-2 space-y-4">
          {/* Original Framework Info */}
          <div className="rounded border border-border p-3 bg-muted/30">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Will be compared with
            </p>
            {renderFrameworkContent(
              loadingFramework,
              frameworkDetail,
              frameworkJobId
            )}
          </div>

          {!canProceed && !loadingFramework && (
            <p className="text-xs text-red-500 flex items-center gap-1">
              <Icon name="warning" size="12px" />
              Both documents must have completed AI processing to{" "}
              {actionText.toLowerCase()}.
            </p>
          )}
        </div>

        <ModalFooter
          onCancel={handleClose}
          onSubmit={handleCompare}
          isSaving={comparing}
          isActionDisabled={!canProceed || loadingFramework}
          actionLabel={buttonText}
          savingLabel={`${actioningText}...`}
          actionIcon="activity"
          actionType="button"
        />
      </DialogContent>
    </Dialog>
  );
}
