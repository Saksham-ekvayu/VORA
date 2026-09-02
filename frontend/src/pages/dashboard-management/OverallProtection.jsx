/* eslint-disable react/prop-types */
import { useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { getAuditorOverallProtection } from "@/services/dashboardService";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";

// ─── Stat Mini Box ────────────────────────────────────────────────────────────

function MiniStatBox({ label, value, valueColor }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-1.5 rounded border border-border bg-card shadow-sm">
      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className="w-px h-3.5 bg-border" />
      <span className={`text-sm font-extrabold ${valueColor}`}>{value}</span>
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
    emptyMessage,
    error,
  } = useTableData(getAuditorOverallProtection, {
    defaultSortBy: "framework",
    defaultSortOrder: "asc",
    defaultLimit: 10,
    emptyMessage: "No framework data found",
  });

  const frameworksData = Array.isArray(rawData)
    ? []
    : rawData?.frameworks || [];
  const currentStats = Array.isArray(rawData) ? null : rawData?.stats;

  const handleStatusFilter = (val) => {
    onFilterChange("statusFilter", val);
  };

  // ── Column definitions ──────────────────────────────────────────────────────
  const columns = [
    {
      key: "framework",
      label: "Framework",
      sortable: false,
      render: (value, row) => (
        <FrameworkMiniCard
          name={row.framework}
          description={row.version}
          link={`/deployment-frameworks/${row.id}`}
        />
      ),
    },
    {
      key: "weightage",
      label: "Weightage",
      sortable: false,
      align: "center",
      render: (value) => <span className="">{value}%</span>,
    },
    {
      key: "implementation",
      label: "Implement",
      sortable: false,
      align: "center",
      render: (value) => <span className="">{value}%</span>,
    },
    {
      key: "trend",
      label: "Trend",
      sortable: false,
      align: "center",
      render: (value, row) => (
        <span
          className={`flex justify-center items-center gap-1 ${
            row.trendUp ? "text-emerald-400" : "text-red-400"
          }`}
        >
          <Icon
            name={row.trendUp ? "trending-up" : "trending-down"}
            size="13px"
          />
          {row.trendUp ? "+" : "-"}
          {value}%
        </span>
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: false,
      align: "right",
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
            Composite score across all active frameworks, deployment points, and
            control categories. Weighted by criticality and asset exposure.
          </p>
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
              label="Controls Evaluated"
              value={statsToUse.controlsEvaluated}
              valueColor="text-emerald-500"
            />
            <MiniStatBox
              label="Deployment Points"
              value={statsToUse.deploymentPoints}
              valueColor="text-amber-500"
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
        emptyMessage={emptyMessage}
        error={error}
      />
    </div>
  );
}
