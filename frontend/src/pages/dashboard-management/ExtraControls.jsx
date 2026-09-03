/* eslint-disable react/prop-types */
import { Link, useNavigate } from "react-router-dom";
import DataTable from "@/components/data-table/DataTable";
import Icon from "@/components/custom/Icon";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { getAuditorExtraControls } from "@/services/dashboardService";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { capitalizeFirstLetter } from "@/utils/stringUtils";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";

export default function ExtraControls() {
  usePageTitle("extra-controls", "Extra Controls");

  const navigate = useNavigate();

  const {
    data: rawData,
    loading,
    error,
    pagination,
    searchTerm,
    onSearch,
  } = useTableData(getAuditorExtraControls, {
    defaultSortBy: "ctrlId",
    defaultSortOrder: "asc",
  });

  const pagedData = Array.isArray(rawData) ? rawData : rawData?.results || [];

  // ── Column definitions ──────────────────────────────────────────────────────
  const columns = [
    {
      key: "frameworkVersion",
      label: "Version",
      sortable: false,
      render: (value, row) => (
        <FrameworkMiniCard
          name={row.frameworkName}
          description={row.frameworkVersion}
          link={`/dashboard/framework/${row.id}`}
        />
      ),
    },
    {
      key: "ctrlId",
      label: "Ctrl ID",
      sortable: false,
      align: "center",
      render: (value) => (
        <span className="font-mono text-xs font-bold text-secondary bg-muted px-2 py-1 rounded whitespace-nowrap">
          {value}
        </span>
      ),
    },
    {
      key: "control",
      label: "control",
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
      key: "deploymentPoints",
      label: "Points",
      sortable: false,
      align: "center",
      render: (value) => <span className="">{value}</span>,
    },
  ];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 my-2">
      {/* Hero summary banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-amber-400">
              {pagination?.totalItems || 0}
            </span>{" "}
            <span className="text-base font-semibold">
              Controls Above Standard Requirements
            </span>
          </p>
          <p className="text-xs text-muted-foreground">
            Your organization implements additional controls beyond mandatory
            framework minimums. These enhance your security posture and
            demonstrate proactive compliance maturity.
          </p>
        </div>

        {/* Right — Button */}
        <div className="shrink-0">
          <Button
            size="xs"
            variant="outline"
            onClick={() => navigate("/dashboard")}
          >
            <Icon name="arrow-left" size="13px" /> Back to Dashboard
          </Button>
        </div>
      </div>

      {/* DataTable — Extra Controls Register */}
      <DataTable
        entityName="Controls"
        columns={columns}
        data={pagedData}
        loading={loading}
        onSearch={onSearch}
        searchTerm={searchTerm}
        onClearSearch={() => onSearch("")}
        pagination={pagination}
        searchPlaceholder="Search extra controls..."
        emptyMessage={
          searchTerm
            ? "No controls match your filters"
            : "No extra controls found"
        }
        error={error}
      />
    </div>
  );
}
