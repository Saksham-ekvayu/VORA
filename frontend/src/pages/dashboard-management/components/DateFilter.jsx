/* eslint-disable react/prop-types */

import { useState } from "react";
import { CalendarIcon, CheckIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { getPresetRange } from "../hooks/useDateFilter";
import { DropdownMenuSeparator } from "@/components/ui/dropdown-menu";

const PRESETS = [
  { label: "Today", value: "today" },
  { label: "Last 7 Days", value: "7d" },
  { label: "Last 30 Days", value: "30d" },
  { label: "Last 90 Days", value: "90d" },
  { label: "Last 180 Days", value: "180d" },
  { label: "Custom Range", value: "custom" },
];

function toInputDate(iso) {
  if (!iso) return "";
  return new Date(iso).toISOString().slice(0, 10);
}

function formatDisplay(preset, startDate, endDate) {
  if (preset === "custom" && startDate && endDate) {
    const fmt = (d) =>
      new Date(d).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    return `${fmt(startDate)} – ${fmt(endDate)}`;
  }
  return PRESETS.find((p) => p.value === preset)?.label ?? "Select Range";
}

/**
 * DateFilter — a Popover-based date range picker built on shadcn/ui.
 *
 * Props:
 *   value      – active preset key ("today" | "7d" | "30d" | "90d" | "custom")
 *   startDate  – ISO string (confirmed, from parent)
 *   endDate    – ISO string (confirmed, from parent)
 *   onChange   – (preset, startDate, endDate) => void  — called ONLY on confirm
 */
export default function DateFilter({
  value = "180d",
  startDate,
  endDate,
  onChange,
}) {
  const [open, setOpen] = useState(false);

  // Internal draft state — never triggers parent refresh until Apply is clicked
  const [draftPreset, setDraftPreset] = useState(value);
  const [draftStart, setDraftStart] = useState(toInputDate(startDate));
  const [draftEnd, setDraftEnd] = useState(toInputDate(endDate));

  const handleOpenChange = (next) => {
    if (next) {
      // Reset draft to match current confirmed state when opening
      setDraftPreset(value);
      setDraftStart(toInputDate(startDate));
      setDraftEnd(toInputDate(endDate));
    }
    setOpen(next);
  };

  const handlePresetClick = (preset) => {
    if (preset === "custom") {
      setDraftPreset("custom");
      return;
    }

    // Non-custom presets apply immediately and close the popover
    const range = getPresetRange(preset);

    onChange(preset, range.startDate, range.endDate);

    setDraftPreset(preset);
    setOpen(false);
  };

  const today = new Date().toISOString().slice(0, 10);

  const validationError = (() => {
    if (!draftStart && !draftEnd) return null; // untouched, no error yet
    if (draftStart && !draftEnd) return "Please select an end date.";
    if (!draftStart && draftEnd) return "Please select a start date.";
    if (draftStart > today) return "Start date cannot be in the future.";
    if (draftEnd > today) return "End date cannot be in the future.";
    if (draftStart > draftEnd) return "End date must be after start date.";
    return null;
  })();

  const canApply = !!draftStart && !!draftEnd && !validationError;

  const handleApply = () => {
    if (!canApply) return;
    const start = new Date(draftStart);
    start.setHours(0, 0, 0, 0);
    const end = new Date(draftEnd);
    end.setHours(23, 59, 59, 999);
    onChange("custom", start.toISOString(), end.toISOString());
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          id="date-filter-trigger"
          variant="outline"
          size="sm"
          className={cn(
            "flex items-center gap-2 text-xs font-medium",
            "border-border bg-accent hover:border-primary hover:bg-primary/10",
            open && "border-primary bg-primary/10"
          )}
        >
          <CalendarIcon className="size-3.5 text-primary shrink-0" />
          <span className="max-w-50 truncate">
            {formatDisplay(value, startDate, endDate)}
          </span>
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-72 p-0 shadow-2xl"
      >
        {/* Preset list */}
        <div className="p-1.5 space-y-0.5">
          <p className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            Quick Select
          </p>
          <DropdownMenuSeparator />
          {PRESETS.map((p) => {
            const active = draftPreset === p.value;
            return (
              <button
                key={p.value}
                type="button"
                onClick={() => handlePresetClick(p.value)}
                className={cn(
                  "w-full flex items-center justify-between rounded px-2 py-1.5 text-sm text-left transition-colors cursor-pointer",
                  active
                    ? "bg-primary/15 text-primary font-medium"
                    : "text-foreground hover:bg-accent"
                )}
              >
                {p.label}
                {active && <CheckIcon className="size-3.5 shrink-0" />}
              </button>
            );
          })}
        </div>

        {/* Custom date range inputs — only visible when "Custom Range" is selected */}
        {draftPreset === "custom" && (
          <>
            <div className="border-t border-border p-2 space-y-2">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                Custom Range
              </p>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground font-normal">
                    Start
                  </Label>
                  <Input
                    type="date"
                    value={draftStart}
                    max={today}
                    onChange={(e) => setDraftStart(e.target.value)}
                    className={cn(
                      "h-7 text-xs px-2 cursor-pointer",
                      validationError &&
                        draftStart > today &&
                        "border-destructive focus-visible:ring-destructive"
                    )}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground font-normal">
                    End
                  </Label>
                  <Input
                    type="date"
                    value={draftEnd}
                    max={today}
                    onChange={(e) => setDraftEnd(e.target.value)}
                    className={cn(
                      "h-7 text-xs px-2 cursor-pointer",
                      validationError &&
                        (draftEnd > today || draftStart > draftEnd) &&
                        "border-destructive focus-visible:ring-destructive"
                    )}
                  />
                </div>
              </div>

              {validationError && (
                <p className="text-xs text-destructive">{validationError}</p>
              )}
            </div>

            {/* Footer actions — only for custom range */}
            <div className="border-t border-border p-1.5 flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                size="xs"
                className="text-xs"
                onClick={() => setOpen(false)}
              >
                Cancel
              </Button>
              <Button
                size="xs"
                className="text-xs"
                disabled={!canApply}
                onClick={handleApply}
              >
                Apply
              </Button>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  );
}
