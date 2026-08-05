/* eslint-disable react/prop-types */
import { useState, useEffect } from "react";
import { useModalState } from "@/hooks/useModalState";
import ModalHeader from "./ModalHeader";
import ModalFooter from "./ModalFooter";
import ConfirmModal from "./ConfirmModal";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDownIcon } from "lucide-react";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import Icon from "@/components/custom/Icon";
import DeploymentPointsEditor from "@/pages/framework-management/components/custom/DeploymentPointsEditor";

/**
 * DeleteControlModal
 * Sub-component for rendering control deletion confirmation dialog.
 */
function DeleteControlModal({ control, onConfirm, onCancel, open }) {
  if (!control) return null;

  return (
    <ConfirmModal
      onCancel={onCancel}
      onConfirm={onConfirm}
      icon="warning"
      title="Delete Control"
      description="Confirm deletion of control. This action cannot be undone."
      actionLabel="Delete Control"
      savingLabel="Deleting..."
      actionIcon="trash"
      open={open}
    >
      <p className="text-muted-foreground text-xs leading-relaxed">
        Are you sure you want to delete this control? This action cannot be
        undone.
      </p>

      <div className="bg-muted rounded p-3 border-l-4 border-destructive">
        <div className="flex items-center gap-3 mb-2">
          <div className="shrink-0 px-2 py-1 rounded bg-destructive/15 text-destructive text-xs font-bold font-mono">
            {control.id}
          </div>
          <h4 className="text-sm font-semibold text-foreground leading-snug">
            {control.name}
          </h4>
        </div>
        {control.description && (
          <div className="mt-2 pt-2 border-t border-border">
            <p className="text-xs text-muted-foreground leading-relaxed text-justify line-clamp-3">
              {control.description}
            </p>
          </div>
        )}
        {control.deployment_points?.length > 0 && (
          <p className="mt-2 text-xs text-muted-foreground">
            <span className="font-medium">
              {control.deployment_points.length}
            </span>{" "}
            deployment point{control.deployment_points.length === 1 ? "" : "s"}{" "}
            will also be removed.
          </p>
        )}
      </div>
    </ConfirmModal>
  );
}

/**
 * AddEditControlModal
 * Sub-component for rendering the Add or Edit control forms.
 */
function AddEditControlModal({
  type,
  control,
  sections = [],
  onSave,
  onCancel,
  open,
}) {
  const { handleError } = useErrorHandler();
  const { loading: saving, setLoading: setSaving } = useModalState();

  const [sectionId, setSectionId] = useState("");
  const [newSection, setNewSection] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [points, setPoints] = useState([]);

  // Sync state with type/props changes
  useEffect(() => {
    if (type === "add") {
      setSectionId(
        sections.length > 0 ? (sections[0]?.id ?? "other") : "other"
      );
      setNewSection("");
      setName("");
      setDescription("");
      setPoints([{ id: "DP-001", name: "" }]);
    } else if (type === "edit" && control) {
      setName(control.name ?? "");
      setDescription(control.description ?? "");
      const existing = control.deployment_points ?? [];
      setPoints(existing.length > 0 ? existing : [{ id: "", name: "" }]);
    }
  }, [type, control, sections]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const filteredPoints = points.filter((p) => p.name.trim().length > 0);

      if (type === "add") {
        const mappedPoints = filteredPoints.map((p) => ({
          name: p.name.trim(),
        }));
        const payload = {
          name: name.trim(),
          description: description.trim(),
          deployment_points: mappedPoints,
        };

        if (sectionId === "other") {
          payload.newSection = newSection.trim();
        } else {
          payload.sectionId = sectionId;
        }

        await onSave(payload);
      } else if (type === "edit") {
        await onSave({
          ...control,
          name: name.trim(),
          description: description.trim(),
          deployment_points: filteredPoints,
        });
      }
      onCancel();
    } catch (error) {
      handleError(
        error,
        type === "add" ? "Error adding control" : "Error saving control"
      );
    } finally {
      setSaving(false);
    }
  };

  const isSectionValid =
    sectionId === "other"
      ? newSection.trim().length > 0
      : sectionId.trim().length > 0;

  const isFormValid =
    type === "add"
      ? isSectionValid &&
        name.trim().length > 0 &&
        description.trim().length > 0 &&
        points.some((p) => p.name.trim().length > 0)
      : points.some((p) => p.name.trim().length > 0);

  const isDisabled = saving || !isFormValid;

  const renderSectionSelectorValue = () => {
    if (sectionId === "other") {
      return (
        <span className="flex items-center gap-2">
          <Icon name="plus" size="13px" className="text-muted-foreground" />
          Other (Create new section...)
        </span>
      );
    }
    if (sectionId) {
      const s = sections.find((sec) => sec.id === sectionId);
      if (s) {
        return (
          <span className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground mr-1">
              [{s.id}]
            </span>
            {s.name}
          </span>
        );
      }
    }
    return <span className="text-muted-foreground">Select a section...</span>;
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen) onCancel();
      }}
    >
      <DialogContent className="lg:max-w-175 max-h-[90vh] flex flex-col">
        <ModalHeader
          icon={type === "add" ? "plus" : "edit"}
          title={type === "add" ? "Add Control" : "Update Control"}
          description={
            type === "add"
              ? "Add a new control to an existing or new section"
              : name
          }
        />

        <form
          onSubmit={handleSubmit}
          className="flex flex-col flex-1 overflow-hidden"
        >
          <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
            {/* Section selector (Add only) */}
            {type === "add" && (
              <div className="space-y-2">
                <Label className="text-sm font-medium">
                  Section <span className="text-destructive ml-0.5">*</span>
                </Label>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full justify-between font-normal text-left"
                    >
                      {renderSectionSelectorValue()}
                      <ChevronDownIcon className="size-4 opacity-50 shrink-0 ml-2" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="min-w-(--radix-dropdown-menu-trigger-width) max-h-60 overflow-y-auto">
                    {sections.map((s) => (
                      <DropdownMenuItem
                        key={s.id}
                        onSelect={() => setSectionId(s.id)}
                        className={
                          sectionId === s.id ? "bg-primary/10 text-primary" : ""
                        }
                      >
                        <span className="font-mono text-xs text-muted-foreground mr-2">
                          {s.id}
                        </span>
                        {s.name}
                      </DropdownMenuItem>
                    ))}
                    {sections.length > 0 && (
                      <div className="h-px bg-muted my-1" />
                    )}
                    <DropdownMenuItem
                      key="other"
                      onSelect={() => setSectionId("other")}
                      className={
                        sectionId === "other"
                          ? "bg-primary/10 text-primary font-medium"
                          : "font-medium"
                      }
                    >
                      <Icon name="plus" size="13px" className="mr-2" />
                      Other (Create new section...)
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                {sectionId === "other" && (
                  <div className="pt-1 animate-in fade-in slide-in-from-top-1 duration-200">
                    <Input
                      id="add-new-section"
                      value={newSection}
                      onChange={(e) => setNewSection(e.target.value)}
                      placeholder="Enter new section name (e.g. Access Control)..."
                    />
                  </div>
                )}
              </div>
            )}

            {/* Control Name */}
            <div className="space-y-1">
              <Label htmlFor="control-name" className="text-sm font-medium">
                Control Name{" "}
                {type === "add" && (
                  <span className="text-destructive ml-0.5">*</span>
                )}
              </Label>
              <Input
                id="control-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter control name..."
              />
            </div>

            {/* Description */}
            <div className="space-y-1">
              <Label
                htmlFor="control-description"
                className="text-sm font-medium"
              >
                Description{" "}
                {type === "add" && (
                  <span className="text-destructive ml-0.5">*</span>
                )}
              </Label>
              <Textarea
                id="control-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={type === "add" ? 3 : 5}
                className={
                  type === "add" ? "min-h-20 resize-none" : "field-sizing-fixed"
                }
                placeholder="Enter control description..."
              />
            </div>

            {/* Deployment Points */}
            <DeploymentPointsEditor
              points={points}
              onChange={setPoints}
              required={type === "add"}
            />
          </div>

          <ModalFooter
            onCancel={onCancel}
            isSaving={saving}
            isActionDisabled={isDisabled}
            actionLabel={type === "add" ? "Add Control" : "Save Changes"}
            className="shrink-0"
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * ControlModal
 * Shell routing component to dispatch between subcomponents.
 */
export default function ControlModal({
  type,
  control,
  sections = [],
  onSave,
  onConfirm,
  onCancel,
  open = true,
}) {
  if (type === "delete") {
    return (
      <DeleteControlModal
        control={control}
        onConfirm={onConfirm}
        onCancel={onCancel}
        open={open}
      />
    );
  }

  return (
    <AddEditControlModal
      type={type}
      control={control}
      sections={sections}
      onSave={onSave}
      onCancel={onCancel}
      open={open}
    />
  );
}
