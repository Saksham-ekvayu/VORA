/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import {
  isInternalExpert,
  getScoreStyle,
  getScoreLabel,
  getGapStatusStyle,
} from "@/utils/commonUtils";
import { Textarea } from "@/components/ui/textarea";
import { addGapReviewRemark } from "@/services/deploymentFrameworkService";
import { toast } from "sonner";

export default function GapReviewCommentModal({
  isOpen,
  onClose,
  point,
  userRole,
  onSave,
}) {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const packageVersion = searchParams.get("package-version");

  const [tempComment, setTempComment] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Sync initial comment directly from point object when modal opens or point changes
  useEffect(() => {
    if (isOpen && point) {
      setTempComment(point.reviewComment || "");
    }
  }, [isOpen, point]);

  const handleSave = async () => {
    if (!point) return;
    try {
      setIsSaving(true);
      const response = await addGapReviewRemark(id, packageVersion, {
        assignedControlId: point.assigned_framework_control_id,
        assignedPointId: point.assigned_dp?.id,
        deploymentControlId: point.deployment_framework_control_id,
        deploymentPointId: point.deployment_dp?.id,
        comment: tempComment,
      });
      if (response.success) {
        toast.success("Review comment saved successfully");
        onSave?.();
        onClose();
      } else {
        toast.error(response.message || "Failed to save comment");
      }
    } catch (err) {
      console.error("Failed to save comment:", err);
      toast.error(err?.message || "Failed to save comment");
    } finally {
      setIsSaving(false);
    }
  };

  const showEdit = isInternalExpert(userRole);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="lg:max-w-lg">
        <ModalHeader
          icon="message-square"
          title="Review Comments (Gap Analysis)"
          description="View or add review remarks for this point alignment."
        />

        <div className="flex flex-col gap-2 p-2">
          {point && (
            <div className="space-y-2">
              {/* Context header */}
              <div className="grid grid-cols-2 gap-4 p-3 rounded bg-muted/40 border border-border text-xs">
                <div>
                  <p className="font-bold text-primary uppercase mb-1">
                    Assigned Point{" "}
                    {point.assigned_dp?.id ? `#${point.assigned_dp.id}` : ""}
                  </p>
                  <p className="text-muted-foreground line-clamp-4 text-[11px] leading-relaxed">
                    {point.assigned_dp?.point || "N/A"}
                  </p>
                </div>
                <div className="border-l border-border pl-4">
                  <p className="font-bold text-primary uppercase mb-1">
                    Deployment Point{" "}
                    {point.deployment_dp?.id
                      ? `#${point.deployment_dp.id}`
                      : ""}
                  </p>
                  <p className="text-muted-foreground line-clamp-4 text-[11px] leading-relaxed">
                    {point.deployment_dp?.point ||
                      "No matching deployment point"}
                  </p>
                </div>
              </div>

              {/* Similarity Score + Status */}
              <div className="flex items-center justify-between p-2 rounded border border-border bg-card text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-muted-foreground">
                    Similarity Score:
                  </span>
                  {(() => {
                    const score = Math.round(point.similarity_score);
                    return (
                      <span
                        className="text-xs font-bold px-2 py-0.5 rounded-full"
                        style={getScoreStyle(score)}
                      >
                        {score}% ({getScoreLabel(score)})
                      </span>
                    );
                  })()}
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-muted-foreground">
                    Status:
                  </span>
                  <span
                    className="font-bold capitalize text-xs px-1.5 py-0.5 rounded"
                    style={getGapStatusStyle(point.implementation_status)}
                  >
                    {point.implementation_status}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Comments section */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-foreground uppercase tracking-wider block">
              {showEdit ? "Add / Edit Comments" : "Comments (View Only)"}
            </label>
            {showEdit ? (
              <Textarea
                className="h-45 overflow-y-auto resize-none text-sm"
                style={{ fieldSizing: "normal" }}
                placeholder="Type your review comments or feedback here..."
                value={tempComment}
                onChange={(e) => setTempComment(e.target.value)}
              />
            ) : (
              <div className="w-full rounded border border-border bg-muted/40 px-3 py-3 text-sm h-45 overflow-y-auto text-foreground text-justify leading-relaxed whitespace-pre-wrap">
                {tempComment || "No review comments submitted yet."}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        {showEdit && (
          <ModalFooter
            onCancel={onClose}
            onSubmit={handleSave}
            isSaving={isSaving}
            actionLabel="Save Comment"
            actionIcon="check"
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
