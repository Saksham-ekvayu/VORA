/* eslint-disable react/prop-types */
import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import Icon from "@/components/custom/Icon";
import CustomBadge from "@/components/custom/CustomBadge";
import TableHeaderActions from "@/components/custom/TableHeaderActions";
import SearchInput from "@/components/custom/SearchInput";
import { usePageTitle } from "@/hooks/usePageTitle";

// ─── Static mock data ─────────────────────────────────────────────────────────

const STATS = {
  integrations: 4,
  totalInstances: 581,
  online: "4 / 4",
  description:
    "Control coverage across all integrated infrastructure and identity platforms. Each deployment point hosts multiple control instances that are continuously evaluated.",
};

const DEPLOYMENT_POINTS = [
  {
    id: "aws",
    name: "AWS Infrastructure",
    framework: "ISO 27001",
    icon: "cloud",
    iconColor: "text-blue-400",
    iconBg: "bg-blue-500/10",
    status: "Online",
    instances: 234,
    subtitle: "12 services monitored",
    controls: [
      { name: "IAM Policies", pct: 88, color: "bg-blue-400" },
      { name: "S3 Bucket Config", pct: 93, color: "bg-emerald-400" },
      { name: "Security Groups", pct: 79, color: "bg-amber-400" },
      { name: "CloudTrail Logging", pct: 72, color: "bg-red-400" },
    ],
  },
  {
    id: "iam",
    name: "IAM / Okta",
    framework: "ISO 27001",
    icon: "key",
    iconColor: "text-amber-400",
    iconBg: "bg-amber-500/10",
    status: "Online",
    instances: 189,
    subtitle: "8 identity domains",
    controls: [
      { name: "MFA Enforcement", pct: 82, color: "bg-emerald-400" },
      { name: "Password Policy", pct: 95, color: "bg-emerald-400" },
      { name: "Privileged Access", pct: 68, color: "bg-amber-400" },
      { name: "Lifecycle Mgmt", pct: 91, color: "bg-emerald-400" },
    ],
  },
  {
    id: "logs",
    name: "Application Logs",
    framework: "NIST CSF",
    icon: "document",
    iconColor: "text-violet-400",
    iconBg: "bg-violet-500/10",
    status: "Online",
    instances: 100,
    subtitle: "6 log sources",
    controls: [
      { name: "Log Retention", pct: 100, color: "bg-emerald-400" },
      { name: "Integrity Checks", pct: 78, color: "bg-violet-400" },
      { name: "SIEM Integration", pct: 85, color: "bg-emerald-400" },
    ],
  },
  {
    id: "hr",
    name: "HR / Admin",
    framework: "NIST CSF",
    icon: "users",
    iconColor: "text-emerald-400",
    iconBg: "bg-emerald-500/10",
    status: "Online",
    instances: 58,
    subtitle: "HR platform + admin tools",
    controls: [
      { name: "Onboarding Controls", pct: 90, color: "bg-emerald-400" },
      { name: "Offboarding Checks", pct: 74, color: "bg-amber-400" },
      { name: "Background Vetting", pct: 100, color: "bg-emerald-400" },
    ],
  },
];

const FRAMEWORK_NAMES = Array.from(
  new Set(DEPLOYMENT_POINTS.map((dp) => dp.framework))
);
const STATUS_NAMES = Array.from(
  new Set(DEPLOYMENT_POINTS.map((dp) => dp.status))
);

// ─── Stat Mini Box ────────────────────────────────────────────────────────────

function MiniStatBox({ label, value, valueColor }) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-2 rounded border border-border bg-accent min-w-25">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1 text-center">
        {label}
      </p>
      <p
        className={`text-2xl font-bold leading-none ${valueColor ?? "text-foreground"}`}
      >
        {value}
      </p>
    </div>
  );
}

// ─── Control progress bar row ─────────────────────────────────────────────────

function ControlBar({ name, pct, color }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-foreground w-36 shrink-0 truncate">
        {name}
      </span>
      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-foreground w-9 text-right shrink-0">
        {pct}%
      </span>
    </div>
  );
}

// ─── Deployment point card ────────────────────────────────────────────────────

function DeploymentCard({ point }) {
  return (
    <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-7 h-7 rounded flex items-center justify-center ${point.iconBg}`}
          >
            <Icon name={point.icon} size="16px" className={point.iconColor} />
          </div>
          <div>
            <p className={`text-sm font-bold ${point.iconColor}`}>
              {point.name}
            </p>
            <p className="text-[10px] text-muted-foreground">
              {point.instances} control instances · {point.subtitle}
            </p>
          </div>
        </div>
        <CustomBadge status={point.status} size="xs" />
      </div>
      <div className="space-y-2">
        {point.controls.map((ctrl) => (
          <ControlBar key={ctrl.name} {...ctrl} />
        ))}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function DeploymentPointsPage() {
  usePageTitle("deployment-points", "Deployment Points");

  const navigate = useNavigate();

  const [searchTerm, setSearchTerm] = useState("");
  const [frameworkFilter, setFrameworkFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const handleSearch = useCallback((term) => setSearchTerm(term), []);
  const handleFrameworkFilter = useCallback(
    (val) => setFrameworkFilter(val),
    []
  );
  const handleStatusFilter = useCallback((val) => setStatusFilter(val), []);

  const filtered = useMemo(() => {
    let list = DEPLOYMENT_POINTS;
    if (frameworkFilter)
      list = list.filter((dp) => dp.framework === frameworkFilter);
    if (statusFilter) list = list.filter((dp) => dp.status === statusFilter);
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter((dp) => dp.name.toLowerCase().includes(q));
    }
    return list;
  }, [searchTerm, frameworkFilter, statusFilter]);

  const headerActions = [
    {
      type: "dropdown",
      label: frameworkFilter || "All Frameworks",
      triggerClassName: "w-fit min-w-36",
      options: [
        { label: "All Frameworks", onClick: () => handleFrameworkFilter("") },
        ...FRAMEWORK_NAMES.map((fw, i) => ({
          label: fw,
          separatorBefore: i === 0,
          onClick: () => handleFrameworkFilter(fw),
        })),
      ],
    },
    {
      type: "dropdown",
      label: statusFilter || "All Status",
      triggerClassName: "w-fit min-w-28",
      options: [
        { label: "All Status", onClick: () => handleStatusFilter("") },
        ...STATUS_NAMES.map((s, i) => ({
          label: s,
          separatorBefore: i === 0,
          onClick: () => handleStatusFilter(s),
        })),
      ],
    },
  ];

  return (
    <div className="space-y-3 my-2">
      {/* Page header */}
      <div className="flex items-center justify-between px-1">
        <h2 className="text-lg font-semibold text-foreground">
          Deployment Points
        </h2>
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-primary border border-border bg-accent hover:border-primary rounded px-3 py-1.5 transition-colors"
        >
          <Icon name="arrow-left" size="13px" /> Back to Dashboard
        </button>
      </div>

      {/* Hero banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-primary">Deployment Points</span>
            <span className="text-base font-semibold text-muted-foreground ml-2">
              — {STATS.totalInstances} Total Control Instances
            </span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">
            {STATS.description}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <MiniStatBox
            label="Integrations"
            value={STATS.integrations}
            valueColor="text-foreground"
          />
          <MiniStatBox
            label="Total Instances"
            value={STATS.totalInstances}
            valueColor="text-foreground"
          />
          <MiniStatBox
            label="Online"
            value={STATS.online}
            valueColor="text-emerald-400"
          />
        </div>
      </div>

      {/* Toolbar — same pattern as DataTable header */}
      <div className="bg-card border border-border rounded overflow-hidden">
        <div className="flex justify-between gap-2 items-center p-2 border-b border-border bg-linear-to-r from-card to-muted/30">
          <div className="flex items-center gap-3 flex-1 max-w-xl">
            <SearchInput
              debounced
              searchTerm={searchTerm}
              onSearch={handleSearch}
              onClearSearch={() => handleSearch("")}
              loading={false}
              debounceDelay={400}
              placeholder="Search deployment points..."
              className="flex-1"
            />
          </div>
          <div className="flex items-center gap-2">
            <TableHeaderActions actions={headerActions} />
          </div>
        </div>

        {/* Cards grid */}
        <div className="p-3">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                <Icon name="folder" size="32px" className="opacity-50" />
              </div>
              <p className="text-base font-medium text-muted-foreground">
                No deployment points found
              </p>
              <p className="text-sm text-muted-foreground/70 mt-1">
                Try adjusting your search or filters
              </p>
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {filtered.map((point) => (
                <DeploymentCard key={point.id} point={point} />
              ))}
            </div>
          )}
        </div>

        {/* Footer count */}
        <div className="flex justify-between items-center px-4 py-3 border-t border-border bg-muted text-sm text-muted-foreground">
          Showing {filtered.length} of {DEPLOYMENT_POINTS.length} Deployment
          Points
        </div>
      </div>
    </div>
  );
}
