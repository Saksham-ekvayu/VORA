/* eslint-disable react/prop-types */

import { useState, useMemo } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import { Textarea } from "@/components/ui/textarea";
import { reviewDeploymentPackage } from "@/services/deploymentFrameworkService";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Stat helpers — derived from the package data
// ---------------------------------------------------------------------------

function getComparisonStats(pkg) {
  const total = pkg?.comparison?.total_controls || 0;
  const reviewed = pkg?.comparison?.reviewed_controls || 0;
  return { total, reviewed };
}

function getGapStats(pkg) {
  const total = pkg?.gapAnalysis?.total_points || 0;
  const reviewed = pkg?.gapAnalysis?.reviewed_points || 0;
  return { total, reviewed };
}

// ---------------------------------------------------------------------------
// Small stat pill
// ---------------------------------------------------------------------------

function ReviewStat({ label, reviewed, total }) {
  const allDone = reviewed === total && total > 0;
  const none = reviewed === 0;

  let colorClass =
    "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/20 dark:border-amber-900/30 dark:text-amber-400";
  if (allDone) {
    colorClass =
      "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/20 dark:border-emerald-900/30 dark:text-emerald-400";
  } else if (none) {
    colorClass =
      "bg-rose-50 border-rose-200 text-rose-700 dark:bg-rose-950/20 dark:border-rose-900/30 dark:text-rose-400";
  }

  let statusText = `${total - reviewed} pending`;
  if (total === 0) statusText = "No data";
  else if (allDone) statusText = "All reviewed";

  return (
    <div className={`flex-1 rounded border p-2.5 text-xs ${colorClass}`}>
      <p className="font-semibold uppercase tracking-wider mb-1 opacity-70">
        {label}
      </p>
      <p className="text-base font-bold leading-none">
        {reviewed}
        <span className="text-xs font-normal opacity-60"> / {total}</span>
      </p>
      <p className="text-[10px] mt-1 opacity-70">{statusText}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

/**
 * Props:
 *   isOpen        — controls visibility
 *   onClose       — called when modal should close
 *   action        — "approve" | "return"
 *   frameworkId   — deployment framework _id
 *   packageVersion — the package version being reviewed
 *   packageData   — the full package object from API (for review stats)
 *   onSuccess     — callback after successful save (refresh parent)
 */
export default function ExpertReviewModal({
  isOpen,
  onClose,
  action,
  frameworkId,
  packageVersion,
  packageData,
  onSuccess,
}) {
  const [comments, setComments] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const isApprove = action === "approve";

  const title = isApprove ? "Approve Package" : "Return Package";
  const description = isApprove
    ? "Confirm approval of this deployment package. It will be marked as deployed and go live."
    : "Return this package to the auditor for revision. Please provide feedback below.";
  const icon = isApprove ? "check-circle" : "warning";
  const actionLabel = isApprove ? "Approve & Deploy" : "Return for Revision";
  const actionIcon = isApprove ? "check" : "x-circle";

  const comparisonStats = useMemo(
    () => getComparisonStats(packageData),
    [packageData]
  );
  const gapStats = useMemo(() => getGapStats(packageData), [packageData]);

  const handleClose = () => {
    setComments("");
    onClose();
  };

  const handleSubmit = async () => {
    if (!isApprove && !comments.trim()) {
      toast.error("Please provide comments when returning a package.");
      return;
    }
    try {
      setIsSaving(true);
      const response = await reviewDeploymentPackage(
        frameworkId,
        packageVersion,
        { action, comments: comments.trim() || undefined }
      );
      if (response.success) {
        toast.success(response.message || `Package ${action}d successfully`);
        handleClose();
        onSuccess?.();
      } else {
        toast.error(response.message || `Failed to ${action} package`);
      }
    } catch (err) {
      toast.error(err?.message || `Failed to ${action} package`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="lg:max-w-lg">
        <ModalHeader icon={icon} title={title} description={description} />

        <div className="flex flex-col gap-3 p-2">
          {/* Package version context */}
          <div className="flex items-center justify-between p-2.5 rounded border border-border bg-muted/40 text-xs">
            <span className="font-semibold text-muted-foreground">
              Package Version:
            </span>
            <span className="font-bold text-foreground">v{packageVersion}</span>
          </div>

          {/* Review coverage stats */}
          <div>
            <p className="text-xs font-bold text-foreground uppercase tracking-wider mb-2">
              Review Coverage
            </p>
            <div className="flex gap-2">
              <ReviewStat
                label="Comparison Reviews"
                reviewed={comparisonStats.reviewed}
                total={comparisonStats.total}
              />
              <ReviewStat
                label="Gap Analysis Reviews"
                reviewed={gapStats.reviewed}
                total={gapStats.total}
              />
            </div>
          </div>

          {/* Comments */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground uppercase tracking-wider block">
              {isApprove ? "Comments (Optional)" : "Comments (Required)"}
            </label>
            <Textarea
              className="h-28 resize-none text-sm"
              style={{ fieldSizing: "normal" }}
              placeholder={
                isApprove
                  ? "Add any optional notes about this approval..."
                  : "Describe what needs to be revised before re-submission..."
              }
              value={comments}
              onChange={(e) => setComments(e.target.value)}
            />
          </div>

          {/* Info banner */}
          {isApprove ? (
            <div className="text-[11px] text-emerald-700 dark:text-emerald-400 flex items-start gap-1.5 bg-emerald-50 dark:bg-emerald-950/20 p-2.5 rounded border border-emerald-200/60 dark:border-emerald-900/30">
              <span className="shrink-0 mt-0.5">✓</span>
              <span>
                This will deploy the package as the live version. Any previously
                live package will be marked as superseded.
              </span>
            </div>
          ) : (
            <div className="text-[11px] text-amber-700 dark:text-amber-400 flex items-start gap-1.5 bg-amber-50 dark:bg-amber-950/20 p-2.5 rounded border border-amber-200/60 dark:border-amber-900/30">
              <span className="shrink-0 mt-0.5">⚠</span>
              <span>
                The package will be returned to the auditor with your feedback
                for revision.
              </span>
            </div>
          )}
        </div>

        <ModalFooter
          onCancel={handleClose}
          onSubmit={handleSubmit}
          isSaving={isSaving}
          actionLabel={actionLabel}
          actionIcon={actionIcon}
          actionVariant={isApprove ? "default" : "destructive"}
        />
      </DialogContent>
    </Dialog>
  );
}
