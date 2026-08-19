/* eslint-disable react/prop-types */
import { useState, useMemo, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Icon from "@/components/custom/Icon";
import SearchInput from "@/components/custom/SearchInput";
import TableHeaderActions from "@/components/custom/TableHeaderActions";
import CustomPagination from "@/components/custom/CustomPagination";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { getAuditorDeploymentPoints } from "@/services/dashboardService";
import { Skeleton } from "@/components/ui/skeleton";
import { capitalizeFirstLetter } from "@/utils/stringUtils";

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

function ControlBar({ name, pct }) {
  // Determine semantic color based on percentage
  const getSemanticColor = (val) => {
    if (val <= 30) return "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]";
    if (val <= 70) return "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]";
    return "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]";
  };

  return (
    <div className="flex items-center gap-3 p-1.5 rounded transition-colors hover:bg-muted/50 group">
      <span className="text-sm font-medium group-hover:text-primary transition-colors flex-1 truncate" title={capitalizeFirstLetter(name)}>
        {capitalizeFirstLetter(name)}
      </span>
      <div className="w-32 h-2.5 rounded-full bg-muted overflow-hidden shrink-0 shadow-inner">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${getSemanticColor(pct)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-bold text-foreground w-10 text-right shrink-0 tabular-nums">
        {pct}%
      </span>
    </div>
  );
}

// ─── Deployment point card ────────────────────────────────────────────────────

function DeploymentCard({ point }) {
  return (
    <div className="rounded border border-border/60 bg-card/80 backdrop-blur-xl shadow-lg flex flex-col overflow-hidden transition-shadow hover:shadow-xl">
      {/* Card Header */}
      <div className="flex items-center justify-between p-4 bg-linear-to-r from-primary/10 via-primary/5 to-transparent border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-background shadow-sm border border-primary/20">
            <Icon name="layers" size="20px" className="text-primary drop-shadow-sm" />
          </div>
          <div>
            <p className="text-base font-extrabold text-foreground tracking-tight">
              {point.frameworkName} <span className="text-primary font-semibold opacity-80">({point.frameworkVersion})</span>
            </p>
            <p className="text-xs font-medium text-muted-foreground mt-0.5">
              {point.instances} Total Control Instances Evaluated
            </p>
          </div>
        </div>
      </div>

      {/* Controls Grid */}
      <div className="p-4 max-h-100 overflow-y-auto custom-scrollbar">
        {point.controls && point.controls.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-1">
            {point.controls.map((ctrl, idx) => (
              <ControlBar key={`${ctrl.name}-${idx}`} {...ctrl} />
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-muted-foreground text-sm">
            No control data available.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function DeploymentPoints() {
  usePageTitle("deployment-points", "Deployment Points");

  const navigate = useNavigate();

  const [deploymentPoints, setDeploymentPoints] = useState([]);
  const [totalInstancesCount, setTotalInstancesCount] = useState(0);
  const [paginationObj, setPaginationObj] = useState({
    currentPage: 1,
    totalPages: 1,
    limit: 10,
    totalItems: 0,
    hasPrevPage: false,
    hasNextPage: false,
  });
  const [isLoading, setIsLoading] = useState(true);

  const [searchTerm, setSearchTerm] = useState("");
  const [frameworkFilter, setFrameworkFilter] = useState("All Frameworks");
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await getAuditorDeploymentPoints({
        page,
        limit,
        search: searchTerm,
        frameworkFilter: frameworkFilter !== "All Frameworks" ? frameworkFilter : "",
      });
      if (res?.success) {
        setDeploymentPoints(res.data?.results || []);
        setTotalInstancesCount(res.data?.totalInstances || 0);
        if (res.pagination) {
          setPaginationObj({
            ...res.pagination,
            limit: res.pagination.itemsPerPage,
            onLimitChange: (newLimit) => {
              setLimit(newLimit);
              setPage(1);
            },
            onPageChange: (newPage) => {
              setPage(newPage);
            }
          });
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [page, limit, searchTerm, frameworkFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSearch = useCallback((term) => {
    setSearchTerm(term);
    setPage(1);
  }, []);

  const frameworkOptions = useMemo(() => {
    // Note: This ideally should come from a separate API or aggregated list if paginated.
    // Assuming backend returns a small list or we just extract from current page for now.
    const versions = new Set(deploymentPoints.map((dp) => dp.frameworkVersion).filter(Boolean));
    return ["All Frameworks", ...Array.from(versions)];
  }, [deploymentPoints]);

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

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="grid gap-3 md:grid-cols-2">
          <Skeleton className="h-48 w-full rounded" />
          <Skeleton className="h-48 w-full rounded" />
        </div>
      );
    }

    if (deploymentPoints.length === 0) {
      return (
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
      );
    }

    return (
      <div className="">
        {deploymentPoints.map((point, idx) => (
          <DeploymentCard key={point.id || idx} point={point} />
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-3 my-2">
      {/* Hero banner */}
      <div className="rounded border border-border bg-linear-to-br from-background to-card shadow-lg p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-2xl font-extrabold text-foreground leading-tight">
            <span className="text-primary">Deployment Points</span>
            <span className="text-base font-semibold text-muted-foreground ml-2">
              — {totalInstancesCount} Total Control Instances
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
              value={paginationObj.totalItems}
              valueColor="text-primary"
            />
            <MiniStatBox
              label="Total Instances"
              value={totalInstancesCount}
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
        <div className="p-2">
          {renderContent()}
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
