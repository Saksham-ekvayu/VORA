import { useEffect, useState, useCallback } from "react";

import { CardContent, CardTitle } from "@/components/ui/card";
import CustomBadge from "@/components/custom/CustomBadge";
import { Button } from "@/components/ui/button";
import CardWrapper from "./components/CardWrapper";
import { getRoleLabel } from "@/utils/commonUtils";
import { useAuth } from "@/context/authContext/useAuth";
import DateFilter from "./components/DateFilter";
import { useDateFilter } from "./hooks/useDateFilter";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import Icon from "@/components/custom/Icon";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";
import UserMiniCard from "@/components/custom/UserMiniCard";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";

import DashboardError from "./components/DashboardError";
import { Skeleton } from "@/components/ui/skeleton";
import { getInternalExpertDashboardAnalytics } from "@/services/dashboardService";

function MetricCard({
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

export default function InternalExpertDashboard() {
  const { user } = useAuth();
  const [currentTime, setCurrentTime] = useState(new Date());

  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const { datePreset, startDate, endDate, handleDateChange } = useDateFilter();

  const fetchDashboardData = useCallback(async (filters = {}, background = false) => {
    if (!background) setIsLoading(true);
    setError(null);
    try {
      const response = await getInternalExpertDashboardAnalytics(filters);
      setDashboardData(response.data);
    } catch (err) {
      console.error("Error fetching internal expert dashboard analytics:", err);
      setError(err.response?.data?.message || "Failed to load dashboard data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData({ startDate, endDate }, dashboardData != null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDate, endDate, fetchDashboardData]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="space-y-3 my-2">
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
        <DashboardError
          error={error}
          onRetry={() => fetchDashboardData({ startDate, endDate })}
        />
      ) : (
        <>
          {/* Metrics */}
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <MetricCard
              icon="document"
              iconColor="text-primary"
              iconBg="bg-primary/10"
              borderColor="border-primary/40"
              title="Pending Review Framework"
              navigation="/pending-reviews"
            >
              {isLoading || !dashboardData ? (
                <Skeleton className="h-10 w-16 mt-1" />
              ) : (
                <p className="text-4xl font-bold text-primary group-hover:opacity-80 transition-opacity">
                  {dashboardData?.metrics?.pendingReview || 0}
                </p>
              )}
            </MetricCard>
            <MetricCard
              icon="history"
              iconColor="text-secondary"
              iconBg="bg-secondary/10"
              borderColor="border-secondary/40"
              title="In Review Framework"
              navigation="/in-review"
            >
              {isLoading || !dashboardData ? (
                <Skeleton className="h-10 w-16 mt-1" />
              ) : (
                <p className="text-4xl font-bold text-secondary group-hover:opacity-80 transition-opacity">
                  {dashboardData?.metrics?.inReview || 0}
                </p>
              )}
            </MetricCard>
            <MetricCard
              icon="check-circle"
              iconColor="text-green-500"
              iconBg="bg-green-500/10"
              borderColor="border-green-500/40"
              title="Approved Framework"
              navigation="/approved"
            >
              {isLoading || !dashboardData ? (
                <Skeleton className="h-10 w-16 mt-1" />
              ) : (
                <p className="text-4xl font-bold text-green-500 group-hover:opacity-80 transition-opacity">
                  {dashboardData?.metrics?.approved || 0}
                </p>
              )}
            </MetricCard>
            <MetricCard
              icon="back"
              iconColor="text-destructive"
              iconBg="bg-destructive/10"
              borderColor="border-destructive/40"
              title="Returned Framework"
              navigation="/returned"
            >
              {isLoading || !dashboardData ? (
                <Skeleton className="h-10 w-16 mt-1" />
              ) : (
                <p className="text-4xl font-bold text-destructive group-hover:opacity-80 transition-opacity">
                  {dashboardData?.metrics?.returned || 0}
                </p>
              )}
            </MetricCard>
          </div>

      <CardWrapper
        title={
          <div>
            <CardTitle className="text-lg">Review Requests</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Deployment frameworks requested by auditors for expert review.
            </p>
          </div>
        }
        right={
          <Button variant="link">
            <Link
              to="/deployment-frameworks"
              className="flex items-center gap-1"
            >
              View All
              <Icon name="chevron-right" size="16px" />
            </Link>
          </Button>
        }
      >
        <CardContent className="p-0">
          <table className="w-full min-w-275 text-sm">
            <thead>
              <tr className="border-b border-border/60 bg-muted/40 text-left text-xs font-medium text-muted-foreground">
                <th className="px-5 py-3">Deployment Framework</th>
                <th className="px-4 py-3">Package Version</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Health</th>
                <th className="px-4 py-3">Requested By</th>
                <th className="px-4 py-3">Requested At</th>
                <th className="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {isLoading || !dashboardData ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="px-5 py-4">
                      <Skeleton className="h-10 w-full" />
                    </td>
                    <td className="px-4 py-4">
                      <Skeleton className="h-4 w-16" />
                    </td>
                    <td className="px-4 py-4">
                      <Skeleton className="h-6 w-20" />
                    </td>
                    <td className="px-4 py-4">
                      <Skeleton className="h-6 w-12" />
                    </td>
                    <td className="px-4 py-4">
                      <Skeleton className="h-10 w-full" />
                    </td>
                    <td className="px-4 py-4">
                      <Skeleton className="h-4 w-24" />
                    </td>
                    <td className="px-5 py-4">
                      <Skeleton className="h-8 w-20 ml-auto" />
                    </td>
                  </tr>
                ))
              ) : dashboardData?.reviewRequests?.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="text-center py-8 text-muted-foreground"
                  >
                    No review requests found for the selected period.
                  </td>
                </tr>
              ) : (
                dashboardData?.reviewRequests?.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-border/50 last:border-0 hover:bg-muted/30"
                  >
                    <td className="px-5 py-3">
                      <FrameworkMiniCard
                        name={item.frameworkName}
                        description={item.frameworkVersion}
                        link={`/deployment-frameworks/${item.id}`}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium">{item.packageVersion}</div>
                    </td>
                    <td className="px-4 py-3">
                      <CustomBadge status={item.status} size="sm" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-lg font-semibold text-foreground">
                        {item.health}%
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <UserMiniCard
                        name={item.requestedBy.name}
                        email={item.requestedBy.email}
                        avatar={item.requestedBy.avatar}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium">
                        {formatDateWithMonthNameAndTime(item.requestedAt)}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Button size="xs">
                        <Link
                          to={`/deployment-frameworks/${item.id}/comparison-and-gap-analysis?package-version=${item.packageVersion}`}
                          className="flex items-center gap-1"
                        >
                          Review Now
                          <Icon name="chevron-right" size="16px" />
                        </Link>
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </CardWrapper>

      <div className="flex flex-col gap-5">
        <CardWrapper title="Review Process">
          <CardContent>
            <div className="flex flex-row gap-5 justify-between">
              {[
                [
                  "audit",
                  "1. Review Request",
                  "Auditor requests review for deployment framework.",
                  "bg-primary/10 text-primary",
                ],
                [
                  "analytics",
                  "2. Review & Analysis",
                  "Review deployment points, comparison & gap analysis.",
                  "bg-secondary/10 text-secondary",
                ],
                [
                  "message-square",
                  "3. Add Remark",
                  "Add review remark for each deployment point.",
                  "bg-orange-50 text-orange-600",
                ],
                [
                  "report",
                  "4. Approve / Return",
                  "Approve if acceptable or return for changes.",
                  "bg-amber-50 text-amber-600",
                ],
                [
                  "rocket",
                  "5. Next Steps",
                  "Auditor updates and resubmits or package gets approved.",
                  "bg-primary/10 text-primary",
                ],
              ].map(([iconName, title, text, tone], index) => (
                <div
                  key={title}
                  className="flex-1 relative flex gap-3 md:block group"
                >
                  <div
                    className={`relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${tone}`}
                  >
                    <Icon name={iconName} size="24px" />
                  </div>
                  <div className="mt-0 md:mt-3 relative z-10">
                    <p className="text-sm font-semibold">{title}</p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      {text}
                    </p>
                  </div>
                  {index < 4 && (
                    <div
                      className="hidden md:block absolute top-6 h-0.5 bg-border/80"
                      style={{ left: "56px", width: "calc(100% - 44px)" }}
                    />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </CardWrapper>
      </div>

      <div className="flex items-start justify-center gap-2 px-2 text-center text-xs text-muted-foreground">
        <Icon name="info" size="16px" className="mt-0.5 shrink-0" />
        <span>
          Health is calculated based on comparison and gap analysis of
          deployment points (implemented vs total required).
        </span>
      </div>
        </>
      )}
    </div>
  );
}
