/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { Button } from "@/components/ui/button";
import CustomBadge from "@/components/custom/CustomBadge";
import UserAvatar from "@/components/custom/UserAvatar";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";

const AssignedFrameworkCard = ({
  framework,
  onDownload,
  onNavigate,
  renderActions,
  isDownloading,
}) => {
  const {
    id,
    frameworkCode,
    frameworkName,
    frameworkVersion,
    status,
    assignment,
    revocation,
    assignedAt,
  } = framework;

  const getActorMetadata = () => {
    if (status === "revoked" && revocation?.revokedBy) {
      return {
        label: "Revoked By",
        user: revocation.revokedBy,
        date: revocation.revokedAt,
      };
    }

    if (assignment?.assignedBy) {
      return {
        label: "Assigned By",
        user: assignment.assignedBy,
        date: assignment?.assignedAt || assignedAt,
      };
    }

    return {
      label: "Assigned By",
      user: null,
      date: assignedAt,
    };
  };

  const actionMeta = getActorMetadata();

  return (
    <div className="bg-card border border-border group rounded overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 flex flex-col h-full border-b-[3px] border-b-transparent hover:border-b-primary">
      {/* Card Header */}
      <div className="p-2 flex flex-col gap-1">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded bg-primary/10 text-primary flex items-center justify-center">
              <Icon name="shield" size="14px" />
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] font-bold uppercase tracking-wider text-foreground truncate max-w-25">
                {frameworkCode}
              </span>
              <p className="text-[10px] text-muted-foreground font-medium">
                Version: {frameworkVersion}
              </p>
            </div>
          </div>
          {/* Status Indicator */}
          <div className="flex items-center gap-1.5">
            <CustomBadge status={status} size="sm" />
            <CustomBadge
              size="sm"
              status={
                framework.finalization?.isFinalized
                  ? "Finalized"
                  : "Not Finalize"
              }
            />
          </div>
          {renderActions?.(framework)}
        </div>

        <div className="mt-1">
          <h3 className="text-sm font-bold text-foreground leading-tight line-clamp-2">
            {frameworkName}
          </h3>
        </div>

        {/* Assignment Info Section */}
        <div className="flex flex-col gap-2 p-2 bg-muted/30 rounded border border-border/40 mt-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-muted-foreground uppercase opacity-60">
              {status === "revoked" ? "Revoked At" : "Assigned At"}
            </span>
            <div className="flex items-center gap-1 text-[10px] font-semibold text-foreground">
              <Icon name="calendar" size="10px" className="opacity-60" />
              <span>{formatDateWithMonthNameAndTime(actionMeta.date)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer / Meta Info */}
      <div className="mt-auto px-3 py-2 bg-muted/10 border-t border-border/50">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex flex-col flex-1 min-w-0">
            <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
              {actionMeta.label}
            </span>
            <div className="flex items-center gap-1">
              <UserAvatar user={actionMeta.user} />
              <div className="flex flex-col">
                <span className="text-[12px] font-bold text-foreground truncate">
                  {actionMeta.user?.name || "System"}
                </span>
                <span className="text-[11px] font-semibold text-foreground truncate">
                  {actionMeta.user?.email || "N/A"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="p-1 bg-card border-t border-border/50 flex items-center gap-2">
        <Button
          variant="secondary"
          className="flex-1 h-8 text-[11px] font-bold rounded transition-all duration-200 bg-primary/5 hover:bg-primary/20 text-primary border border-primary/10"
          onClick={() => onNavigate(id)}
        >
          View
        </Button>
        <Button
          variant="outline"
          className="flex-1 h-8 text-[11px] font-bold rounded"
          onClick={() => onDownload?.(framework)}
          disabled={isDownloading}
        >
          {isDownloading ? (
            <>
              <Icon name="loader" size="12px" className="mr-1.5 spin" />
              Downloading...
            </>
          ) : (
            <>
              <Icon name="download" size="12px" className="mr-1.5" />
              Get
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

export default AssignedFrameworkCard;
