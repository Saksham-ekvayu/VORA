/* eslint-disable react/prop-types */

import {
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import Icon from "../Icon";

/**
 * Reusable Modal Header Component
 * Eliminates duplication across 40+ modal files
 */
export default function ModalHeader({
  icon,
  title,
  description,
  className = "",
}) {
  return (
    <DialogHeader
      className={`flex flex-row items-center justify-between bg-linear-to-br from-primary to-primary/80 text-white py-2 ${className}`}
    >
      <div className="flex items-center gap-3 w-full">
        {icon && <Icon name={icon} size="24px" />}
        <div className="w-full">
          <DialogTitle className="text-xl font-bold text-white drop-shadow-sm">
            {title}
          </DialogTitle>
          {description && (
            <DialogDescription className="text-white text-xs max-w-[90%] text-justify">
              {description}
            </DialogDescription>
          )}
        </div>
      </div>
    </DialogHeader>
  );
}
