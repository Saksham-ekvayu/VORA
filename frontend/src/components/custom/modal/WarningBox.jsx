/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";

/**
 * WarningBox — reusable alert/info box used across ~10 modals.
 *
 * Variants:
 *   "warning"  – amber  (default)
 *   "info"     – yellow (alias for "warning", same style)
 *   "danger"   – red
 *   "success"  – green
 *
 * Props:
 *   variant   – "warning" | "danger" | "success"  (default "warning")
 *   icon      – Icon name string  (default matches variant)
 *   children  – message text or JSX
 *   className – extra classes on the outer div
 */

const VARIANT_STYLES = {
  warning: {
    outer: "bg-amber-500/10 border border-amber-500/30 rounded p-3",
    icon: "text-amber-600 dark:text-amber-400",
    text: "text-amber-800 dark:text-amber-200",
    defaultIcon: "alert-triangle",
  },
  info: {
    outer:
      "bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded p-3",
    icon: "text-yellow-600 dark:text-yellow-400",
    text: "text-yellow-800 dark:text-yellow-200",
    defaultIcon: "info",
  },
  danger: {
    outer:
      "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3",
    icon: "text-red-600 dark:text-red-400",
    text: "text-red-800 dark:text-red-200",
    defaultIcon: "x-circle",
  },
  success: {
    outer:
      "bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded p-3",
    icon: "text-green-600 dark:text-green-400",
    text: "text-green-800 dark:text-green-200",
    defaultIcon: "check-circle",
  },
};

export default function WarningBox({
  variant = "warning",
  icon,
  children,
  className = "",
}) {
  const styles = VARIANT_STYLES[variant] ?? VARIANT_STYLES.warning;
  const iconName = icon ?? styles.defaultIcon;

  return (
    <div className={`${styles.outer} ${className}`}>
      <div className="flex gap-2">
        <Icon
          name={iconName}
          size="16px"
          className={`${styles.icon} mt-0.5 shrink-0`}
        />
        <p className={`text-xs leading-relaxed font-semibold ${styles.text}`}>
          {children}
        </p>
      </div>
    </div>
  );
}
