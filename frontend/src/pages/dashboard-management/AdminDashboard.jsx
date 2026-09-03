/* eslint-disable react/prop-types */

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import CardWrapper from "./components/CardWrapper";
import MetricCard from "./components/MetricCard";
import UserRegistrationChart from "@/pages/dashboard-management/components/charts/UserRegistrationChart";
import Icon from "@/components/custom/Icon";
import { getAdminDashboardAnalytics } from "@/services/dashboardService";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { Link } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/context/authContext/useAuth";
import { getRoleLabel, ROLE_EXPERT } from "@/utils/commonUtils";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import DateFilter from "./components/DateFilter";
import { useDateFilter } from "./hooks/useDateFilter";
import CustomBadge from "@/components/custom/CustomBadge";
import DashboardError from "./components/DashboardError";

export default function AdminDashboard() {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  const { datePreset, startDate, endDate, handleDateChange } = useDateFilter();

  const fetchDashboardData = useCallback(
    async (dateRange, isBackgroundRefresh = false) => {
      try {
        if (!isBackgroundRefresh) {
          setLoading(true);
        }
        setLoadError(null);
        const response = await getAdminDashboardAnalytics(dateRange);
        if (response?.data) {
          setDashboardData(response.data);
        } else if (response?.message) {
          setLoadError(response.message);
        }
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
        setLoadError(error.message || "Failed to load dashboard data");
        if (!isBackgroundRefresh) {
          toast.error(error.message || "Failed to load dashboard data");
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
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  if (loading) {
    return <LoadingSpinner className={"min-h-[calc(100vh-100px)]"} />;
  }

  if (loadError || !dashboardData) {
    return (
      <DashboardError
        error={loadError}
        onRetry={() => fetchDashboardData({ startDate, endDate })}
      />
    );
  }

  const { stats, charts, recentCreatedUsers } = dashboardData;

  const metrics = [
    {
      label: "TOTAL EXPERTS",
      value: stats.usersByRole[ROLE_EXPERT] || 0,
      iconColor: "text-blue-500",
      iconBg: "bg-blue-500/10",
      borderColor: "border-blue-500/40",
      icon: "user-check",
      path: `/profiles?role=${ROLE_EXPERT}`,
    },
    {
      label: "TOTAL EXPERT FRAMEWORK ACCESS",
      value: stats.totalApprovedFrameworkAccess || 0,
      iconColor: "text-emerald-500",
      iconBg: "bg-emerald-500/10",
      borderColor: "border-emerald-500/40",
      icon: "vpn-key",
      path: "/framework-access",
    },
    {
      label: "TOTAL CUSTOMERS",
      value: stats.totalCustomers || 0,
      iconColor: "text-indigo-500",
      iconBg: "bg-indigo-500/10",
      borderColor: "border-indigo-500/40",
      icon: "building",
      path: "/customers",
    },
    {
      label: "TOTAL CUSTOMER ASSIGNED FRAMEWORKS",
      value: stats.totalAssignedFrameworks || 0,
      iconColor: "text-amber-500",
      iconBg: "bg-amber-500/10",
      borderColor: "border-amber-500/40",
      icon: "assignment",
      path: "/framework-assignments",
    },
    {
      label: "TOTAL FRAMEWORK CATEGORIES",
      value: stats.totalFrameworkCategories || 0,
      iconColor: "text-orange-500",
      iconBg: "bg-orange-500/10",
      borderColor: "border-orange-500/40",
      icon: "category",
      path: "/framework-categories",
    },
    {
      label: "TOTAL FRAMEWORKS",
      value: stats.totalFrameworks || 0,
      iconColor: "text-purple-500",
      iconBg: "bg-purple-500/10",
      borderColor: "border-purple-500/40",
      icon: "framework",
      path: "/frameworks",
    },
    {
      label: "TOTAL DEPLOYMENT FRAMEWORKS",
      value: stats.totalDeploymentFrameworks || 0,
      iconColor: "text-cyan-500",
      iconBg: "bg-cyan-500/10",
      borderColor: "border-cyan-500/40",
      icon: "cloud-upload",
      path: "/deployment-frameworks",
    },
    {
      label: "TOTAL DEPLOYMENT DOCUMENTS",
      value: stats.totalDeploymentDocuments || 0,
      iconColor: "text-pink-500",
      iconBg: "bg-pink-500/10",
      borderColor: "border-pink-500/40",
      icon: "document",
      path: "/deployment-documents",
    },
  ];

  return (
    <div className="space-y-3 my-2">
      {/* Metrics */}
      <CardWrapper
        title={
          <>
            Welcome, {user?.name}
            <span className="text-sm ml-1">
              ({user?.role && getRoleLabel(user.role)})
            </span>{" "}
            👋
          </>
        }
        right={
          <div className="flex items-center gap-4">
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
        }
      >
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {metrics.map((m) => (
            <MetricCard
              key={m.label}
              {...m}
              icon={<Icon name={m.icon} size="24px" />}
              path={m.path}
            />
          ))}
        </div>
      </CardWrapper>

      {/* User Analytics */}
      <div className="grid xl:grid-cols-2 gap-3 items-stretch">
        {/* Recent Users */}
        <CardWrapper
          title="Recently Created Profiles"
          right={
            <Link
              to={"/profiles"}
              className="text-primary cursor-pointer flex items-center gap-1"
            >
              View All <Icon name="arrow-right" size="14px" />
            </Link>
          }
          className="flex flex-col"
        >
          <div className="space-y-1.5 flex-1 flex flex-col -m-2">
            {recentCreatedUsers.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-8">
                <Icon
                  name="users"
                  size="48px"
                  className="text-muted-foreground mb-4 mx-auto"
                />
                <p className="text-muted-foreground text-center">
                  No recent users
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead className="text-right">Created At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentCreatedUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <Link
                          to={`/profiles/${user.id}`}
                          className="hover:underline text-xs"
                        >
                          {user.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Link
                          to={`/profiles/${user.id}`}
                          className="hover:underline text-xs"
                        >
                          {user.email}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <CustomBadge size="xs" role={user.role} />
                      </TableCell>
                      <TableCell className="text-right text-xs whitespace-nowrap">
                        {formatDateWithMonthNameAndTime(user.createdAt)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </CardWrapper>
        {/* User Registration Chart */}
        <CardWrapper
          title="Profile Registration Trends"
          className="flex flex-col"
        >
          <UserRegistrationChart data={charts.userCreation} />
        </CardWrapper>
      </div>
    </div>
  );
}
