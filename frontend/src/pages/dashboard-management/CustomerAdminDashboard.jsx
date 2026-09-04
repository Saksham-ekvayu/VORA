/* eslint-disable react/prop-types */

import { useState, useEffect, useCallback, useMemo } from "react";
import { Helmet } from "react-helmet-async";
import { toast } from "sonner";
import { Link, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { CheckIcon, ChevronDownIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import CardWrapper from "./components/CardWrapper";
import DateFilter from "./components/DateFilter";
import { useDateFilter } from "./hooks/useDateFilter";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import DashboardError from "./components/DashboardError";
import Icon from "@/components/custom/Icon";
import { useAuth } from "@/context/authContext/useAuth";
import { getRoleLabel } from "@/utils/commonUtils";
import {
  formatDateWithMonthName,
  formatDateWithMonthNameAndTime,
} from "@/utils/dateFormatter";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { getCustomerAdminDashboardAnalytics } from "@/services/dashboardService";

// ─── Chart colours ────────────────────────────────────────────────────────────
const FW_COLORS = ["#0f9f93", "#8b5cf6", "#3b82f6", "#f97316", "#ec4899"];

// ─── Top Stat Card ────────────────────────────────────────────────────────────
function TopStatCard({
  icon,
  iconColor = "text-primary",
  iconBg = "bg-primary/10",
  borderColor = "border-primary/40",
  title,
  value,
  onClick,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded bg-card border border-border p-4 flex items-center gap-4 text-left w-full hover:border-primary/40 hover:shadow-md transition-all group cursor-pointer"
    >
      <div
        className={cn(
          "w-12 h-12 rounded shrink-0 flex items-center justify-center transition-transform duration-300 group-hover:scale-105 border",
          borderColor,
          iconBg,
          iconColor
        )}
      >
        <Icon name={icon} size="24px" />
      </div>
      <div className="flex flex-col gap-1.5 overflow-hidden">
        <p
          className="text-sm font-medium text-foreground truncate"
          title={title}
        >
          {title}
        </p>
        <p
          className={cn("text-2xl font-bold leading-none truncate", iconColor)}
        >
          {value ?? "—"}
        </p>
      </div>
    </button>
  );
}

// ─── Profiles by Role ─────────────────────────────────────────────────────────
function ProfilesByRoleCard({ profilesByRole = [], total = 0 }) {
  const COLORS = [
    { bar: "bg-teal-500" },
    { bar: "bg-violet-500" },
    { bar: "bg-blue-500" },
    { bar: "bg-orange-400" },
  ];
  return (
    <CardWrapper
      title="Profiles by Role"
      right={
        <Link
          to="/profiles"
          className="text-primary flex items-center gap-1 text-xs font-semibold hover:underline"
        >
          View all <Icon name="arrow-right" size="13px" />
        </Link>
      }
      className="h-full"
    >
      <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border-b border-border pb-1.5 mb-2">
        <span>Role</span>
        <span>Distribution</span>
      </div>
      <div className="space-y-3">
        {profilesByRole.length === 0 && (
          <p className="text-xs text-muted-foreground py-4 text-center">
            No profile data available.
          </p>
        )}
        {profilesByRole.map((r, i) => (
          <div key={r.role} className="flex items-center gap-2">
            <span
              className="text-[11px] font-semibold px-2.5 py-0.5 rounded text-white shrink-0"
              style={{
                backgroundColor: ["#0f9f93", "#8b5cf6", "#3b82f6", "#f97316"][
                  i % 4
                ],
              }}
            >
              {r.role}
            </span>
            <div className="flex-1 h-2.5 rounded-full bg-muted overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full",
                  COLORS[i % COLORS.length].bar
                )}
                style={{
                  width: `${total ? Math.round((r.count / total) * 100) : 0}%`,
                }}
              />
            </div>
            <span className="text-xs font-bold text-foreground w-6 text-right shrink-0">
              {r.count}
            </span>
          </div>
        ))}
      </div>
    </CardWrapper>
  );
}

// ─── Framework Setup Filter ───────────────────────────────────────────────────
function FrameworkSetupFilter({ frameworks = [], selectedId, onChange }) {
  const [open, setOpen] = useState(false);
  const activeId = selectedId || frameworks?.[0]?.id;

  const getSelectedName = () => {
    if (!frameworks?.length) return "No Frameworks";
    return (
      frameworks?.find((f) => f.id === activeId)?.frameworkVersion || "Select"
    );
  };

  const handleSelect = (id) => {
    onChange(id);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={!frameworks?.length}
          className={cn(
            "flex items-center gap-1.5 text-xs font-medium",
            "border-border bg-accent hover:border-primary hover:bg-primary/10",
            open && "border-primary bg-primary/10",
            !frameworks?.length && "opacity-50 cursor-not-allowed"
          )}
        >
          <span className="truncate max-w-32">{getSelectedName()}</span>
          <ChevronDownIcon className="size-3 text-muted-foreground shrink-0" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" sideOffset={6} className="w-37 p-1 shadow-xl">
        <div className="space-y-0.5">
          {frameworks?.length === 0 ? (
            <div className="px-2 py-2 text-xs text-muted-foreground text-center">
              No frameworks found
            </div>
          ) : (
            frameworks.map((f) => {
              const active = activeId === f.id;
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => handleSelect(f.id)}
                  className={cn(
                    "w-full flex items-center justify-between rounded px-2 py-1.5 text-xs text-left transition-colors cursor-pointer",
                    active
                      ? "bg-primary/15 text-primary font-medium"
                      : "text-foreground hover:bg-accent"
                  )}
                >
                  {f.frameworkVersion}
                  {active && <CheckIcon className="size-3 shrink-0" />}
                </button>
              );
            })
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// Custom tooltip: framework name + Assigned on / Deployed on / Status
const CustomTooltip = ({ active, payload, data }) => {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="bg-background rounded-xl px-4 py-3 shadow-2xl border border-border min-w-50">
      <div className="flex items-center gap-2 mb-2 pb-2 border-b border-border">
        <span
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{
            backgroundColor: FW_COLORS[data.indexOf(item) % FW_COLORS.length],
          }}
        />
        <p className="text-sm font-bold text-foreground">{item.version}</p>
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between gap-6">
          <span className="text-xs text-muted-foreground">Assigned on</span>
          <span className="text-xs font-semibold text-foreground">
            {formatDateWithMonthName(item.assignedOn)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-6">
          <span className="text-xs text-muted-foreground">Deployed on</span>
          <span className="text-xs font-semibold text-foreground">
            {formatDateWithMonthName(item.deployedOn)}
          </span>
        </div>
      </div>
    </div>
  );
};

// ─── Deployed Frameworks Donut Chart ─────────────────────────────────────────

function DeployedFrameworksChart({ data = [] }) {
  const [activeIndex, setActiveIndex] = useState(null);

  return (
    <div className="grid grid-cols-2 gap-4 items-center w-full max-w-xl mx-auto">
      {/* Donut chart — left column */}
      <div
        className="relative shrink-0 mx-auto"
        style={{ width: 220, height: 220 }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={62}
              outerRadius={98}
              paddingAngle={2}
              minAngle={2}
              activeIndex={activeIndex}
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
              isAnimationActive={false}
              stroke="#fff"
              strokeWidth={2}
            >
              {data.map((entry, i) => (
                <Cell
                  key={`${entry.name}-${i}`}
                  fill={FW_COLORS[i % FW_COLORS.length]}
                />
              ))}
            </Pie>

            <Tooltip
              content={<CustomTooltip data={data} />}
              wrapperStyle={{ zIndex: 1000 }}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Centre */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-2xl font-bold leading-none text-foreground">
              {data.length}
            </p>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              frameworks
            </p>
          </div>
        </div>
      </div>

      {/* Legend — right column */}
      <div className="flex flex-col justify-center gap-2.5 min-w-0 pl-4">
        {data.map((entry, i) => (
          <div
            key={entry.name}
            className="flex items-center gap-2 cursor-default"
          >
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: FW_COLORS[i % FW_COLORS.length] }}
            />
            <span
              className={cn(
                "text-xs transition-colors",
                activeIndex === i
                  ? "text-foreground font-semibold"
                  : "text-muted-foreground"
              )}
            >
              {entry.name} {entry.version ? `(${entry.version})` : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Assigned Frameworks Table ────────────────────────────────────────────────
function AssignedFrameworksTable({ rows = [] }) {
  if (!rows.length) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-2 text-center">
        <Icon name="assignment" size="40px" className="text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          No assigned frameworks yet.
        </p>
      </div>
    );
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="text-[10px] uppercase tracking-wide">
            Framework
          </TableHead>
          <TableHead className="text-[10px] uppercase tracking-wide text-right">
            Version
          </TableHead>
          <TableHead className="text-[10px] uppercase tracking-wide text-right">
            Assignment
          </TableHead>
          <TableHead className="text-[10px] uppercase tracking-wide text-right">
            Finalisation
          </TableHead>
          <TableHead className="text-[10px] uppercase tracking-wide text-right">
            Action
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.slice(0, 6).map((fw) => (
          <TableRow key={fw.id || fw.name}>
            <TableCell>
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs font-medium text-foreground truncate inline-block">
                  {fw.name}
                </span>
              </div>
            </TableCell>
            <TableCell className="text-xs text-muted-foreground text-right">
              {fw.version}
            </TableCell>
            <TableCell
              className={cn(
                "text-xs font-semibold capitalize text-right",
                fw.assignmentStatus === "assigned"
                  ? "text-teal-500"
                  : "text-muted-foreground"
              )}
            >
              {fw.assignmentStatus}
            </TableCell>
            <TableCell
              className={cn(
                "text-xs font-semibold capitalize text-right",
                fw.finalizationStatus === "finalized"
                  ? "text-blue-500"
                  : "text-amber-500"
              )}
            >
              {fw.finalizationStatus}
            </TableCell>
            <TableCell className="text-right">
              {fw.id ? (
                <Link
                  to={`/assigned-frameworks/${fw.id}`}
                  className="text-xs text-primary font-medium inline-flex items-center justify-end gap-0.5 hover:underline whitespace-nowrap"
                >
                  View
                </Link>
              ) : (
                <span className="text-right text-xs text-muted-foreground">
                  —
                </span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ─── Recent Activity Feed ─────────────────────────────────────────────────────
const ACT_DOTS = [
  "bg-teal-500",
  "bg-blue-500",
  "bg-amber-500",
  "bg-violet-500",
  "bg-orange-400",
];

function RecentActivityFeed({ items = [] }) {
  if (!items.length) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-2 text-center">
        <Icon name="list" size="40px" className="text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No recent activity.</p>
      </div>
    );
  }
  return (
    <div className="overflow-y-auto pr-0.5" style={{ maxHeight: "220px" }}>
      {items.slice(0, 10).map((item, i) => (
        <div
          key={item.id || i}
          className="flex items-start gap-3 py-2.5 border-b border-border last:border-0"
        >
          <span
            className={cn(
              "mt-1.5 w-2.5 h-2.5 rounded-full shrink-0",
              ACT_DOTS[i % ACT_DOTS.length]
            )}
          />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-foreground leading-relaxed">
              {item.message || item.description}
            </p>
            {item.actor && (
              <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                {item.actor}
              </p>
            )}
          </div>
          <span className="text-[11px] text-muted-foreground shrink-0 whitespace-nowrap">
            {item.timeAgo ||
              (item.createdAt
                ? formatDateWithMonthNameAndTime(item.createdAt)
                : "")}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function CustomerAdminDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [selectedFrameworkId, setSelectedFrameworkId] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const { datePreset, startDate, endDate, handleDateChange } = useDateFilter();

  const fetchDashboardData = useCallback(
    async (dateRange, isBackgroundRefresh = false) => {
      try {
        if (!isBackgroundRefresh) {
          setLoading(true);
        }
        setLoadError(null);
        const response = await getCustomerAdminDashboardAnalytics(dateRange);
        if (response?.success) {
          setDashboardData(response.data);
        } else {
          setLoadError(response?.message);
        }
      } catch (err) {
        console.error("Dashboard error:", err);
        setLoadError(err.message || "Failed to load dashboard data");
        if (!isBackgroundRefresh) {
          toast.error(err.message || "Failed to load dashboard data");
        }
      } finally {
        if (!isBackgroundRefresh) {
          setLoading(false);
        }
      }
    },
    []
  );

  useEffect(() => {
    fetchDashboardData({ startDate, endDate }, dashboardData !== null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDate, endDate, fetchDashboardData]);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const {
    stats = {},
    profilesByRole = [],
    setupProgress = {},
    setupProgressByFramework = [],
    deployedFrameworks = [],
    assignedFrameworks = [],
    recentActivity = [],
  } = dashboardData || {};

  const calculatedTotal = profilesByRole.reduce(
    (s, r) => s + (r.count || 0),
    0
  );
  const profileTotal =
    calculatedTotal > 0 ? calculatedTotal : stats.totalProfiles || 0;

  // Active setup progress — defaults to first framework in list
  const activeSetupProgress = useMemo(() => {
    const list = setupProgressByFramework || [];
    if (!list.length) return setupProgress;
    const found = list.find((f) => f.id === selectedFrameworkId);
    return found || list[0];
  }, [setupProgressByFramework, selectedFrameworkId, setupProgress]);

  const cfgPct =
    activeSetupProgress.percentage ??
    (activeSetupProgress.total
      ? Math.round(
          (activeSetupProgress.configured / activeSetupProgress.total) * 100
        )
      : 0);

  const getMonitoringSetupValue = () => {
    if (stats.controlsConfigured != null && stats.controlsTotal != null) {
      return `${stats.controlsConfigured} / ${stats.controlsTotal}`;
    }
    if (setupProgress.configured != null) {
      return `${setupProgress.configured} / ${setupProgress.total ?? "?"}`;
    }
    return "—";
  };

  const monitoringSetupValue = getMonitoringSetupValue();

  if (loading) return <LoadingSpinner className="min-h-[70vh]" />;

  if (loadError || !dashboardData) {
    return (
      <DashboardError
        error={loadError}
        onRetry={() => fetchDashboardData({ startDate, endDate })}
      />
    );
  }

  return (
    <div className="space-y-3 my-2">
      <Helmet>
        <title>VORA - Customer Admin Dashboard</title>
      </Helmet>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2 px-1">
        <h2 className="text-lg font-semibold text-foreground">
          Welcome, {user?.name}
          <span className="text-sm font-normal text-muted-foreground ml-1">
            ({user?.role && getRoleLabel(user.role)})
          </span>
          {" 👋"}
        </h2>
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <p className="text-[10px] font-medium text-foreground">
              {currentTime.toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </p>
            <p className="text-xs text-muted-foreground font-mono">
              {currentTime.toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: true,
              })}
            </p>
          </div>
          <DateFilter
            value={datePreset}
            startDate={startDate}
            endDate={endDate}
            onChange={handleDateChange}
          />
        </div>
      </div>

      {/* ── Row 1: Top stat cards ──────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <TopStatCard
          title="Total Profiles"
          icon="users"
          iconColor="text-primary"
          iconBg="bg-primary/10"
          borderColor="border-primary/40"
          value={profileTotal}
          onClick={() => navigate("/profiles")}
        />
        <TopStatCard
          title="Assigned Frameworks"
          icon="assignment"
          iconColor="text-violet-500"
          iconBg="bg-violet-500/10"
          borderColor="border-violet-500/40"
          value={stats.assignedFrameworks ?? stats.totalAssignedFrameworks ?? 0}
          onClick={() => navigate("/assigned-frameworks")}
        />
        <TopStatCard
          title="Deployment Frameworks"
          icon="cloud-upload"
          iconColor="text-blue-500"
          iconBg="bg-blue-500/10"
          borderColor="border-blue-500/40"
          value={
            stats.deploymentFrameworks ?? stats.totalDeploymentFrameworks ?? 0
          }
          onClick={() => navigate("/deployment-frameworks")}
        />
        <TopStatCard
          title="Monitoring Point Configured"
          icon="shield-check"
          iconColor="text-emerald-500"
          iconBg="bg-emerald-500/10"
          borderColor="border-emerald-500/40"
          value={monitoringSetupValue}
          onClick={() => navigate("/monitoring-setup")}
        />
      </div>

      {/* ── Row 2: (Monitoring Setup + Profiles) | Timeline Chart ─────── */}
      <div className="grid xl:grid-cols-2 gap-3 items-stretch">
        <div className="flex flex-col gap-3 h-full">
          {/* Monitoring Point Setup Progress */}
          <CardWrapper
            title="Monitoring Point Configured Progress"
            right={
              <div className="flex items-center gap-2">
                <FrameworkSetupFilter
                  frameworks={setupProgressByFramework}
                  selectedId={selectedFrameworkId}
                  onChange={setSelectedFrameworkId}
                />
              </div>
            }
          >
            <div className="space-y-2 pt-1">
              <div className="h-2.5 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500"
                  style={{ width: `${Math.min(cfgPct, 100)}%` }}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-muted-foreground">
                  {activeSetupProgress.configured ?? 0} /{" "}
                  {activeSetupProgress.total ?? 0} Monitoring point
                </span>
                <span className="text-xs font-bold text-primary">
                  {cfgPct}% complete
                </span>
              </div>
            </div>
          </CardWrapper>

          {/* Profiles by Role */}
          <div className="flex-1 min-h-0">
            <ProfilesByRoleCard
              profilesByRole={profilesByRole}
              total={profileTotal}
            />
          </div>
        </div>

        {/* Framework Timeline Chart */}
        <CardWrapper
          title="Deployed Frameworks"
          right={
            <div className="flex items-center gap-2">
              <Link
                to="/assigned-frameworks"
                className="text-primary text-xs flex items-center gap-1 font-semibold hover:underline"
              >
                View all <Icon name="arrow-right" size="13px" />
              </Link>
            </div>
          }
          className="flex flex-col"
        >
          <p className="text-[11px] text-muted-foreground mb-2">
            Hover a slice to see assignment &amp; deployment details
          </p>
          <DeployedFrameworksChart data={deployedFrameworks} />
        </CardWrapper>
      </div>

      {/* ── Row 3: Assigned Frameworks | Recent Activity ───────────────── */}
      <div className="grid xl:grid-cols-2 gap-3 items-stretch">
        <CardWrapper
          title="Assigned Frameworks"
          right={
            <Link
              to="/assigned-frameworks"
              className="text-primary flex items-center gap-1 text-xs font-semibold hover:underline"
            >
              View all <Icon name="arrow-right" size="14px" />
            </Link>
          }
          className="flex flex-col"
        >
          <AssignedFrameworksTable rows={assignedFrameworks} />
        </CardWrapper>

        <CardWrapper title="Recent Activity" className="flex flex-col">
          <RecentActivityFeed items={recentActivity} />
        </CardWrapper>
      </div>
    </div>
  );
}
