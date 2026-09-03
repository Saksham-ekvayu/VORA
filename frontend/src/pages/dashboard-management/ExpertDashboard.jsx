/* eslint-disable react/prop-types */

import { useEffect, useState, useCallback } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Award, CloudUpload, ExternalLink, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useDateFilter } from "./hooks/useDateFilter";
import DateFilter from "./components/DateFilter";
import { getExpertDashboardAnalytics } from "@/services/frameworkService";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import DashboardError from "./components/DashboardError";
import {
  STATUS_APPROVED,
  STATUS_PENDING,
  STATUS_REJECTED,
  STATUS_REVOKED,
  getAccessStatusFilterLabel,
  getApprovalStatusColor,
} from "@/utils/commonUtils";

const ACCESS_STATUS_META = {
  [STATUS_APPROVED]: { color: "#0f9f93" },
  [STATUS_PENDING]: { color: "#eab308" },
  [STATUS_REJECTED]: { color: "#ff5a45" },
  [STATUS_REVOKED]: { color: "#2f80ed" },
};

const CODE_BADGE_CLASSES = [
  "bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300",
  "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
  "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300",
  "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
];

const STAT_TONE_CLASSES = {
  teal: {
    icon: "bg-primary/10 text-primary border-primary/20",
    value: "text-primary",
    footer: "from-primary/10 to-primary/5 text-primary",
  },
  violet: {
    icon: "bg-secondary/10 text-secondary border-secondary/20",
    value: "text-secondary",
    footer: "from-secondary/10 to-secondary/5 text-secondary",
  },
  orange: {
    icon: "bg-warning/10 text-warning border-warning/20",
    value: "text-warning",
    footer: "from-warning/10 to-warning/5 text-foreground",
  },
};

function getCodeBadgeClass(code) {
  if (!code) return "bg-muted text-muted-foreground";

  const colorIndex = String(code)
    .split("")
    .reduce((sum, character) => sum + character.codePointAt(0), 0);

  return CODE_BADGE_CLASSES[colorIndex % CODE_BADGE_CLASSES.length];
}

function buildStats(stats) {
  return [
    {
      title: "Framework Categories",
      value: stats.totalCategories || 0,
      description: "Approved, pending, rejected and revoked",
      action: "View All Categories",
      actionPath: "/framework-categories",
      icon: LockKeyhole,
      tone: "teal",
    },
    {
      title: "Framework Uploads",
      value: stats.totalUploads || 0,
      description: "Submitted in the selected date range",
      action: "View All Uploads",
      actionPath: "/frameworks",
      icon: CloudUpload,
      tone: "violet",
    },
    {
      title: "Framework Approval Progress",
      value: `${stats.approvalProgress || 0}%`,
      description: `${stats.approvedUploads || 0} approved out of ${
        stats.totalUploads || 0
      } uploaded frameworks`,
      action: "View Approval Details",
      actionPath: "/frameworks?approvalStatus=approved",
      icon: Award,
      tone: "orange",
      progress: stats.approvalProgress || 0,
    },
  ];
}

function formatPercentage(value, total) {
  if (!total) return "0.0%";
  return `${((value / total) * 100).toFixed(1)}%`;
}

function buildAccessStatusChartData(accessStatus = {}) {
  const total = Object.keys(ACCESS_STATUS_META).reduce(
    (sum, status) => sum + (accessStatus[status] || 0),
    0
  );

  return Object.entries(ACCESS_STATUS_META).map(([status, meta]) => {
    const value = accessStatus[status] || 0;

    return {
      status,
      name: getAccessStatusFilterLabel(status),
      color: meta.color,
      value,
      percentage: formatPercentage(value, total),
    };
  });
}

function PageHeader({ datePreset, startDate, endDate, handleDateChange }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <p className="mt-1 text-lg text-muted-foreground">
        Welcome, Expert! Here's what's happening with your frameworks.
      </p>
      <DateFilter
        value={datePreset}
        startDate={startDate}
        endDate={endDate}
        onChange={handleDateChange}
      />
    </div>
  );
}

function StatCard({ stat }) {
  const tone = STAT_TONE_CLASSES[stat.tone];
  const IconComponent = stat.icon;

  return (
    <div className="flex h-full flex-col overflow-hidden rounded border border-border bg-card text-card-foreground hover:shadow-md transition-all group">
      <Link to={stat.actionPath} className="flex flex-1 items-start gap-5 p-4">
        <div
          className={cn(
            "flex size-14 shrink-0 items-center justify-center rounded border group-hover:scale-105 duration-300",
            tone.icon
          )}
        >
          <IconComponent className="size-7" strokeWidth={2} />
        </div>
        <div className="min-w-0 flex-1 pt-1">
          <p className="text-sm font-semibold text-foreground">{stat.title}</p>
          <p className={cn("mt-2 text-3xl font-bold leading-none", tone.value)}>
            {stat.value}
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            {stat.description}
          </p>
        </div>
      </Link>
    </div>
  );
}

function CardShell({ title, actionLabel, actionPath, children, className }) {
  let actionButton = null;

  if (actionLabel && actionPath) {
    actionButton = (
      <Button
        asChild
        variant="outline"
        size="sm"
        className="h-9 gap-2 rounded border-border bg-card px-3 text-xs font-semibold text-primary"
      >
        <Link to={actionPath}>
          {actionLabel}
          <ExternalLink className="size-3.5" />
        </Link>
      </Button>
    );
  } else if (actionLabel) {
    actionButton = (
      <Button
        variant="outline"
        size="sm"
        className="h-9 gap-2 rounded border-border bg-card px-3 text-xs font-semibold text-primary"
      >
        {actionLabel}
        <ExternalLink className="size-3.5" />
      </Button>
    );
  }

  return (
    <section
      className={cn(
        "rounded border border-border bg-card text-card-foreground shadow-sm",
        className
      )}
    >
      <div className="flex items-center justify-between gap-3 border-b border-transparent px-4 py-3">
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
        {actionButton}
      </div>
      {children}
    </section>
  );
}

function UploadTrendChart({ data }) {
  const maxUploads = Math.max(...data.map((item) => item.uploads || 0), 0);

  return (
    <ResponsiveContainer width="100%" height={230}>
      <AreaChart data={data} margin={{ top: 8, right: 22, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="uploadTrend" x1="0" x2="0" y1="0" y2="1">
            <stop offset="5%" stopColor="#0f9f93" stopOpacity={0.24} />
            <stop offset="95%" stopColor="#0f9f93" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid
          stroke="var(--color-border)"
          strokeDasharray="4 4"
          vertical={false}
        />
        <XAxis
          dataKey="month"
          axisLine={{ stroke: "var(--color-border)" }}
          tick={{ fill: "var(--color-muted-foreground)", fontSize: 12 }}
          tickLine={false}
        />
        <YAxis
          axisLine={{ stroke: "var(--color-border)" }}
          allowDecimals={false}
          domain={[0, Math.max(5, maxUploads + 2)]}
          label={{
            value: "Uploads",
            angle: -90,
            position: "insideLeft",
            fill: "var(--color-muted-foreground)",
            fontSize: 12,
          }}
          tick={{ fill: "var(--color-muted-foreground)", fontSize: 12 }}
          tickLine={false}
        />
        <Tooltip
          cursor={{ stroke: "#0f9f93", strokeDasharray: "3 3" }}
          contentStyle={{
            borderRadius: 6,
            backgroundColor: "var(--color-card)",
            borderColor: "var(--color-border)",
            color: "var(--color-card-foreground)",
            fontSize: 12,
          }}
        />
        <Area
          dataKey="uploads"
          fill="url(#uploadTrend)"
          stroke="#0f9f93"
          strokeWidth={3}
          dot={{ r: 5, fill: "#0f9f93", stroke: "#0f9f93" }}
          activeDot={{ r: 6 }}
          label={{
            position: "top",
            dy: -6,
            fill: "var(--color-foreground)",
            fontSize: 13,
            fontWeight: 700,
          }}
          type="monotone"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function renderPieLabel({ cx, cy, midAngle, outerRadius, value, payload }) {
  if (!value) return null;

  const percentage = payload?.percentage || "0.0%";
  const radius = outerRadius * 0.72;
  const radians = (Math.PI / 180) * -midAngle;
  const x = cx + radius * Math.cos(radians);
  const y = cy + radius * Math.sin(radians);

  return (
    <text
      dominantBaseline="central"
      fill="#ffffff"
      fontSize={14}
      fontWeight={700}
      textAnchor="middle"
      x={x}
      y={y}
    >
      <tspan x={x} dy="-0.35em">
        {value}
      </tspan>
      <tspan x={x} dy="1.25em" fontSize={11}>
        ({percentage})
      </tspan>
    </text>
  );
}

function AccessStatusChart({ data, total }) {
  return (
    <div className="grid gap-5 px-4 pb-4 lg:grid-cols-[240px_1fr]">
      <div className="relative h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              innerRadius={52}
              label={renderPieLabel}
              labelLine={false}
              outerRadius={104}
              paddingAngle={0}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color || "#94a3b8"} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                borderRadius: 6,
                backgroundColor: "var(--color-card)",
                borderColor: "var(--color-border)",
                color: "var(--color-card-foreground)",
                fontSize: 12,
              }}
              wrapperStyle={{ zIndex: 20 }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-2xl font-bold leading-none text-foreground">
              {total}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Total</p>
          </div>
        </div>
      </div>
      <StatusLegend data={data} />
    </div>
  );
}

function StatusLegend({ data }) {
  return (
    <div className="overflow-hidden rounded border border-border bg-card">
      {data.map((item) => (
        <div
          key={item.name}
          className="grid grid-cols-[1fr_48px_64px] items-center gap-4 border-b border-border px-4 py-4 last:border-b-0"
        >
          <div className="flex items-center gap-3">
            <span
              className="size-3 rounded-full"
              style={{ backgroundColor: item.color || "#94a3b8" }}
            />
            <Link
              to={`/framework-categories?accessStatus=${item.name.toLowerCase()}`}
              className="text-sm font-medium hover:underline"
              style={{ color: item.color || "#64748b" }}
            >
              {item.name}
            </Link>
          </div>
          <span
            className="text-right text-sm font-semibold"
            style={{ color: item.color || "#64748b" }}
          >
            {item.value}
          </span>
          <span
            className="text-right text-sm font-semibold"
            style={{ color: item.color || "#64748b" }}
          >
            {item.percentage}
          </span>
        </div>
      ))}
    </div>
  );
}

function CodeBadge({ code }) {
  return (
    <span
      className={cn(
        "inline-flex rounded px-2.5 py-1 text-xs font-medium",
        getCodeBadgeClass(code)
      )}
    >
      {code}
    </span>
  );
}

function StatusBadge({ status }) {
  return (
    <span
      className={cn(
        "inline-flex rounded px-2.5 py-1 text-xs font-medium",
        getApprovalStatusColor(String(status || "").toLowerCase())
      )}
    >
      {status}
    </span>
  );
}

function UploadsTable({ rows }) {
  if (!rows.length) {
    return (
      <div className="px-4 py-10 text-center text-sm text-muted-foreground">
        No recent framework uploads found.
      </div>
    );
  }

  return (
    <Table className="table-fixed">
      <TableHeader className="bg-muted/60">
        <TableRow>
          <TableHead className="w-[34%] overflow-hidden text-foreground">
            Framework Name
          </TableHead>
          <TableHead className="w-[16%] overflow-hidden text-foreground">
            Version
          </TableHead>
          <TableHead className="w-[18%] overflow-hidden text-foreground">
            Uploaded By
          </TableHead>
          <TableHead className="w-[17%] overflow-hidden text-foreground">
            Upload Date
          </TableHead>
          <TableHead className="w-[15%] overflow-hidden text-foreground">
            Status
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={`${row.frameworkName}-${row.date}`}>
            <TableCell className="min-w-0 overflow-hidden font-medium text-foreground">
              <Link
                to={`/frameworks/${row.id}`}
                className="block truncate"
                title={row.frameworkName}
              >
                {row.frameworkName}
              </Link>
            </TableCell>
            <TableCell className="overflow-hidden">
              <CodeBadge code={row.frameworkVersion} />
            </TableCell>
            <TableCell className="min-w-0 overflow-hidden text-muted-foreground">
              <span className="block truncate" title={row.uploadedBy}>
                {row.uploadedBy}
              </span>
            </TableCell>
            <TableCell className="overflow-hidden text-muted-foreground">
              {row.date}
            </TableCell>
            <TableCell className="overflow-hidden">
              <StatusBadge status={row.status} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ApprovedFrameworksTable({ rows }) {
  if (!rows.length) {
    return (
      <div className="px-4 py-10 text-center text-sm text-muted-foreground">
        No approved frameworks found.
      </div>
    );
  }

  return (
    <Table className="table-fixed">
      <TableHeader className="bg-muted/60">
        <TableRow>
          <TableHead className="w-[34%] overflow-hidden text-foreground">
            Framework Name
          </TableHead>
          <TableHead className="w-[16%] overflow-hidden text-foreground">
            Version
          </TableHead>
          <TableHead className="w-[18%] overflow-hidden text-foreground">
            Approved By
          </TableHead>
          <TableHead className="w-[17%] overflow-hidden text-foreground">
            Approval Date
          </TableHead>
          <TableHead className="w-[15%] overflow-hidden text-foreground">
            Status
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={`${row.frameworkName}-${row.date}`}>
            <TableCell className="min-w-0 overflow-hidden font-medium text-foreground">
              <Link
                to={`/frameworks/${row.id}`}
                className="block truncate"
                title={row.frameworkName}
              >
                {row.frameworkName}
              </Link>
            </TableCell>
            <TableCell className="overflow-hidden">
              <CodeBadge code={row.frameworkVersion} />
            </TableCell>
            <TableCell className="min-w-0 overflow-hidden text-muted-foreground">
              <span className="block truncate" title={row.approvedBy}>
                {row.approvedBy}
              </span>
            </TableCell>
            <TableCell className="overflow-hidden text-muted-foreground">
              {row.date}
            </TableCell>
            <TableCell className="overflow-hidden">
              <StatusBadge status={row.status} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function TableCard({ title, actionLabel, actionPath, children }) {
  return (
    <CardShell title={title} actionLabel={actionLabel} actionPath={actionPath}>
      {children}
    </CardShell>
  );
}

export default function ExpertDashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const { datePreset, startDate, endDate, handleDateChange } = useDateFilter();

  const fetchDashboardData = useCallback(
    async (dateRange, isBackgroundRefresh = false) => {
      try {
        if (!isBackgroundRefresh) {
          setLoading(true);
        }
        setLoadError(null);
        const response = await getExpertDashboardAnalytics(dateRange);
        setDashboardData(response?.data || null);
      } catch (error) {
        console.error("Error fetching expert dashboard data:", error);
        if (!isBackgroundRefresh) {
          setLoadError(error.message || "Failed to load expert dashboard data");
        }
        setDashboardData(null);
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

  if (loading) {
    return <LoadingSpinner className="min-h-[calc(100vh-100px)]" />;
  }

  if (loadError || !dashboardData) {
    return (
      <DashboardError
        error={loadError}
        onRetry={() => fetchDashboardData({ startDate, endDate })}
      />
    );
  }

  const accessStatus = buildAccessStatusChartData(dashboardData.accessStatus);
  const statCards = buildStats(dashboardData.stats);
  const accessTotal = accessStatus.reduce(
    (sum, item) => sum + (item.value || 0),
    0
  );

  return (
    <div className="space-y-2 mt-2">
      <PageHeader
        datePreset={datePreset}
        startDate={startDate}
        endDate={endDate}
        handleDateChange={handleDateChange}
      />

      <div className="grid gap-2 lg:grid-cols-3">
        {statCards.map((stat) => (
          <StatCard key={stat.title} stat={stat} />
        ))}
      </div>

      <div className="grid gap-2 xl:grid-cols-2">
        <CardShell
          title="Framework Upload Trend"
          actionLabel="View Full Analytics"
          actionPath="/frameworks"
        >
          <div className="px-3 pb-4">
            <UploadTrendChart data={dashboardData.uploadTrend || []} />
          </div>
        </CardShell>

        <CardShell
          title="Framework Category Access Status"
          actionLabel="View Status Details"
          actionPath="/framework-categories"
        >
          <AccessStatusChart data={accessStatus} total={accessTotal} />
        </CardShell>
      </div>

      <div className="grid gap-2 xl:grid-cols-2">
        <TableCard
          title="Recent Framework Uploads"
          actionLabel="View All Uploads"
          actionPath="/frameworks"
        >
          <UploadsTable rows={dashboardData.recentUploads || []} />
        </TableCard>

        <TableCard
          title="Recently Approved Frameworks"
          actionLabel="View All Approved Frameworks"
          actionPath="/frameworks?approvalStatus=approved"
        >
          <ApprovedFrameworksTable
            rows={dashboardData.approvedFrameworks || []}
          />
        </TableCard>
      </div>
    </div>
  );
}
