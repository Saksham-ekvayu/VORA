/* eslint-disable react/prop-types */

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Sector,
} from "recharts";
import { useState } from "react";

// Custom tooltip component
const CustomTooltip = ({ active, payload, total }) => {
  if (active && payload?.length) {
    const item = payload[0].payload;
    const percentage = total > 0 ? ((item.value / total) * 100).toFixed(1) : 0;

    return (
      <div className="bg-background backdrop-blur-sm rounded px-4 py-2 shadow-xl border border-border z-100">
        <p className="text-sm font-semibold mb-1">{item.name}</p>
        <p className="text-xs">
          Value: <span className="font-medium">{item.value}</span>
        </p>
        <p className="text-xs">
          Percentage: <span className="font-medium">{percentage}%</span>
        </p>
      </div>
    );
  }
  return null;
};

export default function ReviewStatusPieChart({ data }) {
  const [activeIndex, setActiveIndex] = useState(null);
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const completedCount = data
    .filter((d) => d.name === "Approved")
    .reduce((sum, d) => sum + d.value, 0);

  // Custom shape with hover effect - only pie expands
  const renderActiveShape = (props) => {
    const {
      cx,
      cy,
      innerRadius,
      outerRadius,
      startAngle,
      endAngle,
      fill,
      index,
    } = props;

    const isActive = activeIndex === index;
    const radius = isActive ? outerRadius + 12 : outerRadius;
    const innerRad = isActive ? innerRadius - 4 : innerRadius;

    return (
      <g>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRad}
          outerRadius={radius}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
          stroke="#fff"
          strokeWidth={3}
          style={{
            transition: "all 0.3s ease-in-out",
            cursor: "pointer",
            filter: isActive
              ? "drop-shadow(0 4px 8px rgba(0,0,0,0.2))"
              : "none",
          }}
        />
      </g>
    );
  };

  return (
    <div className="w-full h-full flex flex-col">
      {/* Chart area */}
      <div className="flex-1 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={4}
              dataKey="value"
              animationDuration={1000}
              animationBegin={0}
              animationEasing="ease-out"
              stroke="#fff"
              strokeWidth={3}
              isAnimationActive={true}
              activeIndex={activeIndex}
              activeShape={renderActiveShape}
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
            >
              {data.map((entry) => (
                <Cell
                  key={`cell-${entry.color}`}
                  fill={entry.color}
                  className="cursor-pointer transition-all duration-300"
                />
              ))}
            </Pie>
            <Tooltip
              content={<CustomTooltip total={total} />}
              wrapperStyle={{ zIndex: 1000 }}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Center content */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
          style={{ zIndex: 1 }}
        >
          <div className="text-3xl font-bold text-foreground">{total}</div>
          <div className="text-xs text-muted-foreground mt-1">
            Total Reviews
          </div>
          <div className="flex items-center gap-1 mt-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs text-muted-foreground">
              {total > 0 ? ((completedCount / total) * 100).toFixed(0) : 0}%
              Approved
            </span>
          </div>
        </div>
      </div>

      {/* Bottom legend with items and values - no hover effect */}
      <div className="grid grid-cols-3 gap-2 px-4">
        {data.map((item) => (
          <div
            key={item.color}
            className="flex items-center justify-between p-2 rounded bg-accent"
          >
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-xs font-medium text-foreground capitalize">
                {item.name}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-foreground">
                {item.value}
              </span>
              <span className="text-xs text-muted-foreground">
                ({total > 0 ? ((item.value / total) * 100).toFixed(1) : 0}%)
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
