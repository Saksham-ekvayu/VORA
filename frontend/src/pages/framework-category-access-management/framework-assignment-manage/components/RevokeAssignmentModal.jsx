/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { ConfirmModal } from "@/components/custom/modal";

export default function RevokeAssignmentModal({
  assignment,
  onConfirm,
  onCancel,
}) {
  return (
    <ConfirmModal
      onCancel={onCancel}
      onConfirm={onConfirm}
      icon="x-circle"
      title="Revoke Framework Assignment"
      description="Revoke framework assignment for customer. This action cannot be undone."
      actionLabel="Revoke Assignment"
      savingLabel="Revoking..."
      actionIcon="x-circle"
    >
      <p className="text-muted-foreground text-xs leading-relaxed">
        Are you sure you want to revoke this framework assignment? The customer
        will lose access to this framework.
      </p>

      <div className="bg-muted rounded p-3 border-l-4 border-red-500">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <Icon
                name="users"
                size="20px"
                className="text-blue-600 dark:text-blue-400"
              />
            </div>
            <div className="flex-1">
              <h4 className="text-base font-semibold text-foreground m-0">
                {assignment?.customer?.name}
              </h4>
              <p className="text-sm text-muted-foreground m-0">
                {assignment?.customer?.email}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
              <Icon
                name="shield"
                size="20px"
                className="text-purple-600 dark:text-purple-400"
              />
            </div>
            <div className="flex-1">
              <h4 className="text-base font-semibold text-foreground m-0">
                {assignment?.frameworkName}
              </h4>
              <p className="text-sm text-muted-foreground m-0 font-mono">
                {assignment?.frameworkCode} v{assignment?.frameworkVersion}
              </p>
            </div>
          </div>
          <div className="flex gap-2 mt-1">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
              Assigned
            </span>
          </div>
        </div>
      </div>
    </ConfirmModal>
  );
}
