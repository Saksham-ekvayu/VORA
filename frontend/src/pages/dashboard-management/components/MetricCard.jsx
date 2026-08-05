/* eslint-disable react/prop-types */

import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

function MetricCard({
  icon,
  label,
  value,
  iconColor = "text-primary",
  iconBg = "bg-primary/10",
  borderColor = "border-primary/40",
  path,
}) {
  return (
    <Link
      to={path}
      className="rounded bg-card border border-border p-3 flex items-center gap-4 text-left w-full hover:border-primary/40 hover:shadow-md transition-all group cursor-pointer"
      title={label}
    >
      <div
        className={cn(
          "w-12 h-12 rounded shrink-0 flex items-center justify-center transition-transform duration-300 group-hover:scale-105 border",
          borderColor,
          iconBg,
          iconColor
        )}
      >
        {icon}
      </div>
      <div className="flex flex-col gap-1.5 overflow-hidden">
        <p
          className="text-sm font-medium text-foreground truncate capitalize"
          title={label}
        >
          {label.toLowerCase()}
        </p>
        <p
          className={cn("text-2xl font-bold leading-none truncate", iconColor)}
        >
          {value ?? "—"}
        </p>
      </div>
    </Link>
  );
}

export default MetricCard;
