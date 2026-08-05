/* eslint-disable react/prop-types */

import { useModalState } from "@/hooks/useModalState";
import Icon from "@/components/custom/Icon";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";
import { requestFrameworkAccess } from "@/services/frameworkService";
import { Dialog, DialogContent } from "@/components/ui/dialog";

import { useErrorHandler } from "@/hooks/useErrorHandler";

/**
 * RequestAccessModal Component - Modal for requesting framework access
 *
 * @param {Object} framework - Framework to request access for (can be direct framework or access record with nested frameworkCategory)
 * @param {Function} onSuccess - Success handler
 * @param {Function} onClose - Close handler
 */
export default function RequestAccessModal({ framework, onSuccess, onClose }) {
  const { loading: requesting, setLoading: setRequesting } = useModalState();
  const { handleError, handleSuccess } = useErrorHandler();

  // Handle both data structures: direct framework object or nested frameworkCategory
  const getFrameworkData = () => {
    if (framework?.frameworkCategory) {
      // Data from FrameworkAccess (nested structure)
      return {
        id: framework.frameworkCategory.id,
        frameworkCategoryName:
          framework.frameworkCategory.frameworkCategoryName,
        code: framework.frameworkCategory.code,
        description: framework.frameworkCategory.description,
      };
    } else {
      // Data from FrameworkCategory (direct structure)
      return {
        id: framework?.id,
        frameworkCategoryName: framework?.frameworkCategoryName,
        code: framework?.code,
        description: framework?.description,
      };
    }
  };

  const frameworkData = getFrameworkData();

  const handleSubmit = async (e) => {
    e.preventDefault();

    setRequesting(true);
    try {
      const response = await requestFrameworkAccess(frameworkData.id);

      handleSuccess(response.message);
      onSuccess?.();
      onClose();
    } catch (err) {
      handleError(err, "Failed to request framework access");
    } finally {
      setRequesting(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent>
        <ModalHeader
          icon="send"
          title="Request Framework Access"
          description="Request access to framework category"
        />

        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-4 p-3">
            {/* Framework Details */}
            <div className="bg-muted/50 rounded p-4 border border-border">
              <h3 className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
                <Icon name="info" size="16px" className="text-primary" />
                Framework Details
              </h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                    <Icon
                      name="shield"
                      size="20px"
                      className="text-purple-600 dark:text-purple-400"
                    />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-base font-semibold text-foreground">
                      {frameworkData?.frameworkCategoryName}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Code: {frameworkData?.code}
                    </p>
                  </div>
                </div>

                {frameworkData?.description && (
                  <div className="bg-background p-3 rounded border border-border">
                    <p className="text-xs text-muted-foreground mb-1">
                      Description:
                    </p>
                    <p className="text-sm text-foreground line-clamp-3">
                      {frameworkData.description}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <ModalFooter
            onCancel={onClose}
            isSaving={requesting}
            savingLabel="Requesting..."
            actionLabel="Request Access"
            actionIcon="send"
            actionType="submit"
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
