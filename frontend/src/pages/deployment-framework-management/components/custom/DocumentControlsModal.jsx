import { useState, useEffect, useMemo } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import ControlsPanel from "@/components/custom/ControlsPanel";
import { ModalHeader, ControlModal } from "@/components/custom/modal";
import UpdateSectionModal from "@/components/custom/modal/UpdateSectionModal";
import { toast } from "sonner";
import {
  addDocumentControl,
  updateDocumentControl,
  deleteDocumentControl,
  updateDeploymentFrameworkSection,
} from "@/services/deploymentFrameworkService";

export default function DocumentControlsModal({
  isOpen,
  onClose,
  document: initialDocument,
  frameworkId,
  packageVersion,
  onSuccess,
}) {
  const [localDocument, setLocalDocument] = useState(initialDocument);
  const [editingControl, setEditingControl] = useState(null);
  const [deletingControl, setDeletingControl] = useState(null);
  const [sectionToEdit, setSectionToEdit] = useState(null);
  const [globalSearch, setGlobalSearch] = useState("");

  useEffect(() => {
    setLocalDocument(initialDocument);
  }, [initialDocument]);

  const controlsData = useMemo(() => {
    return localDocument?.aiExtraction?.controls?.controls_data || [];
  }, [localDocument?.aiExtraction?.controls?.controls_data]);

  const totalSections =
    localDocument?.aiExtraction?.controls?.total_sections ||
    controlsData.length;
  const totalControls =
    localDocument?.aiExtraction?.controls?.total_controls || 0;

  if (!isOpen || !localDocument) return null;

  const handleAddControl = async (newControl) => {
    try {
      const response = await addDocumentControl(
        frameworkId,
        packageVersion,
        localDocument.fileId,
        newControl
      );
      if (response.success && response.data) {
        toast.success(response.message || "Control added successfully");
        const { sectionId, control } = response.data;
        const updatedControlsData = [...controlsData];
        let targetSection = updatedControlsData.find((s) => s.id === sectionId);

        if (!targetSection) {
          targetSection = {
            id: sectionId,
            name: "Custom Controls",
            controls: [],
          };
          updatedControlsData.push(targetSection);
        }

        targetSection.controls = [...(targetSection.controls || []), control];

        setLocalDocument((prev) => ({
          ...prev,
          aiExtraction: {
            ...prev.aiExtraction,
            controls: {
              ...prev.aiExtraction.controls,
              controls_data: updatedControlsData,
              total_sections: updatedControlsData.length,
              total_controls: prev.aiExtraction.controls.total_controls + 1,
            },
          },
        }));

        if (onSuccess) {
          onSuccess();
        }

        return response;
      } else {
        toast.error(response.message || "Failed to add control");
        return { success: false };
      }
    } catch (error) {
      toast.error(error.message || "Error adding control");
      return { success: false };
    }
  };

  const handleEditSubmit = async (updatedData) => {
    try {
      const response = await updateDocumentControl(
        frameworkId,
        packageVersion,
        localDocument.fileId,
        editingControl.id || editingControl._uiKey,
        updatedData
      );
      if (response.success && response.data) {
        toast.success(response.message);
        const updatedControl = response.data.control;
        const updatedControlsData = controlsData.map((section) => ({
          ...section,
          controls: (section.controls || []).map((c) =>
            c.id === updatedControl.id ||
            (c._uiKey && c._uiKey === editingControl._uiKey)
              ? { ...c, ...updatedControl }
              : c
          ),
        }));

        setLocalDocument((prev) => ({
          ...prev,
          aiExtraction: {
            ...prev.aiExtraction,
            controls: {
              ...prev.aiExtraction.controls,
              controls_data: updatedControlsData,
            },
          },
        }));

        if (onSuccess) {
          onSuccess();
        }

        setEditingControl(null);
      } else {
        toast.error(response.message || "Failed to update control");
      }
    } catch (error) {
      toast.error(error.message || "Error updating control");
    }
  };

  const handleWeightageChange = async (control, weightage) => {
    try {
      const response = await updateDocumentControl(
        frameworkId,
        packageVersion,
        localDocument.fileId,
        control.id || control._uiKey,
        { weightage }
      );
      if (response.success && response.data) {
        toast.success(response.message || "Weightage updated successfully");
        const updatedControl = response.data.control;
        const updatedControlsData = controlsData.map((section) => ({
          ...section,
          controls: (section.controls || []).map((c) =>
            c.id === updatedControl.id ||
            (c._uiKey && c._uiKey === control._uiKey)
              ? { ...c, ...updatedControl }
              : c
          ),
        }));

        setLocalDocument((prev) => ({
          ...prev,
          aiExtraction: {
            ...prev.aiExtraction,
            controls: {
              ...prev.aiExtraction.controls,
              controls_data: updatedControlsData,
            },
          },
        }));

        if (onSuccess) {
          onSuccess();
        }
      } else {
        toast.error(response.message || "Failed to update weightage");
      }
    } catch (error) {
      toast.error(error.message || "Error updating weightage");
    }
  };

  const handleDeleteSubmit = async () => {
    try {
      const response = await deleteDocumentControl(
        frameworkId,
        packageVersion,
        localDocument.fileId,
        deletingControl.id || deletingControl._uiKey
      );

      if (response.success) {
        toast.success(response.message);

        const updatedControlsData = controlsData.map((section) => ({
          ...section,
          controls: (section.controls || []).filter(
            (c) =>
              c.id !== deletingControl.id && c._uiKey !== deletingControl._uiKey
          ),
        }));

        setLocalDocument((prev) => ({
          ...prev,
          aiExtraction: {
            ...prev.aiExtraction,
            controls: {
              ...prev.aiExtraction.controls,
              controls_data: updatedControlsData,
              total_controls: prev.aiExtraction.controls.total_controls - 1,
            },
          },
        }));

        if (onSuccess) {
          onSuccess();
        }

        setDeletingControl(null);
      } else {
        toast.error(response.message || "Failed to delete control");
      }
    } catch (error) {
      toast.error(error.message || "Error deleting control");
    }
  };

  const handleEditSectionSubmit = async (updatedSection) => {
    try {
      const response = await updateDeploymentFrameworkSection(
        frameworkId,
        packageVersion,
        updatedSection.id,
        { name: updatedSection.name }
      );
      if (response.success) {
        toast.success(response.message);
        const newName = updatedSection.name;

        const updatedControlsData = controlsData.map((section) =>
          String(section.id) === String(updatedSection.id)
            ? { ...section, name: newName }
            : section
        );

        setLocalDocument((prev) => ({
          ...prev,
          aiExtraction: {
            ...prev.aiExtraction,
            controls: {
              ...prev.aiExtraction.controls,
              controls_data: updatedControlsData,
            },
          },
        }));

        if (onSuccess) {
          onSuccess();
        }

        setSectionToEdit(null);
      } else {
        toast.error(response.message || "Failed to update section");
      }
    } catch (error) {
      console.error("Update section error:", error);
      toast.error(error?.message || "Failed to update section");
    }
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="sm:max-w-7xl w-full h-fit flex flex-col overflow-hidden p-0">
          <ModalHeader
            icon="document"
            title="Extracted Controls"
            description={`${localDocument.originalFileName}`}
            className="shrink-0 pl-3 pr-8"
            globalSearch={globalSearch}
            setGlobalSearch={setGlobalSearch}
            placeholder="Search Sections, Controls & DPs..."
            isGlobalSearch={true}
          />
          <div className="flex-1 overflow-hidden p-2">
            <ControlsPanel
              sections={controlsData}
              totalSections={totalSections}
              totalControls={totalControls}
              canModify={true}
              onAdd={handleAddControl}
              onEdit={(control) => setEditingControl(control)}
              onDelete={(control) => setDeletingControl(control)}
              onEditSection={(section) => setSectionToEdit(section)}
              globalSearch={globalSearch}
              onUpdateWeightage={handleWeightageChange}
            />
          </div>
        </DialogContent>
      </Dialog>

      {editingControl && (
        <ControlModal
          type="edit"
          open={!!editingControl}
          control={editingControl}
          sections={controlsData}
          onSave={handleEditSubmit}
          onCancel={() => setEditingControl(null)}
        />
      )}

      {deletingControl && (
        <ControlModal
          type="delete"
          open={!!deletingControl}
          control={deletingControl}
          onConfirm={handleDeleteSubmit}
          onCancel={() => setDeletingControl(null)}
        />
      )}

      {sectionToEdit && (
        <UpdateSectionModal
          open={!!sectionToEdit}
          onCancel={() => setSectionToEdit(null)}
          onSave={handleEditSectionSubmit}
          section={sectionToEdit}
        />
      )}
    </>
  );
}
