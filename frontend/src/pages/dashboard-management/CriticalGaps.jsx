/* eslint-disable react/prop-types */
import { Link, useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { getAuditorCriticalGaps } from "@/services/dashboardService";

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CriticalGaps() {
  usePageTitle("critical-gaps", "Critical Gaps");

  const navigate = useNavigate();
  const urlParams = new URLSearchParams(globalThis.location.search);

  const {
    data: rawData,
    loading,
    pagination,
    searchTerm,
    onSearch,
    onFilterChange,
  } = useTableData(getAuditorCriticalGaps, {
    defaultSortBy: "failingPct",
    defaultSortOrder: "desc",
  });

  const severityFilter = urlParams.get("severityFilter") || "";
  const tableData = Array.isArray(rawData) ? [] : rawData?.results || [];
  const stats = (Array.isArray(rawData) ? null : rawData?.stats) || {
    description:
      "Active control failures exceeding risk tolerance thresholds. Each gap requires remediation evidence before the next audit cycle.",
    priorities: { high: 0, medium: 0, low: 0 },
  };

  const priorityPills = [
    {
      label: `${stats.priorities.high} High Priority`,
      color: "bg-red-500/20 text-red-400 border border-red-500/30",
    },
    {
      label: `${stats.priorities.medium} Medium Priority`,
      color: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    },
    {
      label: `${stats.priorities.low} Low Priority`,
      color: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    },
  ];

  // ── Column definitions ──────────────────────────────────────────────────────
  const columns = [
    {
      key: "frameworkVersion",
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
      key: "frameworkName",
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
      key: "ctrlNo",
      label: "Ctrl ID",
      sortable: false,
      render: (value) => (
        <span className="font-mono font-bold text-secondary bg-muted px-2 py-1 rounded whitespace-nowrap">
          {value}
        </span>
      ),
    },
    {
      key: "controlName",
      label: "Control Name",
      sortable: false,
      render: (value) => <span className="capitalize">{value}</span>,
    },
    {
      key: "instances",
      label: "Instances",
      sortable: false,
      render: (value) => <span className="text-center block">{value}</span>,
    },
    {
      key: "failingPct",
      label: "% Failing",
      sortable: false,
      render: (value) => (
        <span className="font-semibold text-red-400 text-center block">
          {value}
        </span>
      ),
    },
    {
      key: "severity",
      label: "Severity",
      sortable: false,
      render: (value) => <CustomBadge severity={value} size="xs" />,
    },
  ];

  // ── Header actions ──────────────────────────────────────────────────────────
  const getHeaderActions = () => [
    {
      type: "dropdown",
      label: severityFilter || "All Severities",
      triggerClassName: "w-fit min-w-32",
      options: [
        {
          label: "All Severities",
          onClick: () => onFilterChange("severityFilter", ""),
        },
        {
          label: "High",
          separatorBefore: true,
          onClick: () => onFilterChange("severityFilter", "High"),
        },
        {
          label: "Medium",
          onClick: () => onFilterChange("severityFilter", "Medium"),
        },
        {
          label: "Low",
          onClick: () => onFilterChange("severityFilter", "Low"),
        },
      ],
    },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 my-2">
      {/* Hero summary banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-red-400">{pagination?.totalItems || 0}</span>{" "}
            <span className="text-base font-semibold">
              Critical Non-Conformances
            </span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">
            {stats.description}
          </p>
        </div>

        {/* Right — Button */}
        <div className="flex flex-col items-end gap-2">
          <Button
            size="xs"
            variant="outline"
            onClick={() => navigate("/dashboard")}
          >
            <Icon name="arrow-left" size="13px" /> Back to Dashboard
          </Button>
          {/* Priority pills */}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {priorityPills.map((p) => (
              <span
                key={p.label}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold ${p.color}`}
              >
                {p.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* DataTable — All Active Gaps */}
      <DataTable
        entityName="Gaps"
        columns={columns}
        data={tableData}
        loading={loading}
        onSearch={onSearch}
        searchTerm={searchTerm}
        onClearSearch={() => onSearch("")}
        pagination={pagination}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search gaps..."
        emptyMessage={
          searchTerm || severityFilter
            ? "No gaps match your filters"
            : "No critical gaps found"
        }
      />
    </div>
  );
}
