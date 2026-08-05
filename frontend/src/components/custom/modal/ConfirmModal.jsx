/* eslint-disable react/prop-types */

import { Dialog, DialogContent } from "@/components/ui/dialog";

import { useModalState } from "@/hooks/useModalState";
import ModalHeader from "./ModalHeader";
import ModalFooter from "./ModalFooter";

/**
 * ConfirmModal — generic confirmation dialog.
 *
 * Replaces the ~20 delete/confirm modals that share the exact same structure:
 *   Dialog → ModalHeader → body content → destructive ModalFooter
 *
 * Props:
 *   open             – boolean
 *   onCancel         – () => void
 *   onConfirm        – async () => void
 *   icon             – string icon name for ModalHeader  (default "warning")
 *   title            – string
 *   description      – string
 *   actionLabel      – string  (default "Confirm")
 *   savingLabel      – string  (default "Processing...")
 *   actionIcon       – string  (default "check")
 *   actionVariant    – "default" | "destructive"  (default "destructive")
 *   isActionDisabled – boolean  (disables the action button regardless of loading)
 *   maxWidth         – Tailwind class  (default "lg:max-w-125")
 *   children         – modal body content
 */
export default function ConfirmModal({
  open = true,
  onCancel,
  onConfirm,
  icon = "warning",
  title,
  description,
  actionLabel = "Confirm",
  savingLabel = "Processing...",
  actionIcon = "check",
  actionVariant = "destructive",
  isActionDisabled = false,
  maxWidth = "lg:max-w-125",
  children,
}) {
  const { loading, setLoading } = useModalState();

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onCancel?.();
    } catch (error) {
      console.error("ConfirmModal action error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onCancel}>
      <DialogContent className={maxWidth}>
        <ModalHeader icon={icon} title={title} description={description} />

        {children && <div className="flex flex-col gap-2 p-2">{children}</div>}

        <ModalFooter
          onCancel={onCancel}
          onSubmit={handleConfirm}
          isSaving={loading}
          savingLabel={savingLabel}
          actionLabel={actionLabel}
          actionIcon={actionIcon}
          actionType="button"
          actionVariant={actionVariant}
          isActionDisabled={isActionDisabled}
        />
      </DialogContent>
    </Dialog>
  );
}
