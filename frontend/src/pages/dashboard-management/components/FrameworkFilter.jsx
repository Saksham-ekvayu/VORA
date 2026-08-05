/* eslint-disable react/prop-types */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { CheckIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { DropdownMenuSeparator } from "@/components/ui/dropdown-menu";

export default function FrameworkFilter({ frameworks, selectedId, onChange }) {
  const [open, setOpen] = useState(false);
  const activeId = selectedId || "all";

  const getSelectedName = () => {
    if (activeId === "all") return "All Frameworks";
    return (
      frameworks?.find((f) => f.id === activeId)?.frameworkName ||
      "All Frameworks"
    );
  };

  const handleSelect = (id) => {
    onChange(id);
    setOpen(false);
  };

  return (
    <div>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className={cn(
              "flex items-center gap-2 text-xs font-medium max-w-50",
              "border-border bg-accent hover:border-primary hover:bg-primary/10",
              open && "border-primary bg-primary/10"
            )}
          >
            <span className="truncate">{getSelectedName()}</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-72 p-1.5 shadow-2xl">
          <p className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1">
            Filter by Framework
          </p>
          <DropdownMenuSeparator />
          <div className="space-y-0.5 max-h-75 overflow-y-auto">
            <button
              type="button"
              onClick={() => handleSelect("all")}
              className={cn(
                "w-full flex items-center justify-between rounded px-2 py-1.5 text-sm text-left transition-colors cursor-pointer",
                activeId === "all"
                  ? "bg-primary/15 text-primary font-medium"
                  : "text-foreground hover:bg-accent"
              )}
            >
              All Frameworks
              {activeId === "all" && (
                <CheckIcon className="size-3.5 shrink-0" />
              )}
            </button>

            {frameworks?.map((framework) => {
              const active = activeId === framework.id;
              return (
                <button
                  key={framework.id}
                  type="button"
                  onClick={() => handleSelect(framework.id)}
                  className={cn(
                    "w-full flex items-center justify-between rounded px-2 py-1.5 text-sm text-left transition-colors cursor-pointer",
                    active
                      ? "bg-primary/15 text-primary font-medium"
                      : "text-foreground hover:bg-accent"
                  )}
                >
                  <div className="flex flex-col items-start truncate pr-2 w-full">
                    <span className="truncate w-full text-sm leading-tight">
                      {framework.frameworkName}
                    </span>
                    {framework.frameworkVersion && (
                      <span className="truncate w-full text-[11px] text-muted-foreground mt-0.5 font-normal">
                        {framework.frameworkVersion}
                      </span>
                    )}
                  </div>
                  {active && <CheckIcon className="size-3.5 shrink-0" />}
                </button>
              );
            })}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
