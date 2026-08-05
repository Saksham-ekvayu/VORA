/* eslint-disable react/prop-types */
import Icon from "@/components/custom/Icon";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalHeader } from "@/components/custom/modal";
import { cn } from "@/lib/utils";

/**
 * RecordTimelineViewModal - Reusable modal to view entity details and lifecycle history timeline.
 *
 * @param {boolean} isOpen - Dialog state
 * @param {Function} onClose - Close handler
 * @param {string} title - Modal title
 * @param {string} icon - Header icon name
 * @param {string} recordId - Unique identifier of the record
 * @param {string} status - Current status of the record
 * @param {Object} statusConfigs - Custom color/icon configurations for status values
 * @param {Array} infoItems - Array of { label, value, icon } displayed in the header bar
 * @param {Object} leftEntity - Configuration of the left metadata card (e.g. Expert or Customer)
 *    { title, icon, name, email, role }
 * @param {Object} rightEntity - Configuration of the right metadata card (e.g. Framework or Category)
 *    { title, icon, name, code, version, isActive }
 * @param {string} description - Brief paragraph description displayed below cards
 * @param {Array} timelineEvents - Array of events displayed in the timeline:
 *    { title, date, actor, email, reason, icon, color, bgColor }
 * @param {Array} timestamps - Array of timestamps displayed at the bottom:
 *    { label, date }
 */
export default function RecordTimelineViewModal({
  isOpen = true,
  onClose,
  title,
  icon = "eye",
  recordId,
  status,
  statusConfigs = {},
  infoItems = [],
  leftEntity = {},
  rightEntity = {},
  description,
  timelineEvents = [],
  timestamps = [],
}) {
  const defaultStatusConfigs = {
    approved: {
      bg: "bg-emerald-50 dark:bg-emerald-950/30",
      text: "text-emerald-700 dark:text-emerald-400",
      border: "border-emerald-200 dark:border-emerald-800",
      icon: "check-circle",
      label: "Approved",
    },
    assigned: {
      bg: "bg-emerald-50 dark:bg-emerald-950/30",
      text: "text-emerald-700 dark:text-emerald-400",
      border: "border-emerald-200 dark:border-emerald-800",
      icon: "check-circle",
      label: "Assigned",
    },
    rejected: {
      bg: "bg-rose-50 dark:bg-rose-950/30",
      text: "text-rose-700 dark:text-rose-400",
      border: "border-rose-200 dark:border-rose-800",
      icon: "x-circle",
      label: "Rejected",
    },
    revoked: {
      bg: "bg-orange-50 dark:bg-orange-950/30",
      text: "text-orange-700 dark:text-orange-400",
      border: "border-orange-200 dark:border-orange-800",
      icon: "alert-circle",
      label: "Revoked",
    },
    pending: {
      bg: "bg-amber-50 dark:bg-amber-950/30",
      text: "text-amber-700 dark:text-amber-400",
      border: "border-amber-200 dark:border-amber-800",
      icon: "clock",
      label: "Pending",
    },
  };

  const currentStatusConfig =
    statusConfigs[status] ||
    defaultStatusConfigs[status] ||
    defaultStatusConfigs.pending;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="lg:max-w-3xl p-0 gap-0 overflow-hidden">
        <ModalHeader
          icon={icon}
          title={title}
          description="View detailed record information"
        />

        {/* Quick Info Bar */}
        <div className="relative bg-primary/90 px-5 py-2 flex flex-wrap items-center gap-3 text-xs text-white/90">
          {recordId && (
            <div className="flex items-center gap-1.5 bg-white/5 px-2 py-1 rounded">
              <span className="text-white/70 text-[10px] font-medium">ID:</span>
              <span className="font-mono font-medium text-white/90">
                {recordId.slice(-8)}
              </span>
            </div>
          )}

          {infoItems.map((item) => (
            <div
              key={item.label}
              className="flex items-center gap-1.5 bg-white/5 px-2 py-1 rounded"
            >
              {item.icon && (
                <Icon name={item.icon} size="12px" className="text-white/60" />
              )}
              <span className="text-white/70 text-[10px] font-medium">
                {item.label}:
              </span>
              <span className="font-medium text-white/90">{item.value}</span>
            </div>
          ))}

          <div
            className={cn(
              "px-3 py-1 rounded-full border backdrop-blur-sm ml-auto",
              currentStatusConfig.bg,
              currentStatusConfig.border,
              currentStatusConfig.text
            )}
          >
            <div className="flex items-center gap-1.5">
              <Icon name={currentStatusConfig.icon} size="12px" />
              <span className="text-xs font-medium">
                {currentStatusConfig.label}
              </span>
            </div>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="p-4 space-y-4 overflow-y-auto sidebar-scroll max-h-[60vh]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Left Card */}
            {leftEntity.name && (
              <div className="bg-card rounded border p-3">
                <div className="flex items-start gap-2">
                  <div className="p-1.5 rounded bg-primary/10 text-primary shrink-0 flex items-center justify-center">
                    <Icon name={leftEntity.icon || "user"} size="16px" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-medium text-muted-foreground">
                      {leftEntity.title}
                    </p>
                    <h4 className="font-semibold text-foreground text-sm truncate">
                      {leftEntity.name}
                    </h4>
                    {leftEntity.email && (
                      <p className="text-xs text-muted-foreground truncate">
                        {leftEntity.email}
                      </p>
                    )}
                    {leftEntity.role && (
                      <span className="inline-block mt-1 text-[10px] bg-muted px-1.5 py-0.5 rounded-full text-muted-foreground uppercase tracking-wider">
                        {leftEntity.role}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Right Card */}
            {rightEntity.name && (
              <div className="bg-card rounded border p-3">
                <div className="flex items-start gap-2">
                  <div className="p-1.5 rounded bg-secondary/10 text-secondary shrink-0 flex items-center justify-center">
                    <Icon name={rightEntity.icon || "shield"} size="16px" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-medium text-muted-foreground">
                      {rightEntity.title}
                    </p>
                    <h4 className="font-semibold text-foreground text-sm truncate">
                      {rightEntity.name}
                    </h4>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      {rightEntity.code && (
                        <span className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded-full">
                          {rightEntity.code}
                        </span>
                      )}
                      {rightEntity.version && (
                        <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded-full text-muted-foreground">
                          version: {rightEntity.version}
                        </span>
                      )}
                      {rightEntity.isActive !== undefined && (
                        <span
                          className={cn(
                            "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                            rightEntity.isActive
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400"
                              : "bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-400"
                          )}
                        >
                          {rightEntity.isActive ? "Active" : "Inactive"}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Description */}
          {description && (
            <div className="bg-card rounded border p-3">
              <p className="text-xs text-muted-foreground leading-relaxed">
                {description}
              </p>
            </div>
          )}

          {/* Timeline events */}
          {timelineEvents.length > 0 && (
            <div className="bg-card rounded border overflow-hidden">
              <div className="px-3 py-2 border-b bg-muted/30">
                <div className="flex items-center gap-1.5">
                  <Icon name="activity" size="14px" className="text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">
                    Timeline
                  </h3>
                </div>
              </div>
              <div className="p-3">
                <div className="relative">
                  <div className="absolute left-4 top-2 bottom-2 w-0.5 bg-border/60" />
                  <div className="space-y-3">
                    {timelineEvents.map((event) => (
                      <div key={event.email} className="relative flex gap-3">
                        <div
                          className={cn(
                            "relative z-10 w-7 h-7 rounded-full flex items-center justify-center shrink-0 border border-background",
                            event.bgColor || "bg-muted"
                          )}
                        >
                          <Icon
                            name={event.icon || "circle"}
                            size="12px"
                            className={event.color || "text-muted-foreground"}
                          />
                        </div>
                        <div className="flex-1 pb-2">
                          <div className="flex flex-wrap items-center gap-2 mb-0.5">
                            <span className="text-xs font-medium text-foreground">
                              {event.title}
                            </span>
                            {event.date && (
                              <span className="text-[10px] text-muted-foreground">
                                {formatDateWithMonthNameAndTime(event.date)}
                              </span>
                            )}
                          </div>
                          <div className="bg-muted/30 rounded p-2 border">
                            {event.actor && (
                              <div className="flex items-center gap-1.5 text-xs">
                                <Icon
                                  name="user"
                                  size="10px"
                                  className="text-muted-foreground"
                                />
                                <span className="font-medium text-foreground text-xs">
                                  {event.actor}
                                </span>
                                {event.email && (
                                  <span className="text-[10px] text-muted-foreground truncate max-w-37.5">
                                    {event.email}
                                  </span>
                                )}
                              </div>
                            )}
                            {event.reason && (
                              <div className="mt-1.5 text-[10px] text-muted-foreground bg-background/50 p-1.5 rounded border">
                                <span className="font-medium text-foreground">
                                  Reason:{" "}
                                </span>
                                {event.reason}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Timestamps */}
          {timestamps.length > 0 && (
            <div className="bg-card rounded border p-3">
              <div className="flex items-center gap-1.5 mb-2 border-b pb-1.5 text-muted-foreground">
                <Icon name="clock" size="12px" />
                <h3 className="text-sm font-semibold text-foreground">
                  Record Dates
                </h3>
              </div>
              <dl className="space-y-1.5">
                {timestamps.map(
                  (ts) =>
                    ts.date && (
                      <div
                        key={ts.label}
                        className="flex justify-between text-xs"
                      >
                        <dt className="text-muted-foreground">{ts.label}</dt>
                        <dd className="text-foreground">
                          {formatDateWithMonthNameAndTime(ts.date)}
                        </dd>
                      </div>
                    )
                )}
              </dl>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
