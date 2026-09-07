/* eslint-disable react/prop-types */

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalHeader } from "@/components/custom/modal";
import Icon from "@/components/custom/Icon";
import UserAvatar from "@/components/custom/UserAvatar";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";

/**
 * AssignmentHistoryModal Component - Shows assignment and revocation history
 *
 * @param {Object} framework - Framework assignment data
 * @param {Function} onClose - Close handler
 */
export default function AssignmentHistoryModal({ framework, onClose }) {
  if (!framework) return null;

  // Build history array with both assignment and revocation events
  const history = [];

  if (framework.assignment?.assignedAt) {
    history.push({
      type: "assigned",
      date: new Date(framework.assignment.assignedAt),
      user: framework.assignment.assignedBy,
      label: "Assigned",
      icon: "check-circle",
      color: "text-green-600 dark:text-green-400",
    });
  }

  if (framework.revocation?.revokedAt) {
    history.push({
      type: "revoked",
      date: new Date(framework.revocation.revokedAt),
      user: framework.revocation.revokedBy,
      label: "Revoked",
      icon: "x-circle",
      color: "text-red-600 dark:text-red-400",
    });
  }

  // Sort by date descending (latest first)
  history.sort((a, b) => b.date - a.date);

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="lg:max-w-md">
        <ModalHeader
          icon="history"
          title="Assignment History"
          description="Timeline of assignment and revocation events"
        />

        <div className="flex flex-col gap-4 p-2 max-h-96 overflow-y-auto">
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No history available
            </p>
          ) : (
            <div className="space-y-4 p-4">
              {history.map((event) => (
                <div
                  key={`${event.type}-${event.date.getTime()}`}
                  className="flex gap-3"
                >
                  {/* Timeline line */}
                  <div className="flex flex-col items-center">
                    <div
                      className={`p-2 rounded-full flex items-center justify-center ${
                        event.type === "assigned"
                          ? "bg-green-500/15"
                          : "bg-red-500/15"
                      }`}
                    >
                      <Icon
                        name={event.icon}
                        size="14px"
                        className={event.color}
                      />
                    </div>
                    {history.indexOf(event) < history.length - 1 && (
                      <div className="w-0.5 h-8 bg-border mt-2" />
                    )}
                  </div>

                  {/* Event details */}
                  <div className="flex-1 pt-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-xs font-bold uppercase ${event.color}`}
                      >
                        {event.label}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {formatDateWithMonthNameAndTime(event.date)}
                      </span>
                    </div>

                    {event.user ? (
                      <div className="flex items-center gap-2">
                        <UserAvatar
                          user={event.user}
                          size="xs"
                          className="shrink-0"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-foreground truncate">
                            {event.user.name}
                          </p>
                          <p className="text-[10px] text-muted-foreground truncate">
                            {event.user.email}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">
                        System / Unknown
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
