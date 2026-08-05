/* eslint-disable react/prop-types */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import Icon from "@/components/custom/Icon";
import CardWrapper from "../CardWrapper";
import { Link } from "react-router-dom";

const MUTED_COLOR = "var(--muted-foreground)";
const ACCENT_COLOR = "var(--accent)";
const BORDER_COLOR = "var(--border)";

// Custom Tooltip for Upload Frequency Bar Chart
const FrequencyTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div className="bg-background border border-border rounded p-2.5 shadow-lg text-xs">
        <p className="font-semibold text-foreground mb-1">{label}</p>
        <p className="text-blue-500">Uploads: {payload[0]?.value}</p>
      </div>
    );
  }
  return null;
};

// Custom Tooltip for Access Status Radial Chart
const AccessTooltip = ({ active, payload }) => {
  if (active && payload?.length) {
    return (
      <div className="bg-background border border-border rounded p-2.5 shadow-lg text-xs">
        <p className="font-semibold text-foreground">
          {payload[0]?.payload?.name}
        </p>
        <p style={{ color: payload[0]?.payload?.fill }}>
          Count: {payload[0]?.value}
        </p>
      </div>
    );
  }
  return null;
};

export default function UploadAnalyticsChart({ stats }) {
  // Bar chart data for upload frequency
  const frequencyData = Array.isArray(stats.uploadFrequency)
    ? stats.uploadFrequency.map((item) => ({
        month: item.month,
        uploads: item.count,
      }))
    : [
        {
          month: "Last Month",
          uploads: stats.uploadFrequency.lastMonth || 0,
        },
        {
          month: "This Month",
          uploads: stats.uploadFrequency.thisMonth || 0,
        },
      ];

  // Access status data for radial/bar chart
  const accessStatusData = [
    { name: "Approved", value: stats.approvedAccess, fill: "var(--primary)" },
    { name: "Pending", value: stats.pendingRequests, fill: "var(--warning)" },
    {
      name: "Rejected",
      value: stats.rejectedAccess,
      fill: "var(--destructive)",
    },
    {
      name: "Revoked",
      value: stats.revokedAccess,
      fill: MUTED_COLOR,
    },
  ];

  return (
    <CardWrapper title="Framework Upload Analytics" className="flex flex-col">
      <div className="space-y-4 flex-1">
        {/* Upload Frequency Bar Chart */}
        <div className="p-3 bg-accent rounded border border-border">
          <h4 className="font-semibold text-sm flex items-center gap-2 border-b border-border pb-2">
            <Icon name="calendar" size="16px" className="text-blue-500" />
            Upload Frequency
          </h4>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart
              data={frequencyData}
              margin={{ top: 8, right: 8, left: -20, bottom: -13 }}
              barSize={100}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={BORDER_COLOR}
                vertical={false}
              />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 11, fill: MUTED_COLOR }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: MUTED_COLOR }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                content={<FrequencyTooltip />}
                cursor={{ fill: ACCENT_COLOR }}
              />
              <Bar dataKey="uploads" radius={[4, 4, 0, 0]}>
                {frequencyData.map((entry, index) => (
                  <Cell
                    key={entry.month}
                    fill={index === 1 ? "var(--primary)" : "var(--secondary)"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Access Summary + Framework Access Status - Combined Bar Chart */}
        <div className="p-3 bg-accent rounded border border-border">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <h4 className="font-semibold text-sm flex items-center gap-2">
              <Icon name="key" size="16px" className="text-blue-500" />
              Framework Access Status
            </h4>
            <Link
              to="/framework-categories"
              className="text-primary cursor-pointer flex items-center gap-1 text-xs"
            >
              View All <Icon name="arrow-right" size="14px" />
            </Link>
          </div>
          <ResponsiveContainer width="100%" height={130}>
            <BarChart
              data={accessStatusData}
              layout="vertical"
              margin={{ top: 5, right: 24, left: 4, bottom: -13 }}
              barSize={14}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={BORDER_COLOR}
                horizontal={false}
              />
              <XAxis
                type="number"
                tick={{ fontSize: 10, fill: MUTED_COLOR }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11, fill: MUTED_COLOR }}
                axisLine={false}
                tickLine={false}
                width={58}
              />
              <Tooltip
                content={<AccessTooltip />}
                cursor={{ fill: ACCENT_COLOR }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {accessStatusData.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Access Summary totals below chart */}
          <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-border">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-green-500 shrink-0" />
              <span className="text-xs text-muted-foreground">
                Accessible:{" "}
                <span className="font-semibold text-foreground">
                  {stats.totalCategories - stats.inaccessibleCategories}
                </span>
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 shrink-0" />
              <span className="text-xs text-muted-foreground">
                Restricted:{" "}
                <span className="font-semibold text-foreground">
                  {stats.inaccessibleCategories}
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </CardWrapper>
  );
}
