/* eslint-disable react/prop-types */

import { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import Icon from "@/components/custom/Icon";
import CardWrapper from "../CardWrapper";

const FILE_TYPE_COLORS = {
  PDF: "var(--destructive)",
  DOCX: "var(--secondary)",
  XLSX: "var(--primary)",
};

// Custom Tooltip for Pie Chart
const PieTooltip = ({ active, payload }) => {
  if (active && payload?.length) {
    return (
      <div className="bg-background border border-border rounded p-2.5 shadow-xl text-xs pointer-events-none relative z-1000">
        <p className="font-semibold text-foreground">{payload[0]?.name}</p>
        <p
          className="font-medium"
          style={{ color: payload[0]?.payload?.color }}
        >
          {payload[0]?.value}%
        </p>
      </div>
    );
  }
  return null;
};

// Custom Tooltip for Category Bar Chart
const CategoryTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div className="bg-background border border-border rounded p-2.5 shadow-lg text-xs">
        <p className="font-semibold text-foreground">{label}</p>
        <p className="text-purple-500">Count: {payload[0]?.value}</p>
      </div>
    );
  }
  return null;
};

// Custom legend renderer
const renderCustomLegend = (props) => {
  const { payload } = props;
  return (
    <div className="flex justify-center gap-4 mt-1">
      {payload.map((entry) => (
        <div key={entry.color} className="flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-xs text-muted-foreground">{entry.value}</span>
        </div>
      ))}
    </div>
  );
};

export default function FileTypeDistributionChart({ stats }) {
  const { pdf, docx } = stats.fileTypeDistribution;

  const { total, displayPieData } = useMemo(() => {
    // pdf, docx, xlsx are now { count, percentage }
    const pdfPerc = pdf?.percentage || 0;
    const docxPerc = docx?.percentage || 0;

    // Use percentages for the Pie Chart visualization
    const totalPerc = pdfPerc + docxPerc;

    const pData = [
      { name: "PDF", value: pdfPerc, color: FILE_TYPE_COLORS.PDF },
      { name: "DOCX", value: docxPerc, color: FILE_TYPE_COLORS.DOCX },
    ].filter((d) => d.value > 0);

    const dPieData =
      pData.length > 0
        ? pData
        : [
            { name: "PDF", value: 33, color: "#fca5a5" },
            { name: "DOCX", value: 33, color: "#93c5fd" },
          ];

    return { total: totalPerc, displayPieData: dPieData };
  }, [pdf, docx]);

  const isEmpty = total === 0;

  // Category bar chart data
  const categoryData = useMemo(() => {
    return stats.categoryPopularity && stats.categoryPopularity.length > 0
      ? stats.categoryPopularity.slice(0, 5)
      : [];
  }, [stats.categoryPopularity]);

  return (
    <CardWrapper title="File Type Distribution" className="flex flex-col">
      <div className="flex-1 space-y-3">
        <div className="flex justify-center items-center h-45">
          <PieChart key={total} width={200} height={180}>
            <Pie
              data={displayPieData}
              cx="50%"
              cy="50%"
              outerRadius={80}
              innerRadius={0}
              dataKey="value"
              labelLine={false}
              label={false}
              strokeWidth={isEmpty ? 1 : 2}
              stroke="var(--background)"
            >
              {displayPieData.map((entry) => (
                <Cell
                  key={entry.color}
                  fill={entry.color}
                  opacity={isEmpty ? 0.3 : 1}
                />
              ))}
            </Pie>
            <Tooltip
              content={isEmpty ? () => null : <PieTooltip />}
              offset={20}
              wrapperStyle={{ zIndex: 1000 }}
              allowEscapeViewBox={{ x: true, y: true }}
            />
            <Legend content={renderCustomLegend} />
          </PieChart>
        </div>

        {isEmpty && (
          <div className="absolute top-[42%] left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">
              No data yet
            </p>
          </div>
        )}

        {/* File type percentage bars - compact */}
        <div className="space-y-2 px-1">
          {[
            {
              name: "PDF",
              value: pdf?.percentage || 0,
              count: pdf?.count || 0,
              color: FILE_TYPE_COLORS.PDF,
            },
            {
              name: "DOCX",
              value: docx?.percentage || 0,
              count: docx?.count || 0,
              color: FILE_TYPE_COLORS.DOCX,
            },
          ].map((type) => (
            <div key={type.name} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: type.color }}
                  />
                  <span className="font-medium text-foreground">
                    {type.name}: {type.count} files
                  </span>
                </div>
                <span className="text-muted-foreground">{type.value}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-1.5 rounded-full transition-all duration-500"
                  style={{
                    width: `${type.value}%`,
                    backgroundColor: type.color,
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Top Categories Bar Chart */}
        <div className="border-t border-border">
          <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
            <Icon name="chart" size="16px" className="text-secondary" />
            Top Framework Categories
          </h4>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={90}>
              <BarChart
                data={categoryData}
                margin={{ top: 0, right: 8, left: -24, bottom: -12 }}
                barSize={60}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  vertical={false}
                />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  content={<CategoryTooltip />}
                  cursor={{ fill: "var(--accent)" }}
                />
                <Bar
                  dataKey="count"
                  radius={[3, 3, 0, 0]}
                  fill="var(--secondary)"
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No category data available
            </p>
          )}
        </div>
      </div>
    </CardWrapper>
  );
}
