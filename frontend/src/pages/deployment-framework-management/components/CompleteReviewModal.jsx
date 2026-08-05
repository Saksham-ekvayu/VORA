/* eslint-disable react/prop-types */

import { useState } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";

import { useModalState } from "@/hooks/useModalState";
import {
  STATUS_APPROVED,
  STATUS_PENDING,
  STATUS_REJECTED,
} from "@/utils/commonUtils";

const CompleteReviewModal = ({ isOpen, framework, onClose, onConfirm }) => {
  const [comments, setComments] = useState("");
  const { loading: isSubmitting, setLoading: setIsSubmitting } =
    useModalState();

  const allStatuses =
    framework?.fileVersions
      ?.flatMap((ver) => ver.comparison?.comparisons?.comparison_data || [])
      .flatMap((item) => item.Client_deployment_points || [])
      .map((dp) => dp.status) || [];

  const approvedStatus = allStatuses.filter(
    (s) => s === STATUS_APPROVED
  ).length;

  const rejectedStatus = allStatuses.filter(
    (s) => s === STATUS_REJECTED
  ).length;

  const pendingStatus = allStatuses.filter((s) => s === STATUS_PENDING).length;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(comments);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => !isSubmitting && !open && onClose()}
    >
      <DialogContent className="lg:max-w-125">
        <ModalHeader
          title="Complete Review"
          description="Confirm completion of framework review and optionally leave comments."
        />

        <div className="p-4 space-y-4">
          <p className="text-muted-foreground text-xs leading-relaxed">
            Are you sure you want to finalize and submit this review? Ensure all
            deployment points have been marked as either Approved or Rejected.
          </p>

          <div className="grid grid-cols-3 gap-3">
            {/* ✅ Approved */}
            <div className="rounded border border-green-200 bg-green-500/10 p-3 text-center">
              <p className="text-xs text-green-700 font-medium">Approved</p>
              <p className="text-lg font-bold text-green-600">
                {approvedStatus}
              </p>
            </div>

            {/* ❌ Rejected */}
            <div className="rounded border border-red-200 bg-red-500/10 p-3 text-center">
              <p className="text-xs text-red-700 font-medium">Rejected</p>
              <p className="text-lg font-bold text-red-600">{rejectedStatus}</p>
            </div>

            {/* ⏳ Pending */}
            <div className="rounded border border-yellow-200 bg-yellow-500/10 p-3 text-center">
              <p className="text-xs text-yellow-700 font-medium">Pending</p>
              <p className="text-lg font-bold text-yellow-600">
                {pendingStatus}
              </p>
            </div>
          </div>
          {pendingStatus > 0 && (
            <div className="text-xs text-yellow-600 bg-yellow-500/10 border border-yellow-200 rounded px-3 py-2">
              ⚠️ You still have {pendingStatus} pending deployment points.
              Please review them before completing.
            </div>
          )}

          <div>
            <label
              htmlFor="overall-comments"
              className="text-sm font-medium mb-2 block"
            >
              Overall Comments (Optional)
            </label>
            <textarea
              id="overall-comments"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
              rows={4}
              placeholder="Add final review notes, summaries, or general feedback here..."
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              disabled={isSubmitting}
            />
          </div>
        </div>

        <ModalFooter
          onCancel={onClose}
          onSubmit={handleSubmit}
          isSaving={isSubmitting}
          isActionDisabled={pendingStatus > 0}
          actionLabel="Complete Review"
          savingLabel="Complete Review"
          actionIcon="check-circle"
          actionType="button"
        />
      </DialogContent>
    </Dialog>
  );
};

export default CompleteReviewModal;
