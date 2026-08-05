/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { ConfirmModal, WarningBox } from "@/components/custom/modal";

export default function ApproveFrameworkModal({
  framework,
  onConfirm,
  onCancel,
}) {
  return (
    <ConfirmModal
      onCancel={onCancel}
      onConfirm={onConfirm}
      icon="check-circle"
      title="Finalise Framework"
      description="Confirm finalisation of framework. This will mark the framework as finalised and ready for use."
      actionLabel="Finalise Framework"
      savingLabel="Approving..."
      actionIcon="check-circle"
      actionVariant="default"
    >
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
              Framework version: {framework.frameworkVersion}
            </p>
            <p className="text-sm text-muted-foreground m-0">
              Current File version: {framework.currentFileVersion}
            </p>
          </div>
        </div>
      </div>

      <WarningBox variant="warning">
        Are you sure you want to finalise this framework? This action cannot be
        undone. Once finalised, the framework will be marked as ready for use,
        and you will no longer be able to edit, update, or delete it.
      </WarningBox>

      <WarningBox variant="warning">
        Warning: Please ensure all controls have a valid weightage between 1 and
        10 before finalising. The process will fail if any controls are missing
        a weightage.
      </WarningBox>
    </ConfirmModal>
  );
}
