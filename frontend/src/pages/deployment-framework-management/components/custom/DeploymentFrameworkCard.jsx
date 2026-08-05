/* eslint-disable react/prop-types */

import Icon from "@/components/custom/Icon";
import UserAvatar from "@/components/custom/UserAvatar";
import StatusCard from "@/components/custom/StatusCard";
import { Link } from "react-router-dom";

// ─── helpers ────────────────────────────────────────────────────────────────

const formatDate = (iso) => {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const getDocTypeKey = (typeLabel) => {
  // Incoming list format is usually like: "6 pdf", "3 docx"
  const raw = String(typeLabel || "")
    .toLowerCase()
    .trim();
  const token = raw.split(/\s+/).pop(); // last token
  const knownTypes = {
    pdf: "pdf",
    doc: "doc",
    docx: "docx",
  };
  return knownTypes[token] || "unknown";
};

const getDocTypePillClass = (typeLabel) => {
  const key = getDocTypeKey(typeLabel);
  const common = "text-[10px] px-1.5 py-0.5 rounded-full border font-medium";

  const cfg = {
    pdf: "border-red-200 text-red-800 bg-red-50 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-300",
    doc: "border-blue-200 text-blue-800 bg-blue-50 dark:bg-blue-500/10 dark:border-blue-500/20 dark:text-blue-300",
    docx: "border-indigo-200 text-indigo-800 bg-indigo-50 dark:bg-indigo-500/10 dark:border-indigo-500/20 dark:text-indigo-300",
    unknown:
      "border-border/60 text-muted-foreground bg-background dark:bg-muted/30 dark:border-border/50",
  };

  return `${common} ${cfg[key] || cfg.unknown}`;
};

// ─── component ──────────────────────────────────────────────────────────────

const DeploymentFrameworkCard = ({ framework, renderActions }) => {
  const {
    id,
    frameworkName,
    frameworkVersion,
    currentPackageVersion,
    document,
    aiExtraction,
    requestReview,
    package: pkg,
    uploadedBy,
    createdAt,
  } = framework;

  const documentCount = document?.count ?? 0;
  const isPlural = documentCount > 1;

  return (
    <div className="group relative bg-card border border-border rounded overflow-hidden shadow-sm hover:shadow-md hover:border-border/80 transition-all duration-200 flex flex-col h-full">
      {/* Top accent bar */}
      <div className="h-0.75 bg-linear-to-r from-teal-700 via-teal-500 to-teal-300 shrink-0" />

      {/* ── Header ── */}
      <div className="px-3.5 pt-2.5 pb-2 flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0 flex-1">
          {/* Icon */}
          <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Icon name="shield-check" size="16px" />
          </div>

          {/* Title */}
          <div className="min-w-0">
            <Link
              to={`/deployment-frameworks/${id}`}
              className="text-[13.5px] font-medium text-foreground hover:text-primary transition-colors line-clamp-2 leading-snug"
            >
              {frameworkName}
            </Link>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {frameworkVersion}
            </p>
          </div>
        </div>

        {renderActions?.(framework)}
      </div>

      {/* ── Package section ── */}
      <div className="mx-3.5 mb-2.5 px-2.5 py-2 rounded-md bg-muted/30 border border-border/40 flex items-center gap-2">
        <div className="w-8 h-8 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
          <Icon name="folder" size="16px" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[12px] font-medium text-foreground">
            Package v{currentPackageVersion || "1.0.0"}
          </p>
          <div className="flex items-center justify-between gap-1.5 mt-0.5 flex-wrap">
            <span className="text-[11px] text-muted-foreground">
              {documentCount} document
              {isPlural ? "s" : ""}
            </span>
            <div className="flex items-center gap-1.5">
              {document?.types?.map((type, i) => (
                <span key={i + 1} className={getDocTypePillClass(type)}>
                  {type}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Status grid ── */}
      <div className="px-3.5 pb-2.5 grid grid-cols-3 gap-1.5">
        {/* AI Extraction */}
        <div className="rounded-md border border-border/40 px-2 py-1.5">
          <p className="text-[9.5px] font-semibold uppercase tracking-wider text-muted-foreground/70 mb-1.5">
            AI Extraction
          </p>
          <StatusCard item={aiExtraction} width="w-full" />
        </div>

        {/* Review Status */}
        <div className="rounded-md border border-border/40 px-2.5 py-2">
          <p className="text-[9.5px] font-semibold uppercase tracking-wider text-muted-foreground/70 mb-1.5">
            Review Status
          </p>
          <StatusCard item={requestReview} width="w-full" />
        </div>

        {/* Packege Status */}
        <div className="rounded-md border border-border/40 px-2.5 py-2">
          <p className="text-[9.5px] font-semibold uppercase tracking-wider text-muted-foreground/70 mb-1.5">
            Package Status
          </p>
          <StatusCard item={pkg} width="w-full" />
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="mt-auto px-3.5 py-2 border-t border-border/40 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <UserAvatar user={uploadedBy} />
          <div className="min-w-0">
            <p className="text-[12px] font-medium text-foreground truncate leading-tight">
              {uploadedBy?.name || "System"}
            </p>
            <p className="text-[10.5px] text-muted-foreground truncate leading-tight">
              {uploadedBy?.email}
            </p>
          </div>
        </div>
        <span className="text-[11px] text-muted-foreground shrink-0">
          {formatDate(createdAt)}
        </span>
      </div>
    </div>
  );
};

export default DeploymentFrameworkCard;
