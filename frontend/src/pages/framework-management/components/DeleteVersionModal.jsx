/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { ConfirmModal, WarningBox } from "@/components/custom/modal";

export default function DeleteVersionModal({ version, onConfirm, onCancel }) {
  if (!version) return null;

  return (
    <ConfirmModal
      onCancel={onCancel}
      onConfirm={onConfirm}
      icon="warning"
      title="Delete Version"
      description="Confirm deletion of file version. This action cannot be undone."
      actionLabel="Delete Version"
      savingLabel="Deleting..."
      actionIcon="trash"
    >
      <p className="text-muted-foreground text-xs leading-relaxed">
        Are you sure you want to delete version{" "}
        <span className="font-semibold text-foreground">
          {version.fileVersion}
        </span>{" "}
        ? This action cannot be undone.
      </p>

      <div className="bg-muted rounded p-3 border-l-4 border-red-500">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center text-red-600 dark:text-red-400">
            <Icon name="document" size="20px" />
          </div>
          <div className="flex-1">
            <h4 className="text-base font-semibold text-foreground m-0">
              {version.originalFileName}
            </h4>
            <p className="text-sm text-muted-foreground m-0">
              File version: {version.fileVersion}
            </p>
          </div>
        </div>
        <div className="flex gap-2 mt-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
            {version.frameworkType?.toUpperCase() || "PDF"}
          </span>
          {version.fileSize && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400">
              {version.fileSize}
            </span>
          )}
        </div>
        {version.uploadedBy?.name && (
          <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
            Created By: {version.uploadedBy.name}
          </p>
        )}
      </div>

      <WarningBox variant="info" icon="info">
        Other versions will remain intact. If this is the current version, the
        latest version will become the new current version.
      </WarningBox>
    </ConfirmModal>
  );
}
