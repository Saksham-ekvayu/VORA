/* eslint-disable react/prop-types */

import { ConfirmModal, WarningBox } from "@/components/custom/modal";

export default function FinalizeFrameworkVersionModal({
  framework,
  onConfirm,
  onCancel,
}) {
  if (!framework) return null;

  return (
    <ConfirmModal
      onCancel={onCancel}
      onConfirm={onConfirm}
      icon="lock"
      title="Finalize Framework"
      description="Finalize this framework assignment configuration. This action cannot be undone."
      actionLabel="Finalize Framework"
      savingLabel="Finalizing..."
      actionIcon="lock"
      actionVariant="default"
    >
      <div className="bg-muted rounded p-3 border-l-4 border-emerald-500 space-y-1">
        <h4 className="text-sm font-semibold text-foreground leading-snug truncate">
          {framework.frameworkName}
        </h4>
        <div className="flex items-center gap-3">
          <div className="shrink-0 px-2 py-1 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 text-xs font-bold font-mono">
            Framework Version: {framework.frameworkVersion}
          </div>
        </div>
      </div>

      <WarningBox variant="warning">
        Are you sure you want to finalize this framework? Once finalized, all
        control customizations will be permanently locked. You will no longer be
        able to add, edit, delete, or change the applicability or weightage of
        any controls for this framework assignment.
      </WarningBox>
    </ConfirmModal>
  );
}
