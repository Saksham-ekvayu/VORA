import { Link, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { getAuditorCriticalGaps } from "@/services/dashboardService";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";
import { capitalizeFirstLetter } from "@/utils/stringUtils";

// ─── Stat Box ─────────────────────────────────────────────────────────────────

function StatBox({ label, value, valueColor }) {
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

export default function CriticalGaps() {
  usePageTitle("critical-gaps", "Critical Gaps");

  const navigate = useNavigate();
  const urlParams = new URLSearchParams(globalThis.location.search);

  const {
    data: rawData,
    loading,
    error,
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
    priorities: { high: 0, medium: 0, low: 0 },
  };

  const priorityPills = [
    {
      label: "High Priority",
      value: stats.priorities.high,
      color: "text-red-400",
    },
    {
      label: "Medium Priority",
      value: stats.priorities.medium,
      color: "text-amber-400",
    },
    {
      label: "Low Priority",
      value: stats.priorities.low,
      color: "text-emerald-400",
    },
  ];

  // ── Column definitions ──────────────────────────────────────────────────────
  const columns = [
    {
      key: "frameworkVersion",
      label: "Framework",
      sortable: false,
      render: (value, row) => (
        <FrameworkMiniCard
          name={row.frameworkName}
          description={row.frameworkVersion}
          link={`/deployment-frameworks/${row.id}`}
        />
      ),
    },
    {
      key: "ctrlNo",
      label: "Ctrl ID",
      sortable: false,
      align: "center",
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
      render: (value, row) => (
        <Link
          to={`/deployment-frameworks/${row.id}/comparison-and-gap-analysis?package-version=${row.packageVersion}&tab=controls&control=${row.ctrlNo}&section=${row.sectionId}`}
          className="hover:underline hover:text-primary"
        >
          {capitalizeFirstLetter(value)}
        </Link>
      ),
    },
    {
      key: "instances",
      label: "Instances",
      sortable: false,
      align: "center",
      render: (value) => <span className="">{value}</span>,
    },
    {
      key: "failingPct",
      label: "% Failing",
      sortable: false,
      align: "center",
      render: (value) => (
        <span className="font-semibold text-red-400">{value}</span>
      ),
    },
    {
      key: "severity",
      label: "Severity",
      sortable: false,
      align: "right",
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
      <Helmet>
        <title>VORA - Critical Gaps</title>
      </Helmet>
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
            Active control failures exceeding risk tolerance thresholds. Each
            gap requires remediation evidence before the next audit cycle.
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
              <StatBox
                key={p.label}
                label={p.label}
                value={p.value}
                valueColor={p.color}
              />
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
        error={error}
      />
    </div>
  );
}
