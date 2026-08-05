/* eslint-disable react/prop-types */
import Icon from "@/components/custom/Icon";
import ConfirmModal from "./ConfirmModal";
import WarningBox from "./WarningBox";
import { getRoleBadgeClass } from "@/utils/commonUtils";

/**
 * ConfirmDeleteModal — a parameterized, unified deletion confirmation modal.
 * Consolidates DeleteUserModal, DeleteCustomerModal, DeleteCategoryModal,
 * DeleteFrameworkModal, DeleteDeploymentFrameworkModal, DeleteDeploymentDocumentModal,
 * and DeletePackageModal into a single reusable configuration-driven modal.
 */
export default function ConfirmDeleteModal({
  open,
  onCancel,
  onConfirm,
  title,
  description,
  actionLabel = "Delete",
  actionIcon = "trash",
  savingLabel = "Deleting...",
  isActionDisabled = false,
  bodyText, // optional text paragraph above the entity box
  // Entity Box Details
  entityIcon,
  entityName,
  entitySubtitle,
  badges = [], // Array of { text, className }
  stats = [], // Array of { label, value, icon, capitalize }
  metaText, // e.g., "Created By: User"
  metaIcon, // optional icon for meta text
  warningText, // optional warning message to show in a WarningBox
  warningVariant = "warning",
  children, // fallback/custom additional elements
}) {
  return (
    <ConfirmModal
      open={open}
      onCancel={onCancel}
      onConfirm={onConfirm}
      icon="warning"
      title={title}
      description={description}
      actionLabel={actionLabel}
      savingLabel={savingLabel}
      actionIcon={actionIcon}
      isActionDisabled={isActionDisabled}
    >
      {bodyText && (
        <p className="text-muted-foreground text-xs leading-relaxed mb-2">
          {bodyText}
        </p>
      )}

      {(entityName ||
        entityIcon ||
        entitySubtitle ||
        badges.length > 0 ||
        stats.length > 0 ||
        metaText) && (
        <div className="bg-muted rounded p-3 border-l-4 border-red-500 flex flex-col gap-2">
          <div className="flex items-center gap-3 mb-1">
            {entityIcon && (
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary shrink-0">
                <Icon name={entityIcon} size="20px" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              {entityName && (
                <h4 className="text-base font-semibold text-foreground m-0 truncate">
                  {entityName}
                </h4>
              )}
              {entitySubtitle && (
                <p className="text-sm text-muted-foreground m-0 truncate">
                  {entitySubtitle}
                </p>
              )}
            </div>
          </div>

          {badges.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-1">
              {badges.map((badge) => (
                <span
                  key={badge.text}
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.className}`}
                >
                  {badge.text}
                </span>
              ))}
            </div>
          )}

          {stats.length > 0 && (
            <div className="grid grid-cols-2 gap-2 mt-1">
              {stats.map((s) => (
                <div
                  key={s.label}
                  className="flex items-center gap-2 bg-background rounded px-2.5 py-1.5"
                >
                  {s.icon && (
                    <Icon
                      name={s.icon}
                      size={13}
                      className="text-muted-foreground shrink-0"
                    />
                  )}
                  <div className="min-w-0">
                    <p className="text-[10px] text-muted-foreground leading-none">
                      {s.label}
                    </p>
                    <p
                      className={`text-xs font-semibold text-foreground mt-0.5 truncate ${
                        s.capitalize ? "capitalize" : ""
                      }`}
                    >
                      {s.value}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {metaText && (
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1 leading-relaxed">
              {metaIcon && <Icon name={metaIcon} size={11} />}
              {metaText}
            </p>
          )}
        </div>
      )}

      {children}

      {warningText && (
        <WarningBox variant={warningVariant} icon="alert-triangle">
          {warningText}
        </WarningBox>
      )}
    </ConfirmModal>
  );
}

// ─── Presets ──────────────────────────────────────────────────────────

export function DeleteUserModal({ open, onCancel, onConfirm, user }) {
  if (!user) return null;
  return (
    <ConfirmDeleteModal
      open={open}
      onCancel={onCancel}
      onConfirm={onConfirm}
      title="Delete User"
      description="Choose how you want to delete this user. This action cannot be undone."
      entityIcon="user"
      entityName={user.name}
      entitySubtitle={user.email}
      badges={[
        {
          text: user.role,
          className: `capitalize ${getRoleBadgeClass(user.role)}`,
        },
        {
          text: user.isEmailVerified ? "Verified" : "Pending",
          className: user.isEmailVerified
            ? "bg-green-100 text-green-800"
            : "bg-yellow-100 text-yellow-800",
        },
      ]}
    />
  );
}

export function DeleteFrameworkModal({ open, onCancel, onConfirm, framework }) {
  if (!framework) return null;
  return (
    <ConfirmDeleteModal
      open={open}
      onCancel={onCancel}
      onConfirm={onConfirm}
      title="Delete Framework"
      description="Confirm deletion of framework. This action cannot be undone."
      bodyText="Are you sure you want to delete this framework? This action cannot be undone."
      entityIcon="document"
      entityName={framework.frameworkName}
      entitySubtitle={`Code: ${framework.frameworkCode}`}
      badges={[
        {
          text: framework.frameworkType?.toUpperCase() || "PDF",
          className:
            "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
        },
        framework.fileInfo?.fileSize && {
          text: framework.fileInfo.fileSize,
          className:
            "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
        },
      ].filter(Boolean)}
      metaText={
        framework.uploadedBy?.name
          ? `Created By: ${framework.uploadedBy.name}`
          : undefined
      }
    />
  );
}

const getDeleteModalStats = (framework) => {
  if (!framework) return [];
  const packageCount = Array.isArray(framework.packages)
    ? framework.packages.length
    : (framework.package?.packageCount ?? 0);

  const totalDocuments = Array.isArray(framework.packages)
    ? framework.packages.reduce(
        (sum, pkg) => sum + (pkg.documents?.length ?? 0),
        0
      )
    : (framework.document?.count ?? 0);

  const currentPkg = Array.isArray(framework.packages)
    ? framework.packages.find(
        (p) => p.packageVersion === framework.currentPackageVersion
      )
    : null;

  const packageStatus = Array.isArray(framework.packages)
    ? (currentPkg?.status ?? "—")
    : (framework.package?.status ?? "—");

  return [
    { icon: "layers", label: "Packages", value: packageCount },
    { icon: "document", label: "Documents", value: totalDocuments },
    {
      icon: "tag",
      label: "Current Version",
      value: framework.currentPackageVersion
        ? `v${framework.currentPackageVersion}`
        : "—",
    },
    {
      icon: "hourglass",
      label: "Package Status",
      value: packageStatus,
      capitalize: true,
    },
  ];
};

export function DeleteDeploymentFrameworkModal({
  open,
  onCancel,
  onConfirm,
  framework,
}) {
  if (!framework) return null;
  return (
    <ConfirmDeleteModal
      open={open}
      onCancel={onCancel}
      onConfirm={onConfirm}
      title="Delete Framework"
      description="Confirm deletion of deployment framework"
      bodyText="Are you sure you want to delete this framework? This action cannot be undone."
      entityIcon="document"
      entityName={framework.frameworkName}
      entitySubtitle={`${framework.frameworkVersion} · Code: ${framework.frameworkCode}`}
      stats={getDeleteModalStats(framework)}
      metaText={
        framework.uploadedBy?.name
          ? `Created by: ${framework.uploadedBy.name}`
          : undefined
      }
      metaIcon="user"
    />
  );
}
