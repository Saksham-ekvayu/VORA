/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import CardWrapper from "./components/CardWrapper";
import ProgressBar from "../../components/custom/ProgressBar";
import Icon from "@/components/custom/Icon";
import { useDateFilter } from "./hooks/useDateFilter";
import { useAuth } from "@/context/authContext/useAuth";
import { getRoleLabel } from "@/utils/commonUtils";
import DateFilter from "./components/DateFilter";
import { getAuditorDashboardAnalytics } from "@/services/dashboardService";
import { formatDateOnly } from "@/utils/dateFormatter";
import { Skeleton } from "@/components/ui/skeleton";

// ─── Dynamic Frontend Configuration ──────────────────────────────────────────
const COLORS = [
  { tagColor: "#3b82f6", barColor: "bg-blue-500" },
  { tagColor: "#22c55e", barColor: "bg-green-500" },
  { tagColor: "#8b5cf6", barColor: "bg-violet-500" },
  { tagColor: "#ef4444", barColor: "bg-red-500" },
  { tagColor: "#f59e0b", barColor: "bg-amber-500" },
  { tagColor: "#06b6d4", barColor: "bg-cyan-500" },
  { tagColor: "#ec4899", barColor: "bg-pink-500" },
  { tagColor: "#14b8a6", barColor: "bg-teal-500" },
];

const getHashIndex = (str, max) => {
  if (!str) return 0;
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.codePointAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % max;
};

const DASHBOARD_CONFIG = {
  getFrameworkConfig: (name) => COLORS[getHashIndex(name, COLORS.length)],
};

// ─── Small reusable pieces ───────────────────────────────────────────────────

function getStreamDotColor(status) {
  if (status === "pass") return "bg-emerald-500";
  if (status === "warn") return "bg-amber-500";
  return "bg-red-500";
}

function getStreamTextColor(status) {
  if (status === "pass") return "text-emerald-500";
  if (status === "warn") return "text-amber-500";
  return "text-red-500";
}

function TopStatCard({
  icon,
  iconColor = "text-primary",
  iconBg = "bg-primary/10",
  borderColor = "border-primary/40",
  title,
  navigation,
  children,
}) {
  return (
    <Link
      to={navigation}
      className="rounded border border-border bg-linear-to-br from-background to-card p-2.5 flex justify-between shadow-lg hover:shadow-xl transition-shadow duration-300 hover:border-primary/50 cursor-pointer"
    >
      <div className="flex flex-col gap-2 w-full">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </p>
        <div className="">{children}</div>
      </div>
      <span
        className={cn(
          "w-12 h-12 rounded shrink-0 flex items-center justify-center transition-transform duration-300 group-hover:scale-105 border",
          borderColor,
          iconBg,
          iconColor
        )}
      >
        <Icon name={icon} size="24px" />
      </span>
    </Link>
  );
}

function PriorityBadge({ priority }) {
  const map = {
    High: "bg-red-100   text-red-700   dark:bg-red-900/30   dark:text-red-400",
    Medium:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    Low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  };
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${map[priority] ?? "bg-muted text-muted-foreground"}`}
    >
      {priority}
    </span>
  );
}

function EmptyState({ message = "No data available", icon = "inbox" }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-muted-foreground py-8 gap-2 text-center">
      <Icon name={icon} size="24px" className="opacity-50" />
      <span className="text-xs">{message}</span>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function AuditorDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [currentTime, setCurrentTime] = useState(new Date());
  const { datePreset, startDate, endDate, handleDateChange } = useDateFilter();
  const [dashboardData, setDashboardData] = useState();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await getAuditorDashboardAnalytics({ startDate, endDate });
        if (res?.success === false) {
          setError(res?.message || "Failed to fetch analytics");
        } else {
          setDashboardData(res.data);
        }
      } catch (err) {
        console.error("Failed to fetch auditor analytics", err);
        setError(err?.message || "Failed to fetch analytics");
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [startDate, endDate]);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <div className="space-y-3 mt-2">
      {/* ── Header bar ────────────────────────────────────────────────────── */}
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

      {error ? (
        <div className="bg-red-500/10 border border-red-500/20 text-red-600 rounded-md p-6 my-4 flex flex-col items-center justify-center gap-2">
          <Icon name="triangle-alert" size="32px" />
          <span className="font-medium text-lg">{error}</span>
          <p className="text-sm opacity-80">
            Please try refreshing the page or checking your backend logs.
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {/* Overall Protection */}
            <TopStatCard
              title="Overall Protection"
              icon="shield"
              iconColor="text-primary"
              navigation="/dashboard/overall-protection"
            >
              {isLoading || !dashboardData ? (
                <Skeleton className="h-10 w-24 mt-1" />
              ) : (
                <p className="text-4xl font-bold text-primary group-hover:opacity-80 transition-opacity">
                  {dashboardData?.overallProtection || 0}%
                </p>
              )}
            </TopStatCard>

            {/* Critical Gaps */}
            <TopStatCard
              title="Critical Gaps"
              icon="warning"
              iconColor="text-red-500"
              iconBg="bg-red-500/10"
              borderColor="border-red-500/40"
              navigation="/dashboard/critical-gaps"
            >
              {isLoading || !dashboardData ? (
                <Skeleton className="h-10 w-24 mt-1" />
              ) : (
                <p className="text-4xl font-bold text-red-500 group-hover:opacity-80 transition-opacity">
                  {dashboardData?.criticalGaps || 0}
                </p>
              )}
            </TopStatCard>

            {/* Control Passing */}
            <TopStatCard
              title="Control Passing"
              icon="check-circle"
              iconColor="text-emerald-500"
              iconBg="bg-emerald-500/10"
              borderColor="border-emerald-500/40"
              navigation="/dashboard/controls-passing"
            >
              {isLoading || !dashboardData ? (
                <Skeleton className="h-10 w-24 mt-1" />
              ) : (
                <p className="text-4xl font-bold text-emerald-500 group-hover:opacity-80 transition-opacity">
                  {dashboardData?.controlPassing || 0}
                </p>
              )}
            </TopStatCard>

            {/* Extra Controls */}
            <TopStatCard
              title="Extra Controls"
              icon="star"
              iconColor="text-secondary"
              iconBg="bg-secondary/10"
              borderColor="border-secondary/40"
              navigation="/dashboard/extra-controls"
            >
              {isLoading || !dashboardData ? (
                <Skeleton className="h-10 w-24 mt-1" />
              ) : (
                <p className="text-4xl font-bold text-secondary group-hover:opacity-80 transition-opacity">
                  {dashboardData?.extraControls || 0}
                </p>
              )}
            </TopStatCard>
          </div>

          {/* ── Row 2: Framework Health | Active Gaps | Live Audit ────────────── */}
          <div className="grid xl:grid-cols-3 gap-3 items-stretch">
            {/* Framework Health */}
            <CardWrapper title="Framework Health" className="flex flex-col">
              <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border-b border-border pb-1.5 shrink-0">
                <span>Framework</span>
                <span>IMPLEMENTED / TOTAL POINTS</span>
              </div>

              <div
                className="overflow-y-auto flex-1 pr-0.5"
                style={{ maxHeight: "220px" }}
              >
                {(isLoading || !dashboardData) &&
                  Array.from({ length: 3 }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 w-full group py-1.5 border-b border-border last:border-0"
                    >
                      <Skeleton className="h-5 w-24 shrink-0" />
                      <Skeleton className="h-4 flex-1 rounded-full" />
                      <Skeleton className="h-4 w-8 shrink-0" />
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData?.frameworkHealth?.length > 0 &&
                  dashboardData?.frameworkHealth?.map((fw) => (
                    <Link
                      to={`/dashboard/framework/${fw.id}`}
                      key={`${fw.name}-${fw.version}`}
                      className="flex items-center gap-3 w-full group cursor-pointer py-1.5 border-b border-border last:border-0"
                    >
                      <span
                        className="text-[11px] font-semibold px-1 py-0.3 rounded text-white shrink-0 min-w-24 text-center group-hover:opacity-80 transition-opacity"
                        style={{
                          backgroundColor: DASHBOARD_CONFIG.getFrameworkConfig(
                            fw.version
                          ).tagColor,
                        }}
                      >
                        {fw.version || fw.name}
                      </span>
                      <div className="flex-1">
                        <ProgressBar
                          value={fw.readiness}
                          color={
                            DASHBOARD_CONFIG.getFrameworkConfig(fw.version)
                              .barColor
                          }
                        />
                      </div>
                      <span className="text-xs font-bold text-foreground w-9 text-right shrink-0 group-hover:text-primary transition-colors">
                        {fw.readiness}%
                      </span>
                      <span className="text-xs ">({fw.implemented_dps}/{fw.total_dps})</span>
                    </Link>
                  ))}

                {!isLoading &&
                  dashboardData &&
                  dashboardData?.frameworkHealth?.length <= 0 && (
                    <EmptyState message="No framework data available" />
                  )}
              </div>
            </CardWrapper>

            {/* Deployment Points */}
            <CardWrapper
              title="Deployment Points"
              right={
                <button
                  type="button"
                  onClick={() => navigate("/dashboard/deployment-points")}
                  className="text-primary flex items-center gap-1 text-xs hover:underline cursor-pointer"
                >
                  View All <Icon name="arrow-right" size="14px" />
                </button>
              }
              className="flex flex-col"
            >
              {/* Column headers */}
              <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border-b border-border pb-1.5 mb-2 shrink-0">
                <span>Framework</span>
                <span>TOTAL POINTS</span>
              </div>
              <div
                className="overflow-y-auto flex-1 space-y-4 pr-0.5"
                style={{ maxHeight: "220px" }}
              >
                {(isLoading || !dashboardData) &&
                  Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 w-full py-1"
                    >
                      <Skeleton className="h-5 w-24 shrink-0" />
                      <Skeleton className="h-4 flex-1 rounded-full" />
                      <Skeleton className="h-4 w-8 shrink-0" />
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData?.deploymentPoints?.length > 0 &&
                  dashboardData?.deploymentPoints?.map((dp) => (
                    <div
                      key={`${dp.name}-${dp.version}`}
                      className="flex items-center gap-3 w-full group"
                    >
                      {/* Colored pill tag */}
                      <span
                        className="text-[11px] font-semibold px-1 py-0.3 rounded text-white shrink-0 min-w-24 text-center group-hover:opacity-80 transition-opacity"
                        style={{
                          backgroundColor: DASHBOARD_CONFIG.getFrameworkConfig(
                            dp.version
                          ).tagColor,
                        }}
                      >
                        {dp.version || dp.name}
                      </span>
                      {/* Bar chart */}
                      <div className="flex-1">
                        <ProgressBar
                          value={Math.max(
                            (dp.count /
                              Math.max(
                                ...(dashboardData?.deploymentPoints?.map(
                                  (d) => d.count
                                ) || [1])
                              )) *
                              100,
                            5
                          )}
                          color={
                            DASHBOARD_CONFIG.getFrameworkConfig(dp.version)
                              .barColor
                          }
                        />
                      </div>
                      {/* Count */}
                      <span className="text-xs font-bold text-foreground w-9 text-right shrink-0 group-hover:text-primary transition-colors">
                        {dp.count}
                      </span>
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData &&
                  dashboardData?.deploymentPoints?.length <= 0 && (
                    <EmptyState message="No deployment points found" />
                  )}
              </div>
            </CardWrapper>

            {/* Active Gaps */}
            <CardWrapper
              title="Active Gaps"
              right={
                <button
                  type="button"
                  onClick={() => navigate("/deployment-frameworks")}
                  className="text-primary flex items-center gap-1 text-xs hover:underline cursor-pointer"
                >
                  View All <Icon name="arrow-right" size="14px" />
                </button>
              }
              className="flex flex-col"
            >
              {/* Table header */}
              <div className="grid grid-cols-[0.3fr_1.2fr_0.8fr_0.5fr_0.7fr_1fr] text-[10px] font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1.5 gap-1">
                <span>SL.</span>
                <span>Framework</span>
                <span className="text-center">Ctrl No.</span>
                <span className="text-center">Inst.</span>
                <span className="text-center">% Failing</span>
                <span className="text-right">Last NC Date</span>
              </div>
              <div
                className="flex-1 mt-1 overflow-y-auto"
                style={{ maxHeight: "220px" }}
              >
                {(isLoading || !dashboardData) &&
                  Array.from({ length: 5 }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between py-2.5 border-b border-border"
                    >
                      <Skeleton className="h-4 w-4 shrink-0" />
                      <Skeleton className="h-4 w-24 shrink-0 ml-2" />
                      <Skeleton className="h-4 w-16 shrink-0 ml-2" />
                      <Skeleton className="h-4 w-12 shrink-0 ml-2" />
                      <Skeleton className="h-4 w-16 shrink-0 ml-2" />
                      <Skeleton className="h-4 w-20 shrink-0 ml-2" />
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData?.activeGaps?.length > 0 &&
                  dashboardData?.activeGaps?.map((gap, idx) => (
                    <div
                      key={`${gap.id}-${idx}`}
                      className="grid grid-cols-[0.3fr_1.2fr_0.8fr_0.5fr_0.7fr_1fr] gap-1 items-center py-2 border-b border-border last:border-0 hover:bg-accent/50 rounded transition-colors px-0.5"
                    >
                      <span className="text-xs text-muted-foreground">
                        {idx + 1}
                      </span>
                      <Link
                        to={`/deployment-frameworks/${gap.frameworkId}/comparison-and-gap-analysis?package-version=${gap.packageVersion}&tab=gap-analysis`}
                        className="text-xs font-semibold text-primary truncate hover:underline"
                      >
                        {gap.version || gap.framework}
                      </Link>
                      <span className="text-xs text-secondary font-semibold text-center">
                        {gap.id}
                      </span>
                      <span className="text-xs text-center text-foreground font-medium">
                        {gap.instances}
                      </span>
                      <div className="flex items-center justify-center gap-1">
                        <Icon
                          name={gap.trend === "up" ? "arrow-up" : "arrow-down"}
                          size="12px"
                          className={
                            gap.trend === "up"
                              ? "text-emerald-500"
                              : "text-red-500"
                          }
                        />
                        <span
                          className={`text-xs font-bold ${gap.trend === "up" ? "text-emerald-500" : "text-red-500"}`}
                        >
                          {gap.failing}
                        </span>
                      </div>
                      <span className="text-xs text-right text-muted-foreground">
                        {formatDateOnly(gap.lastNC)}
                      </span>
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData &&
                  dashboardData?.activeGaps?.length <= 0 && (
                    <EmptyState message="No active gaps reported" />
                  )}
              </div>
            </CardWrapper>

            {/* Live Audit Streams */}
            <CardWrapper
              title="Live Audit Streams"
              right={
                <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-500">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>24x7 Active</span>
                </span>
              }
              className="flex flex-col xl:col-span-2"
            >
              <div
                className="overflow-y-auto flex-1 pr-0.5"
                style={{ maxHeight: "300px" }}
              >
                {(isLoading || !dashboardData) &&
                  Array.from({ length: 6 }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 py-2.5 border-b border-border last:border-0"
                    >
                      <Skeleton className="w-2.5 h-2.5 rounded-full shrink-0" />
                      <Skeleton className="h-4 w-8 shrink-0" />
                      <Skeleton className="h-4 w-12 shrink-0" />
                      <div className="flex flex-col flex-1 gap-1.5">
                        <Skeleton className="h-3 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                      </div>
                      <Skeleton className="h-4 w-16 shrink-0" />
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData?.liveAuditStreams?.length > 0 &&
                  dashboardData?.liveAuditStreams?.map((stream, index) => (
                    <div
                      key={`${stream.id}-${index}`}
                      className="flex items-center gap-3 py-1 border-b border-border last:border-0"
                    >
                      <span
                        className={`w-2.5 h-2.5 rounded-full shrink-0 ${getStreamDotColor(stream.status)}`}
                      />
                      <span
                        className={`text-[13px] font-semibold shrink-0 w-9 capitalize ${getStreamTextColor(stream.status)}`}
                      >
                        {stream.status}
                      </span>
                      <span className="text-[11px] text-primary font-semibold">
                        {stream.version}
                      </span>
                      <div className="flex flex-col flex-1">
                        <span className="text-[13px] text-foreground flex-1">
                          DP: {stream.description}
                        </span>
                        <span className="text-[11px] text-muted-foreground flex-1">
                          Reason: {stream.reason}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {formatDateOnly(stream.timestamp)}
                      </span>
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData &&
                  dashboardData?.liveAuditStreams?.length <= 0 && (
                    <EmptyState message="No live audit streams active" />
                  )}
              </div>
            </CardWrapper>

            {/* AI Insights */}
            <CardWrapper
              title="AI Insights"
              right={
                <p className="text-xs text-muted-foreground">
                  Recommended actions to bridge critical gaps
                </p>
              }
              className="flex flex-col"
            >
              <div
                className="overflow-y-auto flex-1 pr-0.5"
                style={{ maxHeight: "300px" }}
              >
                {(isLoading || !dashboardData) &&
                  Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 py-1.5 border-b border-border last:border-0"
                    >
                      <div className="flex-1 space-y-1.5">
                        <Skeleton className="h-3.5 w-full" />
                        <Skeleton className="h-3.5 w-4/5" />
                      </div>
                      <Skeleton className="h-5 w-16 shrink-0 mt-0.5 rounded-full" />
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData?.aiInsights?.length > 0 &&
                  dashboardData?.aiInsights?.map((insight, idx) => (
                    <div
                      key={`${insight.text}-${idx}`}
                      className="flex items-start gap-3 py-1.5 border-b border-border last:border-0"
                    >
                      <p className="text-xs text-foreground flex-1 leading-relaxed">
                        {insight.text}
                      </p>
                      <div className="flex items-center gap-2 shrink-0 mt-0.5">
                        <PriorityBadge priority={insight.priority} />
                      </div>
                    </div>
                  ))}

                {!isLoading &&
                  dashboardData &&
                  dashboardData?.aiInsights?.length <= 0 && (
                    <EmptyState message="No AI insights generated yet" />
                  )}
              </div>
            </CardWrapper>
          </div>
        </>
      )}
    </div>
  );
}
