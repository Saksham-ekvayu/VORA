/* eslint-disable react/prop-types */
import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import Icon from "@/components/custom/Icon";
import SearchInput from "@/components/custom/SearchInput";
import TableHeaderActions from "@/components/custom/TableHeaderActions";
import CustomPagination from "@/components/custom/CustomPagination";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";

// ─── Static mock data ─────────────────────────────────────────────────────────

const STATS = {
  integrations: 4,
  totalInstances: 581,
};

const DEPLOYMENT_POINTS = [
  {
    id: "5871a270-8439-4d0d-b810-4266b5098397",
    frameworkName: "Information Security Management System",
    frameworkVersion: "ISO-27001:2022",
    instances: 234,
    controls: [
      { name: "IAM Policies", pct: 88 },
      { name: "S3 Bucket Config", pct: 93 },
      { name: "Security Groups", pct: 79 },
      { name: "CloudTrail Logging", pct: 72 },
    ],
  },
  {
    id: "032594ab-079f-4004-871f-0c26e7760865",
    frameworkName: "Information Security Management System",
    frameworkVersion: "ISO-27001:2022",
    instances: 189,
    controls: [
      { name: "MFA Enforcement", pct: 82 },
      { name: "Password Policy", pct: 95 },
      { name: "Privileged Access", pct: 68 },
      { name: "Lifecycle Mgmt", pct: 91 },
    ],
  },
  {
    id: "4e317264-db50-479c-b34d-43da6608f381",
    frameworkName: "Cybersecurity Framework",
    frameworkVersion: "NIST-CSF:2020",
    instances: 100,
    controls: [
      { name: "Log Retention", pct: 100 },
      { name: "Integrity Checks", pct: 78 },
      { name: "SIEM Integration", pct: 85 },
    ],
  },
  {
    id: "0510024e-39cc-4884-ac7a-84388f869ac3",
    frameworkName: "Cybersecurity Framework",
    frameworkVersion: "NIST-CSF:2020",
    instances: 58,
    controls: [
      { name: "Onboarding Controls", pct: 90 },
      { name: "Offboarding Checks", pct: 74 },
      { name: "Background Vetting", pct: 100 },
    ],
  },
];

// ─── Stat Mini Box ────────────────────────────────────────────────────────────

function MiniStatBox({ label, value, valueColor }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-1.5 rounded border border-border bg-card shadow-sm">
      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className="w-px h-3.5 bg-border" />
      <span
        className={`text-sm font-extrabold ${valueColor ?? "text-foreground"}`}
      >
        {value}
      </span>
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

const BAR_COLORS = [
  "bg-blue-400",
  "bg-emerald-400",
  "bg-amber-400",
  "bg-violet-400",
  "bg-rose-400",
  "bg-cyan-400",
  "bg-indigo-400"
];

function DeploymentCard({ point }) {
  return (
    <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded flex items-center justify-center bg-primary/10">
            <Icon name="layers" size="16px" className="text-primary" />
          </div>
          <div>
            <p className="text-sm font-bold text-primary">
              {point.frameworkName} - ({point.frameworkVersion})
            </p>
            <p className="text-xs text-muted-foreground">
              {point.instances} control instances
            </p>
          </div>
        </div>
      </div>
      <div className="space-y-2">
        {point.controls.map((ctrl, idx) => (
          <ControlBar key={ctrl.name} {...ctrl} color={ctrl.color || BAR_COLORS[idx % BAR_COLORS.length]} />
        ))}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function DeploymentPoints() {
  usePageTitle("deployment-points", "Deployment Points");

  const navigate = useNavigate();

  const [searchTerm, setSearchTerm] = useState("");
  const [frameworkFilter, setFrameworkFilter] = useState("All Frameworks");
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);

  const handleSearch = useCallback((term) => {
    setSearchTerm(term);
    setPage(1);
  }, []);

  const frameworkOptions = useMemo(() => {
    const versions = new Set(DEPLOYMENT_POINTS.map((dp) => dp.frameworkVersion).filter(Boolean));
    return ["All Frameworks", ...Array.from(versions)];
  }, []);

  const tableActions = useMemo(() => [
    {
      type: "dropdown",
      label: frameworkFilter,
      triggerClassName: "w-fit",
      options: frameworkOptions.map((opt, idx) => ({
        label: opt,
        onClick: () => {
          setFrameworkFilter(opt);
          setPage(1);
        },
        separatorBefore: idx === 1,
      })),
    },
  ], [frameworkFilter, frameworkOptions]);

  const filtered = useMemo(() => {
    let list = DEPLOYMENT_POINTS;
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter((dp) => dp.frameworkName.toLowerCase().includes(q));
    }
    if (frameworkFilter !== "All Frameworks") {
      list = list.filter((dp) => dp.frameworkVersion === frameworkFilter);
    }
    return list;
  }, [searchTerm, frameworkFilter]);

  const paginatedData = useMemo(() => {
    const start = (page - 1) * limit;
    return filtered.slice(start, start + limit);
  }, [filtered, page, limit]);

  const totalPages = Math.ceil(filtered.length / limit);

  const paginationObj = {
    currentPage: page,
    totalPages: totalPages,
    limit: limit,
    totalItems: filtered.length,
    hasPrevPage: page > 1,
    hasNextPage: page < totalPages,
    onLimitChange: (newLimit) => {
      setLimit(newLimit);
      setPage(1);
    },
    onPageChange: (newPage) => {
      setPage(newPage);
    }
  };

  return (
    <div className="space-y-3 my-2">
      {/* Hero banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card shadow-lg p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-primary">Deployment Points</span>
            <span className="text-base font-semibold text-muted-foreground ml-2">
              — {STATS.totalInstances} Total Control Instances
            </span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">
            Control coverage across all integrated infrastructure and identity
            platforms. Each deployment point hosts multiple control instances
            that are continuously evaluated.
          </p>
        </div>
        <div className="flex flex-col items-end gap-3 shrink-0">
          <Button
            size="xs"
            variant="outline"
            onClick={() => navigate("/dashboard")}
          >
            <Icon name="arrow-left" size="13px" /> Back to Dashboard
          </Button>
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <MiniStatBox
              label="Integrations"
              value={STATS.integrations}
              valueColor="text-primary"
            />
            <MiniStatBox
              label="Total Instances"
              value={STATS.totalInstances}
              valueColor="text-secondary"
            />
          </div>
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
            <TableHeaderActions actions={tableActions} />
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
              {paginatedData.map((point) => (
                <DeploymentCard key={point.id} point={point} />
              ))}
            </div>
          )}
        </div>

        {/* Pagination Footer */}
        <CustomPagination
          pagination={paginationObj}
          entityName="Deployment Points"
        />
      </div>
    </div>
  );
}
