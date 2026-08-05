/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import {
  isInternalExpert,
  getScoreStyle,
  getScoreLabel,
} from "@/utils/commonUtils";
import { Textarea } from "@/components/ui/textarea";
import { addReviewRemark } from "@/services/deploymentFrameworkService";
import { toast } from "sonner";

export default function ComparisonReviewCommentModal({
  isOpen,
  onClose,
  control,
  userRole,
  onSave,
}) {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const packageVersion = searchParams.get("package-version");

  const [tempComment, setTempComment] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Sync initial comment directly from control object when modal opens or control changes
  useEffect(() => {
    if (isOpen && control) {
      setTempComment(control.reviewComment || "");
    }
  }, [isOpen, control]);

  const handleSave = async () => {
    if (!control) return;
    try {
      setIsSaving(true);
      const response = await addReviewRemark(id, packageVersion, {
        assignedControlId: control.assigned.id,
        deploymentControlId: control.deployment.id,
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
          title="Review Comments"
          description="View or add review remarks for this control alignment."
        />

        <div className="flex flex-col gap-2 p-2">
          {control && (
            <div className="space-y-2">
              {/* Context header */}
              <div className="grid grid-cols-2 gap-4 p-3 rounded bg-muted/40 border border-border text-xs">
                <div>
                  <p className="font-bold text-primary uppercase mb-1">
                    {control.assigned.id || "Assigned Control"}
                  </p>
                  <p className="font-semibold text-foreground mb-1 line-clamp-1">
                    {control.assigned.name}
                  </p>
                  <p className="text-muted-foreground line-clamp-2 text-[11px]">
                    {control.assigned.desc}
                  </p>
                </div>
                <div className="border-l border-border pl-4">
                  <p className="font-bold text-primary uppercase mb-1">
                    {control.deployment.id || "Deployment Control"}
                  </p>
                  <p className="font-semibold text-foreground mb-1 line-clamp-1">
                    {control.deployment.name}
                  </p>
                  <p className="text-muted-foreground line-clamp-2 text-[11px]">
                    {control.deployment.desc}
                  </p>
                </div>
              </div>

              {/* Similarity / Score details */}
              <div className="flex items-center justify-between p-2 rounded border border-border bg-card">
                <span className="text-xs font-semibold text-muted-foreground">
                  Semantic Score:
                </span>
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded-full"
                  style={getScoreStyle(control.score)}
                >
                  {control.score}% ({getScoreLabel(control.score)})
                </span>
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
                className="h-45 overflow-y-auto resize-none"
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
