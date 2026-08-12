import { Dialog, DialogContent } from "@/components/ui/dialog";
import ControlsPanel from "@/components/custom/ControlsPanel";
import { ModalHeader } from "@/components/custom/modal";

export default function DocumentControlsModal({ isOpen, onClose, document }) {
  if (!isOpen || !document) return null;

  const controlsData = document?.aiExtraction?.controls?.controls_data || [];
  const totalSections =
    document?.aiExtraction?.controls?.total_sections || controlsData.length;
  const totalControls = document?.aiExtraction?.controls?.total_controls || 0;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-7xl w-full h-fit flex flex-col overflow-hidden p-0">
        <ModalHeader
          icon="document"
          title="Extracted Controls"
          description={`${document.originalFileName}`}
          className="shrink-0 pl-3 pr-8"
        />
        <div className="flex-1 overflow-hidden p-2">
          <ControlsPanel
            sections={controlsData}
            totalSections={totalSections}
            totalControls={totalControls}
            canModify={false}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
