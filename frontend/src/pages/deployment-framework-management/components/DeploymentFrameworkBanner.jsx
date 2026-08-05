/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import { Badge } from "@/components/ui/badge";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";

// ─── AssignedFrameworkCard ────────────────────────────────────────────────────
/**
 * Displays the reference assigned framework info inside the banner.
 * accent: "red" for revoked state, "amber" for pending finalization state.
 */
const AssignedFrameworkCard = ({ assignedFramework, accent = "red" }) => {
  const isRed = accent === "red";

  const cardBorder = isRed
    ? "border-red-200 dark:border-red-800"
    : "border-amber-200 dark:border-amber-700";
  const cardBg = isRed ? "dark:bg-red-950/30" : "dark:bg-amber-950/30";
  const labelColor = isRed
    ? "text-red-500 dark:text-red-400"
    : "text-amber-600 dark:text-amber-400";
  const dotColor = isRed ? "bg-red-400" : "bg-amber-400";

  return (
    <div
      className={`bg-white ${cardBg} border ${cardBorder} rounded p-3 space-y-1.5`}
    >
      <p
        className={`text-[10px] font-semibold uppercase tracking-widest mb-2 ${labelColor}`}
      >
        Reference Assigned Framework
      </p>
      <div className="flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor}`} />
        <span className="text-[12px] font-semibold text-foreground">
          {assignedFramework?.frameworkName}
        </span>
      </div>
      <p className="text-[11px] text-muted-foreground pl-3.5">
        <span className="font-medium text-foreground">Framework Version:</span>{" "}
        {assignedFramework?.frameworkVersion}
      </p>
      {assignedFramework?.assignment?.assignedAt && (
        <p className="text-[11px] text-muted-foreground pl-3.5">
          <span className="font-medium text-foreground">Assigned on:</span>{" "}
          {formatDateWithMonthNameAndTime(
            assignedFramework.assignment.assignedAt
          )}
        </p>
      )}
      {assignedFramework?.assignment?.assignedBy?.name && (
        <p className="text-[11px] text-muted-foreground pl-3.5">
          <span className="font-medium text-foreground">Assigned by:</span>{" "}
          {assignedFramework.assignment.assignedBy.name}
        </p>
      )}
    </div>
  );
};

// ─── DeploymentFrameworkBanner ───────────────────────────────────────────────────
/**
 * Handles two warning states for the linked assigned framework:
 *
 * 1. status === "revoked"
 *    The assigned framework was revoked — deployment is non-functional.
 *
 * 2. status === "assigned" && finalization.isFinalized === false
 *    Not yet finalized by the framework manager — deployment cannot be
 *    used as a reference until finalization is complete.
 *
 * @param {{ assignedFramework: object }} props
 */
const DeploymentFrameworkBanner = ({ assignedFramework }) => {
  const isRevoked = assignedFramework?.status === "revoked";
  const isPendingFinalization =
    assignedFramework?.status === "assigned" &&
    assignedFramework?.finalization?.isFinalized === false;

  if (!isRevoked && !isPendingFinalization) return null;

  // ── REVOKED ───────────────────────────────────────────────────────────────
  if (isRevoked) {
    return (
      <div className="rounded border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950/40 overflow-hidden">
        {/* top strip */}
        <div className="bg-red-100 dark:bg-red-900/50 px-4 py-2 flex items-center gap-2 border-b border-red-200 dark:border-red-800">
          <Icon
            name="alert"
            size={14}
            className="text-red-600 dark:text-red-400"
          />
          <p className="text-[11px] font-semibold uppercase tracking-widest text-red-700 dark:text-red-400">
            Assigned Framework Revoked — Action Required
          </p>
          <Badge
            variant="destructive"
            className="ml-auto text-[10px] capitalize"
          >
            Revoked
          </Badge>
        </div>

        <div className="p-4 flex flex-col gap-4">
          {/* context message */}
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 bg-red-100 dark:bg-red-900/50 rounded flex items-center justify-center text-red-600 dark:text-red-400 shrink-0 mt-0.5">
              <Icon name="alert" size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-red-700 dark:text-red-400">
                This deployment framework was uploaded for the assigned
                framework{" "}
                <span className="underline underline-offset-2">
                  {assignedFramework?.frameworkName}
                </span>{" "}
                ({assignedFramework?.frameworkVersion}), which has now been
                revoked.
              </p>
              <p className="text-[11px] text-red-600/80 dark:text-red-400/70 mt-1 leading-relaxed">
                Since the reference assigned framework is no longer active, this
                deployment framework and all its uploaded packages will{" "}
                <strong>not be functional</strong>. Please contact your admin to
                re-assign the framework or resolve this issue.
              </p>
            </div>
          </div>

          {/* two info cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <AssignedFrameworkCard
              assignedFramework={assignedFramework}
              accent="red"
            />

            {/* revocation details */}
            <div className="bg-white dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded p-3 space-y-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-red-500 dark:text-red-400 mb-2">
                Revocation Details
              </p>
              {assignedFramework?.revocation?.revokedAt && (
                <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                  <Icon
                    name="clock"
                    size={11}
                    className="text-red-400 shrink-0"
                  />
                  <span>
                    <span className="font-medium text-foreground">
                      Revoked at:
                    </span>{" "}
                    {formatDateWithMonthNameAndTime(
                      assignedFramework.revocation.revokedAt
                    )}
                  </span>
                </p>
              )}
              {assignedFramework?.revocation?.revokedBy?.name && (
                <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                  <Icon
                    name="user"
                    size={11}
                    className="text-red-400 shrink-0"
                  />
                  <span>
                    <span className="font-medium text-foreground">
                      Revoked by:
                    </span>{" "}
                    {assignedFramework.revocation.revokedBy.name}
                  </span>
                </p>
              )}
              {assignedFramework?.revocation?.revokedBy?.email && (
                <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                  <Icon
                    name="mail"
                    size={11}
                    className="text-red-400 shrink-0"
                  />
                  <span>{assignedFramework.revocation.revokedBy.email}</span>
                </p>
              )}
              {assignedFramework?.revocation?.revokedBy?.role && (
                <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                  <Icon
                    name="shield"
                    size={11}
                    className="text-red-400 shrink-0"
                  />
                  <span className="capitalize">
                    {assignedFramework.revocation.revokedBy.role}
                  </span>
                </p>
              )}
            </div>
          </div>

          {/* contact admin note */}
          <div className="flex items-center gap-2 bg-red-100/60 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded px-3 py-2">
            <Icon name="info" size={13} className="text-red-500 shrink-0" />
            <p className="text-[11px] text-red-700 dark:text-red-400">
              To restore access, please contact your administrator to re-assign
              the framework{" "}
              <strong>
                {assignedFramework?.frameworkName} (
                {assignedFramework?.frameworkVersion})
              </strong>{" "}
              to your organization.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── PENDING FINALIZATION ──────────────────────────────────────────────────
  return (
    <div className="rounded border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 overflow-hidden">
      {/* top strip */}
      <div className="bg-amber-100 dark:bg-amber-900/50 px-4 py-2 flex items-center gap-2 border-b border-amber-200 dark:border-amber-700">
        <Icon
          name="hourglass"
          size={14}
          className="text-amber-600 dark:text-amber-400"
        />
        <p className="text-[11px] font-semibold uppercase tracking-widest text-amber-700 dark:text-amber-400">
          Assigned Framework Not Yet Finalized — Awaiting Framework Manager
        </p>
        <Badge variant="amber" className="ml-auto text-[10px] capitalize">
          Pending Finalization
        </Badge>
      </div>

      <div className="p-4 flex flex-col gap-4">
        {/* context message */}
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 bg-amber-100 dark:bg-amber-900/50 rounded flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0 mt-0.5">
            <Icon name="hourglass" size={18} />
          </div>
          <div>
            <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
              The assigned framework{" "}
              <span className="underline underline-offset-2">
                {assignedFramework?.frameworkName}
              </span>{" "}
              ({assignedFramework?.frameworkVersion}) has been assigned but is{" "}
              <strong>not yet finalized</strong> by the framework manager.
            </p>
            <p className="text-[11px] text-amber-600/80 dark:text-amber-400/70 mt-1 leading-relaxed">
              The framework manager needs to review, make any necessary changes,
              and finalize the assigned framework first. Until finalization is
              complete, this deployment framework and its packages{" "}
              <strong>cannot be used as a reference</strong> for compliance
              work.
            </p>
          </div>
        </div>

        {/* two info cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <AssignedFrameworkCard
            assignedFramework={assignedFramework}
            accent="amber"
          />

          {/* what needs to happen */}
          <div className="bg-white dark:bg-amber-950/30 border border-amber-200 dark:border-amber-700 rounded p-3 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-amber-600 dark:text-amber-400 mb-2">
              What Needs to Happen
            </p>
            {[
              {
                icon: "edit",
                text: "Framework manager reviews the assigned framework",
              },
              { icon: "check", text: "Makes any required changes or updates" },
              { icon: "shield", text: "Finalizes the assigned framework" },
              { icon: "rocket", text: "Your deployment work can then proceed" },
            ].map((step) => (
              <p
                key={step.text}
                className="text-[11px] text-muted-foreground flex items-center gap-1.5"
              >
                <Icon
                  name={step.icon}
                  size={11}
                  className="text-amber-500 shrink-0"
                />
                <span>{step.text}</span>
              </p>
            ))}
          </div>
        </div>

        {/* contact note */}
        <div className="flex items-center gap-2 bg-amber-100/60 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded px-3 py-2">
          <Icon name="info" size={13} className="text-amber-600 shrink-0" />
          <p className="text-[11px] text-amber-700 dark:text-amber-400">
            Please contact your framework manager to finalize{" "}
            <strong>
              {assignedFramework?.frameworkName} (
              {assignedFramework?.frameworkVersion})
            </strong>{" "}
            . Once finalized, this deployment framework will be fully
            operational.
          </p>
        </div>
      </div>
    </div>
  );
};

export default DeploymentFrameworkBanner;
