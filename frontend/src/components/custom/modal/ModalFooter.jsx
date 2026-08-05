/* eslint-disable react/prop-types */

import { DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import Icon from "../Icon";

/**
 * Reusable Modal Footer Component
 * Unifies footer buttons, loader spinner, and styles across all modals
 */
export default function ModalFooter({
  onCancel,
  onSubmit,
  cancelLabel = "Cancel",
  actionLabel = "Save Changes",
  savingLabel = "Saving...",
  isSaving = false,
  isActionDisabled = false,
  actionType = "submit",
  actionVariant = "default",
  actionIcon = "check",
  className = "",
}) {
  return (
    <DialogFooter className={cn("pt-4 border-t border-border p-2", className)}>
      <Button
        type="button"
        variant="outline"
        className="flex-1"
        onClick={onCancel}
        disabled={isSaving}
      >
        {cancelLabel}
      </Button>

      <Button
        type={actionType}
        variant={actionVariant}
        className={cn(
          "flex-1 inline-flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed",
          actionVariant === "destructive" &&
            "bg-destructive hover:bg-destructive/80 text-white"
        )}
        onClick={onSubmit}
        disabled={isSaving || isActionDisabled}
      >
        {isSaving ? (
          <>
            <Icon name="loader" size="16px" className="animate-spin" />
            {savingLabel}
          </>
        ) : (
          <>
            {actionIcon && <Icon name={actionIcon} size="16px" />}
            {actionLabel}
          </>
        )}
      </Button>
    </DialogFooter>
  );
}
