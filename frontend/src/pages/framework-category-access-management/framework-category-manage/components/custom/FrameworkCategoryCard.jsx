/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import CustomBadge from "@/components/custom/CustomBadge";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import UserAvatar from "@/components/custom/UserAvatar";
import { cn } from "@/lib/utils";

const getRequestStatusColor = (status) => {
  if (status === "approved") return "green";
  if (status === "rejected" || status === "revoked") return "red";
  return "yellow";
};

const FrameworkCategoryCard = ({ category, renderActions }) => {
  const {
    code,
    frameworkCategoryName,
    description,
    isActive,
    hasRequested,
    requestStatus,
    createdAt,
    createdBy,
  } = category;

  return (
    <div className="bg-card border border-border group rounded overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 flex flex-col h-full border-b-[3px] border-b-transparent hover:border-b-primary">
      {/* Card Header */}
      <div className="p-2 flex flex-col gap-1">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded bg-primary/10 text-primary flex items-center justify-center">
              <Icon name="category" size="14px" />
            </div>
            <div className="flex flex-col">
              <h3 className="text-sm font-bold text-foreground leading-tight line-clamp-1">
                {frameworkCategoryName}
              </h3>
              <span className="text-[11px] font-bold uppercase tracking-wider text-foreground truncate max-w-25">
                {code}
              </span>
            </div>
          </div>
          {renderActions?.(category)}
        </div>

        {/* Description Section */}
        <div className="mt-2 p-2 bg-muted/30 rounded border border-border/40 min-h-15">
          <p className="text-[11px] text-muted-foreground line-clamp-3 leading-relaxed">
            {description ||
              "No description provided for this framework category."}
          </p>
        </div>

        {/* Status Section */}
        <div
          className={cn(
            "mt-2 grid gap-2 px-1",
            hasRequested === undefined ? "grid-cols-1" : "grid-cols-2"
          )}
        >
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-muted-foreground uppercase opacity-60">
              System Status
            </span>
            <CustomBadge size="sm" isActive={isActive} className="w-fit" />
          </div>

          {hasRequested !== undefined && (
            <div className="flex flex-col gap-1 text-right">
              <span className="text-[10px] font-bold text-muted-foreground uppercase opacity-60">
                Request Status
              </span>
              <div className="flex justify-end">
                <CustomBadge
                  size="sm"
                  label={
                    requestStatus === "not_requested" || !requestStatus
                      ? "Not Requested"
                      : requestStatus
                  }
                  color={getRequestStatusColor(requestStatus)}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* User Info (Footer) */}
      <div className="mt-auto px-3.5 py-2.5 bg-muted/10 border-t border-border/50 flex items-center gap-2.5">
        <UserAvatar user={createdBy} />
        <div className="flex justify-between w-full">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-foreground truncate leading-none">
              {createdBy?.name || "System Admin"}
            </span>
            <span className="text-[10px] text-muted-foreground truncate leading-none">
              {createdBy?.email}
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground mt-1 font-medium">
            {formatDateWithMonthNameAndTime(createdAt)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default FrameworkCategoryCard;
