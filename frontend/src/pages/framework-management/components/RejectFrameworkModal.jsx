/* eslint-disable react/prop-types */

import { useState } from "react";
import Icon from "@/components/custom/Icon";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  ModalFooter,
  ModalHeader,
  WarningBox,
} from "@/components/custom/modal";

import { useModalState } from "@/hooks/useModalState";

export default function RejectFrameworkModal({
  framework,
  onConfirm,
  onCancel,
}) {
  const { loading: rejecting, setLoading: setRejecting } = useModalState();
  const [rejectionReason, setRejectionReason] = useState("");

  const handleConfirm = async () => {
    setRejecting(true);
    try {
      await onConfirm(rejectionReason);
    } catch (error) {
      console.error("Error rejecting framework:", error);
    } finally {
      setRejecting(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={onCancel}>
      <DialogContent className="lg:max-w-125">
        <ModalHeader
          icon="x-circle"
          title="Reject Framework"
          description="Reject framework with optional reason. The uploader will be notified."
        />

        <div className="flex flex-col p-2 gap-3">
          <p className="text-muted-foreground text-xs leading-relaxed">
            Are you sure you want to reject this framework? Please provide a
            reason for rejection.
          </p>

          <div className="bg-muted rounded p-3 border-l-4 border-primary">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary">
                <Icon name="shield" size="20px" />
              </div>
              <div className="flex-1">
                <h4 className="text-base font-semibold text-foreground m-0">
                  {framework.frameworkName}
                </h4>
                <p className="text-sm text-muted-foreground m-0">
                  File version: {framework.currentFileVersion}
                </p>
              </div>
            </div>
          </div>

          <div>
            <Label
              htmlFor="rejectionReason"
              className="block text-sm font-medium mb-2"
            >
              Rejection Reason (Optional)
            </Label>
            <Textarea
              id="rejectionReason"
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Explain why this framework is being rejected..."
              className="w-full resize-none"
              rows={4}
              maxLength={500}
              disabled={rejecting}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {rejectionReason.length}/500 characters
            </p>
          </div>

          <WarningBox variant="info" icon="info">
            Once rejected, the framework will be marked as not approved. The
            uploader will be notified of the rejection.
          </WarningBox>
        </div>

        <ModalFooter
          onCancel={onCancel}
          onSubmit={handleConfirm}
          isSaving={rejecting}
          savingLabel="Rejecting..."
          actionLabel="Reject Framework"
          actionIcon="x-circle"
          actionType="button"
          actionVariant="destructive"
        />
      </DialogContent>
    </Dialog>
  );
}
