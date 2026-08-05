/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { ConfirmModal, WarningBox } from "@/components/custom/modal";

export default function DeleteVersionModal({ version, onConfirm, onCancel }) {
  return (
    <ConfirmModal
      open={!!version}
      onCancel={onCancel}
      onConfirm={onConfirm}
      icon="warning"
      title="Delete File Version"
      description="Confirm deletion of file version"
      actionLabel="Delete Version"
      savingLabel="Deleting..."
      actionIcon="trash"
    >
      <p className="text-muted-foreground text-xs leading-relaxed">
        Are you sure you want to delete this file version? This action cannot be
        undone.
      </p>

      <div className="bg-muted rounded p-3 border-l-4 border-red-500">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary">
            <Icon name="document" size="20px" />
          </div>
          <div className="flex-1">
            <h4 className="text-base font-semibold text-foreground m-0">
              {version?.originalFileName}
            </h4>
            <p className="text-sm text-muted-foreground m-0">
              Version: {version?.version}
            </p>
          </div>
        </div>
        <div className="flex gap-2 mt-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
            {version?.documentType?.toUpperCase() || "PDF"}
          </span>
          {version?.fileSize && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400">
              {version.fileSize}
            </span>
          )}
        </div>
      </div>

      <WarningBox variant="info" icon="info">
        Note: You cannot delete the only remaining version. To remove the
        document entirely, delete it from the documents list.
      </WarningBox>
    </ConfirmModal>
  );
}
