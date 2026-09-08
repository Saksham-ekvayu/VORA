import { useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ModalHeader } from "@/components/custom/modal";
import Icon from "@/components/custom/Icon";

export default function BulkSetupModal({
  isOpen,
  onClose,
  selectedFw,
  onApply,
}) {
  const [pathVal, setPathVal] = useState("");
  const [sourceVal, setSourceVal] = useState("");
  const [isApplying, setIsApplying] = useState(false);

  const handleApply = async (e) => {
    e.preventDefault();
    if (!pathVal.trim() || !sourceVal.trim()) {
      toast.error("Both path and source are required for bulk setup");
      return;
    }
    setIsApplying(true);
    await onApply(pathVal, sourceVal);
    setIsApplying(false);
    onClose();
    setPathVal("");
    setSourceVal("");
  };

  const handleClose = () => {
    onClose();
    setPathVal("");
    setSourceVal("");
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="p-0 overflow-hidden sm:max-w-lg">
        <ModalHeader
          icon="layers"
          title="Bulk Configure Monitoring Points"
          description="Apply the same path and source to all deployment points. Existing configurations will be overwritten."
        />

        <form onSubmit={handleApply} className="flex flex-col">
          <div className="flex flex-col gap-4 p-2">
            <div className="bg-primary/10 border border-primary/20 text-primary-foreground p-3 rounded text-sm text-center flex flex-col gap-0.5">
              <span className="text-primary font-semibold leading-tight">
                Deployment Framework: {selectedFw?.frameworkName}
              </span>
              {(selectedFw?.frameworkVersion ||
                selectedFw?.package?.packageVersion ||
                selectedFw?.packageVersion) && (
                <span className="text-xs text-primary/80 font-medium">
                  {selectedFw?.frameworkVersion &&
                    `${selectedFw.frameworkVersion}`}
                  {selectedFw?.frameworkVersion &&
                    (selectedFw?.package?.packageVersion ||
                      selectedFw?.packageVersion) &&
                    " | "}
                  {(selectedFw?.package?.packageVersion ||
                    selectedFw?.packageVersion) &&
                    `Package v${selectedFw?.package?.packageVersion || selectedFw?.packageVersion}`}
                </span>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="path">
                Path <span className="text-red-500">*</span>
              </Label>
              <Input
                id="path"
                type="text"
                placeholder="e.g. C:/USER/VORA/docs"
                value={pathVal}
                onChange={(e) => setPathVal(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="source">
                Source <span className="text-red-500">*</span>
              </Label>
              <Input
                id="source"
                type="text"
                placeholder="e.g. local or aws etc..."
                value={sourceVal}
                onChange={(e) => setSourceVal(e.target.value)}
                required
              />
            </div>
          </div>

          <DialogFooter className="pt-4 border-t border-border p-2 flex items-center justify-end">
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={isApplying}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isApplying || !pathVal.trim() || !sourceVal.trim()}
              >
                {isApplying ? (
                  <>
                    <Icon
                      name="loader"
                      size="16px"
                      className="animate-spin mr-2"
                    />
                    Applying...
                  </>
                ) : (
                  <>
                    <Icon name="check" size="16px" className="mr-2" />
                    Apply to All
                  </>
                )}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
