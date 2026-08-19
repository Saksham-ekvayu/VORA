/* eslint-disable react/prop-types */
import { Link, useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { getAuditorOverallProtection } from "@/services/dashboardService";

// ─── Stat Mini Box ────────────────────────────────────────────────────────────

function MiniStatBox({ label, value, valueColor }) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-2 rounded border border-border bg-accent min-w-27.5">
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

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function OverallProtection() {
  usePageTitle("overall-protection", "Overall Protection");

  const navigate = useNavigate();
  const urlParams = new URLSearchParams(globalThis.location.search);

  // Extract custom filters from URL
  const statusFilter = urlParams.get("statusFilter") || "";

  // Hook for table data
  const {
    data: rawData,
    loading,
    pagination,
    searchTerm,
    onSearch,
    onFilterChange,
  } = useTableData(getAuditorOverallProtection, {
    defaultSortBy: "framework",
    defaultSortOrder: "asc",
    defaultLimit: 10,
    emptyMessage: "No framework data found",
  });

  const frameworksData = Array.isArray(rawData) ? [] : (rawData?.frameworks || []);
  const currentStats = Array.isArray(rawData) ? null : rawData?.stats;

  const handleStatusFilter = (val) => {
    onFilterChange("statusFilter", val);
  };

  // ── Column definitions ──────────────────────────────────────────────────────
  const columns = [
    {
      key: "version",
      label: "Framework Version",
      sortable: false,
      render: (value, row) => (
        <Link
          to={`/deployment-frameworks/${row.id}`}
          className="hover:underline hover:text-primary"
        >
          {value}
        </Link>
      ),
    },
    {
      key: "framework",
      label: "Framework Name",
      sortable: false,
      render: (value, row) => (
        <Link
          to={`/deployment-frameworks/${row.id}`}
          className="hover:underline hover:text-primary"
        >
          {value}
        </Link>
      ),
    },
    {
      key: "weight",
      label: "Weight",
      sortable: false,
      render: (value) => (
        <span className="">{value}%</span>
      ),
    },
    {
      key: "rawScore",
      label: "Raw Score",
      sortable: false,
      render: (value) => (
        <span className="">{value}%</span>
      ),
    },
    {
      key: "contribution",
      label: "Contribution",
      sortable: false,
      render: (value) => (
        <span className="">{value}%</span>
      ),
    },
    {
      key: "trend",
      label: "Trend",
      sortable: false,
      render: (value, row) => (
        <span
          className={`flex items-center gap-1 ${row.trendUp ? "text-emerald-400" : "text-red-400"
            }`}
        >
          <Icon
            name={row.trendUp ? "trending-up" : "trending-down"}
            size="13px"
          />
          {row.trendUp ? "+" : "-"}{value}%
        </span>
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: false,
      render: (value) => <CustomBadge status={value} size="sm" />,
    },
  ];

  // ── Header actions ──────────────────────────────────────────────────────────
  const getHeaderActions = () => [
    {
      type: "dropdown",
      label: statusFilter || "All Status",
      triggerClassName: "w-fit min-w-36",
      options: [
        { label: "All Status", onClick: () => handleStatusFilter("") },
        {
          label: "On Track",
          separatorBefore: true,
          onClick: () => handleStatusFilter("On Track"),
        },
        {
          label: "Needs Attention",
          onClick: () => handleStatusFilter("Needs Attention"),
        },
        { label: "At Risk", onClick: () => handleStatusFilter("At Risk") },
      ],
    },
  ];

  // Default stats to avoid render issues when loading
  const statsToUse = currentStats || {
    score: 0,
    trend: 0,
    trendUp: true,
    frameworksActive: 0,
    controlsEvaluated: 0,
    deploymentPoints: 0,
  };

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 my-2">
      {/* ── Hero banner ───────────────────────────────────────────────────── */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        {/* Left — score + description + pills */}
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-primary">{statsToUse.score}%</span>{" "}
            <span className="text-base font-semibold">
              Overall Protection Score
            </span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">
            Composite score across all active frameworks, deployment points, and control categories. Weighted by criticality and asset exposure.
          </p>
          {/* Trend + period pills */}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1 ${statsToUse.trendUp
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "bg-red-500/20 text-red-400 border border-red-500/30"
                }`}
            >
              <Icon
                name={statsToUse.trendUp ? "trending-up" : "trending-down"}
                size="11px"
              />
              {statsToUse.trendUp ? "+" : "-"}{statsToUse.trend}% vs last month
            </span>
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-accent text-muted-foreground border border-border">
              Last 180 Days
            </span>
          </div>
        </div>

        {/* Right — Button & 4 stat boxes */}
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
              label="Frameworks Active"
              value={statsToUse.frameworksActive}
              valueColor="text-primary"
            />
            <MiniStatBox
              label="Controls Evaluated"
              value={statsToUse.controlsEvaluated}
              valueColor="text-foreground"
            />
            <MiniStatBox
              label="Deployment Points"
              value={statsToUse.deploymentPoints}
              valueColor="text-primary"
            />
          </div>
        </div>
      </div>

      {/* ── Framework Contribution table ───────────────────────────────────── */}
      <DataTable
        entityName="Frameworks"
        columns={columns}
        data={frameworksData}
        loading={loading}
        onSearch={onSearch}
        searchTerm={searchTerm}
        onClearSearch={() => onSearch("")}
        pagination={pagination}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search framework..."
        emptyMessage={
          searchTerm || statusFilter
            ? "No frameworks match your filters"
            : "No framework data found"
        }
      />
    </div>
  );
}
