/* eslint-disable react/prop-types */
import { Button } from "../ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "../ui/dropdown-menu";
import Icon from "./Icon";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

/**
 * Reusable TableHeaderActions component to render custom buttons or dropdowns
 * in tables or card grids.
 *
 * @param {object} props
 * @param {Array} props.actions - Array of action config objects
 */
export default function TableHeaderActions({ actions = [] }) {
  if (!actions) return null;

  return actions
    .flat()
    .filter(Boolean)
    .map((action) => {
      if (action.type === "dropdown") {
        return (
          <DropdownMenu key={`header-dropdown-${action.label}`}>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className={cn(
                  "justify-between border-border dark:border-gray-600 dark:hover:border-gray-500 dark:bg-gray-800 text-muted-foreground dark:hover:bg-gray-700",
                  action.triggerClassName || "w-32"
                )}
              >
                {action.label}
                <ChevronDown className="h-4 w-4 opacity-50 dark:text-gray-400" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className={cn(
                "border-border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200",
                action.triggerClassName || "w-32"
              )}
            >
              {action.options.map((opt) => (
                <div key={`header-opt-${opt.label}`}>
                  {opt.separatorBefore && <DropdownMenuSeparator />}
                  <DropdownMenuItem
                    onClick={opt.onClick}
                    className="cursor-pointer dark:focus:bg-gray-700 dark:focus:text-white capitalize"
                  >
                    {opt.label}
                  </DropdownMenuItem>
                </div>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      }

      if (action.type === "button") {
        return (
          <Button
            key={`header-btn-${action.label}`}
            size={action.size || "sm"}
            variant={action.variant || "default"}
            onClick={action.onClick}
            disabled={action.disabled}
            className={cn(
              "flex items-center gap-2 font-bold transition-all",
              action.className
            )}
          >
            {action.icon && <Icon name={action.icon} size="18px" />}
            {action.label}
          </Button>
        );
      }

      return null;
    });
}
