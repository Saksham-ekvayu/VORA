/* eslint-disable react/prop-types */
import { Link, useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import CustomBadge from "@/components/custom/CustomBadge";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";

import { useTableData } from "@/components/data-table/hooks/useTableData";
import { getAuditorControlsPassing } from "@/services/dashboardService";

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

export default function ControlsPassing() {
  usePageTitle("controls-passing", "Controls Passing");

  const navigate = useNavigate();
  const urlParams = new URLSearchParams(globalThis.location.search);
  const statusFilter = urlParams.get("statusFilter") || "";

  const {
    data: rawData,
    loading,
    pagination,
    searchTerm,
    onSearch,
    onFilterChange,
  } = useTableData(getAuditorControlsPassing, {
    defaultSortBy: "ctrlId",
    defaultSortOrder: "asc",
    defaultLimit: 10,
    emptyMessage: "No controls found",
  });

  const tableData = Array.isArray(rawData) ? [] : rawData?.results || [];
  const STATS = (Array.isArray(rawData) ? null : rawData?.stats) || {
    passing: 0,
    failing: 0,
    warning: 0,
    notEvaluated: 0,
    total: 0,
    passRate: 0,
    failingOrEvidence: 0,
  };

  const handleStatusFilter = (val) => {
    onFilterChange("statusFilter", val);
  };

  // ── Column definitions ──────────────────────────────────────────────────────
  const columns = [
    {
      key: "frameworkVersion",
      label: "Version",
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
      key: "ctrlId",
      label: "Ctrl ID",
      sortable: false,
      render: (value) => (
        <span className="font-mono text-xs font-bold text-secondary bg-muted px-2 py-1 rounded whitespace-nowrap">
          {value}
        </span>
      ),
    },
    {
      key: "control",
      label: "Control",
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
      key: "passRate",
      label: "Pass Rate",
      sortable: false,
      render: (value, row) => {
        let color = "text-emerald-500";
        if (row.status === "Failing") color = "text-red-500";
        else if (row.status === "Warning") color = "text-amber-500";
        return (
          <span className={`text-sm font-bold block text-center ${color}`}>
            {value}%
          </span>
        );
      },
    },
    {
      key: "status",
      label: "Status",
      sortable: false,
      render: (value) => <CustomBadge status={value} size="sm" />,
    },
    {
      key: "lastRun",
      label: "Last Run",
      sortable: false,
      render: (value) => (
        <span className="whitespace-nowrap">
          {formatDateWithMonthNameAndTime(value)}
        </span>
      ),
    },
  ];

  // ── Header actions (status dropdown) ───────────────────
  const getHeaderActions = () => [
    {
      type: "dropdown",
      label: statusFilter || "All Status",
      triggerClassName: "w-fit min-w-28",
      options: [
        { label: "All Status", onClick: () => handleStatusFilter("") },
        {
          label: "Passing",
          separatorBefore: true,
          onClick: () => handleStatusFilter("Passing"),
        },
        { label: "Failing", onClick: () => handleStatusFilter("Failing") },
        { label: "Warning", onClick: () => handleStatusFilter("Warning") },
        {
          label: "Not Evaluated",
          onClick: () => handleStatusFilter("Not Evaluated"),
        },
      ],
    },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 my-2">
      {/* Hero summary banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card shadow-lg p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-primary">{STATS.passing}</span>
            <span className="text-muted-foreground text-lg font-semibold">
              {" "}
              / {pagination.totalItems || 0}
            </span>{" "}
            <span className="text-base font-semibold">Controls Passing</span>
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">
            {STATS.passRate}% pass rate across all deployed controls.{" "}
            {STATS.failingOrEvidence} controls currently failing or requiring
            evidence.
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
            <StatBox
              label="Passing"
              value={STATS.passing}
              valueColor="text-emerald-500"
            />
            <StatBox
              label="Failing"
              value={STATS.failing}
              valueColor="text-red-500"
            />
            <StatBox
              label="Warning"
              value={STATS.warning}
              valueColor="text-amber-500"
            />
            <StatBox
              label="Not Evaluated"
              value={STATS.notEvaluated}
              valueColor="text-muted-foreground"
            />
          </div>
        </div>
      </div>

      {/* DataTable */}
      <DataTable
        entityName="Controls"
        columns={columns}
        data={tableData}
        loading={loading}
        onSearch={onSearch}
        searchTerm={searchTerm}
        headerActions={getHeaderActions()}
        pagination={pagination}
      />
    </div>
  );
}
