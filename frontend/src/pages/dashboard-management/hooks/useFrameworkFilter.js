/* eslint-disable react/prop-types */

import { useState } from "react";
import { useSearchParams } from "react-router-dom";

export function useFrameworkFilter() {
  const [searchParams, setSearchParams] = useSearchParams();

  const initFrameworkId = searchParams.get("frameworkId") || "all";
  const [selectedFrameworkId, setSelectedFrameworkId] =
    useState(initFrameworkId);

  const handleFrameworkChange = (frameworkId) => {
    setSelectedFrameworkId(frameworkId);

    // Create new URLSearchParams object to avoid overwriting other params
    const newParams = new URLSearchParams(searchParams);

    if (frameworkId && frameworkId !== "all") {
      newParams.set("frameworkId", frameworkId);
    } else {
      newParams.delete("frameworkId");
    }

    setSearchParams(newParams, { replace: true });
  };

  return { selectedFrameworkId, handleFrameworkChange };
}
