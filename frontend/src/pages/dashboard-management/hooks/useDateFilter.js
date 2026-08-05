/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * Compute { startDate, endDate } ISO strings for a given preset key.
 */
export function getPresetRange(preset) {
  const now = new Date();

  const end = new Date(now);
  end.setHours(23, 59, 59, 999);

  const start = new Date(now);
  start.setHours(0, 0, 0, 0);

  switch (preset) {
    case "today":
      return { startDate: start.toISOString(), endDate: end.toISOString() };
    case "7d":
      start.setDate(start.getDate() - 6);
      return { startDate: start.toISOString(), endDate: end.toISOString() };
    case "30d":
      start.setDate(start.getDate() - 29);
      return { startDate: start.toISOString(), endDate: end.toISOString() };
    case "90d":
      start.setDate(start.getDate() - 89);
      return { startDate: start.toISOString(), endDate: end.toISOString() };
    case "180d":
      start.setDate(start.getDate() - 179);
      return { startDate: start.toISOString(), endDate: end.toISOString() };
    default:
      return { startDate: null, endDate: null };
  }
}

/**
 * Encapsulates date filter state + URL search param sync for dashboard pages.
 * Returns { datePreset, startDate, endDate, handleDateChange }.
 */
export function useDateFilter(defaultPreset = "30d") {
  const [searchParams, setSearchParams] = useSearchParams();

  const initPreset = searchParams.get("preset") || defaultPreset;
  const initRange = (() => {
    const s = searchParams.get("startDate");
    const e = searchParams.get("endDate");
    if (s && e) return { startDate: s, endDate: e };
    return getPresetRange(initPreset);
  })();

  const [datePreset, setDatePreset] = useState(initPreset);
  const [startDate, setStartDate] = useState(initRange.startDate);
  const [endDate, setEndDate] = useState(initRange.endDate);

  // Sync default filter into URL on mount if not already present
  useEffect(() => {
    if (!searchParams.get("preset")) {
      setSearchParams(
        {
          preset: initPreset,
          startDate: initRange.startDate,
          endDate: initRange.endDate,
        },
        { replace: true }
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDateChange = (preset, start, end) => {
    setDatePreset(preset);
    setStartDate(start);
    setEndDate(end);
    setSearchParams(
      { preset, startDate: start, endDate: end },
      { replace: true }
    );
  };

  return { datePreset, startDate, endDate, handleDateChange };
}
