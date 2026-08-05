/* eslint-disable react/prop-types */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useTheme } from "@/context/ThemeContext";

// Custom tooltip component
const CustomTooltip = ({ active, payload, label, colors }) => {
  if (active && payload?.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-background/95 backdrop-blur-sm border border-border rounded shadow-xl p-2.5 min-w-32">
        <p className="font-semibold text-foreground text-xs mb-1.5">{label}</p>
        <div className="space-y-0.5">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-medium text-foreground">
              Total Profiles Created
            </span>
            <span
              className="font-bold text-xs"
              style={{ color: colors.primary }}
            >
              {data.total}
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

// Custom legend component
const CustomLegend = ({ payload }) => {
  return (
    <div className="flex items-center justify-center gap-6 mb-4">
      <div className="flex items-center gap-2">
        <div
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: payload[0]?.color }}
        />
        <span className="text-sm font-medium text-foreground">
          Total Profiles Created
        </span>
      </div>
    </div>
  );
};

const getThemeColors = (isDark) => ({
  primary: "oklch(0.6 0.14 190)",
  grid: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)",
  text: isDark ? "#d1d5db" : "#6b7280",
  background: isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.02)",
  border: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)",
});

const transformChartData = (data) => {
  return data.labels.map((date, index) => ({
    date: new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "2-digit",
    }),
    fullDate: date,
    total: data.total[index],
  }));
};

const UserRegistrationChart = ({ data }) => {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  const chartData = transformChartData(data);

  // If date range is large, filter out dates with 0 registrations to make chart cleaner
  // We keep the first and last dates to preserve the visual timeline bounds
  let displayData = chartData;
  if (chartData.length > 31) {
    displayData = chartData.filter(
      (item, index) =>
        item.total > 0 || index === 0 || index === chartData.length - 1
    );
  }

  const colors = getThemeColors(isDark);

  // Calculate totals for summary
  const grandTotal = data.total.reduce((a, b) => a + b, 0);

  return (
    <ResponsiveContainer width="100%" height={310} minWidth={0} minHeight={0}>
      <AreaChart
        data={displayData}
        margin={{
          top: 20,
          right: 30,
          left: -40,
          bottom: -15,
        }}
      >
        <defs>
          <linearGradient id="totalGradient" x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="5%"
              stopColor={colors.primary}
              stopOpacity={isDark ? 0.4 : 0.3}
            />
            <stop
              offset="95%"
              stopColor={colors.primary}
              stopOpacity={isDark ? 0.1 : 0.05}
            />
          </linearGradient>
        </defs>

        <CartesianGrid
          strokeDasharray="3 3"
          stroke={colors.grid}
          opacity={0.6}
        />

        <XAxis
          dataKey="date"
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 12, fill: colors.text }}
          dy={10}
        />

        <YAxis
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 12, fill: colors.text }}
          domain={[0, "dataMax + 1"]}
          allowDecimals={false}
        />

        <Tooltip content={<CustomTooltip colors={colors} />} />

        <Legend content={<CustomLegend />} />

        {/* Reference line for average */}
        <ReferenceLine
          y={grandTotal / data.labels.length}
          stroke={colors.text}
          strokeDasharray="5 5"
          opacity={0.7}
          label={{
            value: "Avg",
            position: "insideTopRight",
            style: { fill: colors.text, fontSize: "12px" },
          }}
        />

        <Area
          type="monotone"
          dataKey="total"
          stroke={colors.primary}
          strokeWidth={2}
          fill="url(#totalGradient)"
          dot={{ fill: colors.primary, strokeWidth: 2, r: 4 }}
          activeDot={{
            r: 6,
            stroke: colors.primary,
            strokeWidth: 2,
            fill: isDark ? "#1f2937" : "#ffffff",
            filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.2))",
          }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default UserRegistrationChart;
