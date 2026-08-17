import { useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ChevronDownIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { startMcpScheduler } from "@/services/mcpService";
import { ModalHeader } from "@/components/custom/modal";
import Icon from "@/components/custom/Icon";

export default function McpSchedulerModal({ isOpen, onClose, onStatusChange }) {
  const [source, setSource] = useState("local");
  const [schedulerType, setSchedulerType] = useState("interval");
  const [minutes, setMinutes] = useState(1);
  const [hour, setHour] = useState(0);
  const [minute, setMinute] = useState(0);
  const [isStarting, setIsStarting] = useState(false);

  const handleStart = async (e) => {
    e.preventDefault();
    setIsStarting(true);
    try {
      const res = await startMcpScheduler({
        source,
        scheduler_type: schedulerType,
        minutes: Number(minutes),
        hour: Number(hour),
        minute: Number(minute),
      });
      toast.success(res.message || "MCP Scheduler started successfully");
      if (onStatusChange) onStatusChange();
      onClose();
    } catch (error) {
      toast.error(error.message || "Failed to start MCP Scheduler");
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="p-0 overflow-hidden sm:max-w-lg">
        <ModalHeader
          icon="clock"
          title="Configure MCP Scheduler"
          description="Configure how often VORA should automatically run evidence retrieval."
        />

        <form onSubmit={handleStart} className="flex flex-col">
          <div className="flex flex-col gap-4 p-2">
            <div className="space-y-1.5">
              <Label htmlFor="source">
                Source <span className="text-red-500">*</span>
              </Label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between font-normal text-sm h-10 px-3 border-input"
                  >
                    {source === "local" ? "Local" : "AWS"}
                    <ChevronDownIcon className="size-4 opacity-50 ml-2" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  style={{ width: "var(--radix-dropdown-menu-trigger-width)" }}
                >
                  <DropdownMenuItem onClick={() => setSource("local")}>
                    Local
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSource("aws")}>
                    AWS
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="schedulerType">
                Schedule Type <span className="text-red-500">*</span>
              </Label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between font-normal text-sm h-10 px-3 border-input"
                  >
                    {schedulerType === "interval"
                      ? "Interval (Minutes)"
                      : "Daily (Time)"}
                    <ChevronDownIcon className="size-4 opacity-50 ml-2" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  style={{ width: "var(--radix-dropdown-menu-trigger-width)" }}
                >
                  <DropdownMenuItem
                    onClick={() => setSchedulerType("interval")}
                  >
                    Interval (Minutes)
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSchedulerType("daily")}>
                    Daily (Time)
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {schedulerType === "interval" && (
              <div className="space-y-1.5">
                <Label htmlFor="minutes">
                  Minutes <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="minutes"
                  type="number"
                  min="1"
                  value={minutes}
                  onChange={(e) => setMinutes(e.target.value)}
                  required
                />
              </div>
            )}

            {schedulerType === "daily" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="hour">
                    Hour (0-23) <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="hour"
                    type="number"
                    min="0"
                    max="23"
                    value={hour}
                    onChange={(e) => setHour(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="minute">
                    Minute (0-59) <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="minute"
                    type="number"
                    min="0"
                    max="59"
                    value={minute}
                    onChange={(e) => setMinute(e.target.value)}
                    required
                  />
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="pt-4 border-t border-border p-2 flex items-center justify-end">
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isStarting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isStarting}>
                {isStarting ? (
                  <>
                    <Icon
                      name="loader"
                      size="16px"
                      className="animate-spin mr-2"
                    />
                    Starting...
                  </>
                ) : (
                  <>
                    <Icon name="check" size="16px" className="mr-2" />
                    Start Monitoring
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
