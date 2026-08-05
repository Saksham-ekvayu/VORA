/* eslint-disable react/prop-types */

import { useState } from "react";
import Icon from "./Icon";
import { Button } from "../ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";

function ActionDropdown({ actions = [] }) {
  const [open, setOpen] = useState(false);
  const [loadingActionId, setLoadingActionId] = useState(null);

  const handleActionClick = async (action, actionId, e) => {
    if (action.onClick && typeof action.onClick === "function") {
      // Prevent Radix from auto-closing the dropdown on click
      e?.preventDefault();
      try {
        setLoadingActionId(actionId);
        const result = action.onClick();
        if (result && typeof result.then === "function") {
          await result;
        }
      } catch (error) {
        console.error("Action error:", error);
      } finally {
        setLoadingActionId(null);
        setOpen(false);
      }
    }
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" title="Actions">
          <Icon name="more-vertical" size="16px" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="overflow-visible p-1" align="end">
        {/* Arrow */}
        <div className="pointer-events-none absolute -top-2 right-3 w-4 h-4 bg-popover border-l border-t border-border rotate-45 -z-10" />
        {actions.map((action, idx) => {
          const actionId = action.id || idx;
          const isLoading = loadingActionId === actionId;
          const isDisabled =
            action.disabled || (loadingActionId !== null && !isLoading);

          return (
            <div key={actionId}>
              <DropdownMenuItem
                onClick={(e) => handleActionClick(action, actionId, e)}
                disabled={isDisabled || isLoading}
                variant={action.variant || "default"}
                className={`gap-1.5 cursor-pointer py-1.5 px-2 text-xs font-normal ${action.className || ""} ${action.hoverClassName || ""}`}
              >
                {isLoading ? (
                  <div className="w-3 h-3 border-2 border-current/30 border-t-current rounded-full animate-spin" />
                ) : (
                  <Icon
                    name={action.icon}
                    size="13px"
                    className="text-current"
                  />
                )}
                <span>{action.label}</span>
              </DropdownMenuItem>
              {idx === actions.length - 2 && <DropdownMenuSeparator />}
            </div>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default ActionDropdown;
