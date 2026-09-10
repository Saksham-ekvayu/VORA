/* eslint-disable react/prop-types */
import { useState, useEffect } from "react";
import { useModalState } from "@/hooks/useModalState";
import ModalHeader from "./ModalHeader";
import ModalFooter from "./ModalFooter";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useErrorHandler } from "@/hooks/useErrorHandler";

export default function UpdateSectionModal({
  section,
  onSave,
  onCancel,
  open = true,
}) {
  const { handleError } = useErrorHandler();
  const { loading: saving, setLoading: setSaving } = useModalState();

  const [name, setName] = useState("");

  useEffect(() => {
    if (section && open) {
      setName(section.name ?? "");
    }
  }, [section, open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave({
        ...section,
        name: name.trim(),
      });
      onCancel();
    } catch (error) {
      handleError(error, "Error updating section");
    } finally {
      setSaving(false);
    }
  };

  const isFormValid = name.trim().length > 0;
  const isDisabled = saving || !isFormValid || name.trim() === section?.name;

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen) onCancel();
      }}
    >
      <DialogContent className="max-w-md">
        <ModalHeader
          icon="edit"
          title="Update Section Name"
          description={`Update name for section [${section?.id}]`}
        />

        <form onSubmit={handleSubmit} className="flex flex-col">
          <div className="px-4 py-4 space-y-4">
            <div className="space-y-1">
              <Label htmlFor="section-name" className="text-sm font-medium">
                Section Name <span className="text-destructive ml-0.5">*</span>
              </Label>
              <Input
                id="section-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter section name..."
                autoFocus
              />
            </div>
          </div>

          <ModalFooter
            onCancel={onCancel}
            isSaving={saving}
            isActionDisabled={isDisabled}
            actionLabel="Save Changes"
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
