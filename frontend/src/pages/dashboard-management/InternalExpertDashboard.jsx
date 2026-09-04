import { useEffect, useState } from "react";

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

const mockDashboardData = {
  metrics: {
    pendingReview: 7,
    inReview: 33,
    approved: 12345,
    returned: 543,
  },
  reviewRequests: [
    {
      id: "df-001",
      frameworkName: "Deployment Framework",
      frameworkVersion: "ISO27001:2022",
      packageVersion: "2.1.0",
      packageStatus: "In Review",
      requestedBy: {
        id: "auditor-001",
        name: "Auditor John",
        email: "auditor.john@acme.com",
        avatar: "https://randomuser.me/api/portraits/men/1.jpg",
      },
      requestedAt: "2026-08-26T06:22:46.553644+00:00",
      status: "In Review",
      health: 68,
    },
    {
      id: "df-002",
      frameworkName: "QMS Framework",
      frameworkVersion: "ISO9001:2015",
      packageVersion: "1.3.0",
      packageStatus: "Pending",
      requestedBy: {
        id: "auditor-002",
        name: "Auditor Sarah",
        email: "auditor.sarah@tech.com",
        avatar: "https://randomuser.me/api/portraits/women/1.jpg",
      },
      requestedAt: "2026-08-26T06:22:46.553644+00:00",
      status: "Pending",
      health: 82,
    },
    {
      id: "df-003",
      frameworkName: "Security Framework",
      frameworkVersion: "SOC 2 Type II",
      packageVersion: "3.0.0",
      packageStatus: "In Review",
      requestedBy: {
        id: "auditor-003",
        name: "Auditor Mike",
        email: "auditor.mike@datasec.com",
        avatar: "https://randomuser.me/api/portraits/men/2.jpg",
      },
      requestedAt: "2026-08-24T06:22:46.553644+00:00",
      status: "In Review",
      health: 55,
    },
    {
      id: "df-004",
      frameworkName: "Compliance Framework",
      frameworkVersion: "GDPR:2021",
      packageVersion: "1.0.0",
      packageStatus: "Pending",
      requestedBy: {
        id: "auditor-004",
        name: "Auditor Emma",
        email: "auditor.emma@globalsys.com",
        avatar: "https://randomuser.me/api/portraits/women/2.jpg",
      },
      requestedAt: "2026-08-23T06:22:46.553644+00:00",
      status: "Pending",
      health: 72,
    },
  ],
};

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

  const { datePreset, startDate, endDate, handleDateChange } = useDateFilter();

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

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
          <MetricCard
            icon="document"
            iconColor="text-primary"
            iconBg="bg-primary/10"
            borderColor="border-primary/40"
            title="Pending Review Framework"
            navigation="/pending-reviews"
          >
            <p className="text-4xl font-bold text-primary group-hover:opacity-80 transition-opacity">
              {mockDashboardData.metrics.pendingReview}
            </p>
          </MetricCard>
          <MetricCard
            icon="history"
            iconColor="text-secondary"
            iconBg="bg-secondary/10"
            borderColor="border-secondary/40"
            title="In Review Framework"
            navigation="/in-review"
          >
            <p className="text-4xl font-bold text-secondary group-hover:opacity-80 transition-opacity">
              {mockDashboardData.metrics.inReview}
            </p>
          </MetricCard>
          <MetricCard
            icon="check-circle"
            iconColor="text-green-500"
            iconBg="bg-green-500/10"
            borderColor="border-green-500/40"
            title="Approved Framework"
            navigation="/approved"
          >
            <p className="text-4xl font-bold text-green-500 group-hover:opacity-80 transition-opacity">
              {mockDashboardData.metrics.approved}
            </p>
          </MetricCard>
          <MetricCard
            icon="back"
            iconColor="text-destructive"
            iconBg="bg-destructive/10"
            borderColor="border-destructive/40"
            title="Returned Framework"
            navigation="/returned"
          >
            <p className="text-4xl font-bold text-destructive group-hover:opacity-80 transition-opacity">
              {mockDashboardData.metrics.returned}
            </p>
          </MetricCard>
        </div>
      </CardWrapper>

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
              {mockDashboardData.reviewRequests.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-border/50 last:border-0 hover:bg-muted/30"
                >
                  <td className="px-5">
                    <FrameworkMiniCard
                      name={item.frameworkName}
                      description={item.frameworkVersion}
                      link={`/deployment-frameworks/${item.id}`}
                    />
                  </td>
                  <td className="px-4">
                    <div className="font-medium">{item.packageVersion}</div>
                  </td>
                  <td className="px-4">
                    <CustomBadge status={item.status} size="sm" />
                  </td>
                  <td className="px-4">
                    <div className="text-lg font-semibold text-foreground">
                      {item.health}%
                    </div>
                  </td>
                  <td className="px-4">
                    <UserMiniCard
                      name={item.requestedBy.name}
                      email={item.requestedBy.email}
                      avatar={item.requestedBy.avatar}
                    />
                  </td>
                  <td className="px-4">
                    <div className="font-medium">
                      {formatDateWithMonthNameAndTime(item.requestedAt)}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right">
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
              ))}
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
          Overall Health is calculated based on comparison and gap analysis of
          deployment points.
        </span>
      </div>
    </div>
  );
}
