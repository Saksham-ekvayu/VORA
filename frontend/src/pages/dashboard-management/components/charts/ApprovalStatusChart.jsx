/* eslint-disable react/prop-types */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import Icon from "@/components/custom/Icon";

function CustomTooltip({ active, payload }) {
  if (!(active && payload?.length)) {
    return null;
  }

  return (
    <div className="bg-background border border-border rounded p-2 shadow-lg text-xs">
      <p className="font-semibold text-foreground">{payload[0].name}</p>

      <p className="font-medium" style={{ color: payload[0].payload.color }}>
        Count: {payload[0].value}
      </p>
    </div>
  );
}

const ApprovalStatusChart = ({ stats }) => {
  // Transform backend stats into Recharts format
  const approvalChartData = stats?.approvalDistribution
    ? [
        {
          name: "Approved",
          count: stats.approvalDistribution.approved,
          color: "var(--primary)",
        },
        {
          name: "Pending",
          count: stats.approvalDistribution.pending,
          color: "var(--warning)",
        },
      ]
    : [];

  return (
    <div className="p-3 bg-accent rounded border border-border">
      <h4 className="font-semibold text-sm pb-2 flex items-center gap-2 border-b border-border">
        <Icon name="check-circle" size="16px" className="text-blue-500" />
        Framework Approval Statistics
      </h4>
      <div className="h-40 pt-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={approvalChartData}
            margin={{ top: 5, right: 5, left: -30, bottom: -12 }}
            barSize={100}
          >
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {approvalChartData.map((entry) => (
                <Cell key={`cell-${entry.color}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ApprovalStatusChart;
