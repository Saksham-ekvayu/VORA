/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import UserMiniCard from "@/components/custom/UserMiniCard";
import { ConfirmModal } from "@/components/custom/modal";

export default function ManageAccessModal({
  type, // "approve" | "reject" | "revoke"
  accessRecord,
  onConfirm,
  onCancel,
}) {
  const config = {
    approve: {
      icon: "check-circle",
      title: "Approve Framework Access",
      description: "Approve framework access request for expert",
      actionLabel: "Approve Access",
      savingLabel: "Approving...",
      actionIcon: "check-circle",
      actionVariant: "default",
      bodyText: "You are about to approve framework access for this expert.",
      borderColor: "border-primary",
      showRequestMessage: true,
      showStatusBadge: false,
    },
    reject: {
      icon: "x-circle",
      title: "Reject Framework Access",
      description: "Reject framework access request for expert",
      actionLabel: "Reject Access",
      savingLabel: "Rejecting...",
      actionIcon: "x-circle",
      actionVariant: "default",
      bodyText: "You are about to reject framework access for this expert.",
      borderColor: "border-red-500",
      showRequestMessage: true,
      showStatusBadge: false,
    },
    revoke: {
      icon: "x-circle",
      title: "Revoke Framework Access",
      description:
        "Revoke framework access for expert. This action cannot be undone.",
      actionLabel: "Revoke Access",
      savingLabel: "Revoking...",
      actionIcon: "x-circle",
      actionVariant: "destructive",
      bodyText:
        "Are you sure you want to revoke framework access for this expert? This action cannot be undone.",
      borderColor: "border-red-500",
      showRequestMessage: false,
      showStatusBadge: true,
    },
  };

  const cfg = config[type] || config.approve;

  return (
    <ConfirmModal
      onCancel={onCancel}
      onConfirm={onConfirm}
      icon={cfg.icon}
      title={cfg.title}
      description={cfg.description}
      actionLabel={cfg.actionLabel}
      savingLabel={cfg.savingLabel}
      actionIcon={cfg.actionIcon}
      actionVariant={cfg.actionVariant}
    >
      <p
        className={
          type === "revoke"
            ? "text-muted-foreground text-xs leading-relaxed"
            : "text-muted-foreground text-sm leading-relaxed"
        }
      >
        {cfg.bodyText}
      </p>

      <div className={`bg-muted rounded p-3 border-l-4 ${cfg.borderColor}`}>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <UserMiniCard
              name={accessRecord?.expert?.name}
              email={accessRecord?.expert?.email}
              avatar={accessRecord?.expert?.avatar}
            />
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
              <Icon
                name="shield"
                size="20px"
                className="text-purple-600 dark:text-purple-400"
              />
            </div>
            <div className="flex-1">
              <h4 className="text-base font-semibold text-foreground m-0">
                {accessRecord?.frameworkCategory?.frameworkCategoryName}
              </h4>
              <div className="flex items-center gap-3">
                <p className="text-sm text-muted-foreground m-0">
                  Code: {accessRecord?.frameworkCategory?.frameworkCode}
                </p>
                {cfg.showStatusBadge && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                    Approved
                  </span>
                )}
              </div>
            </div>
          </div>
          {cfg.showRequestMessage && accessRecord?.requestMessage && (
            <div className="bg-background p-2 rounded">
              <p className="text-xs text-muted-foreground mb-1">
                Request Message:
              </p>
              <p className="text-sm text-foreground leading-relaxed">
                {accessRecord.requestMessage}
              </p>
            </div>
          )}
        </div>
      </div>
    </ConfirmModal>
  );
}
